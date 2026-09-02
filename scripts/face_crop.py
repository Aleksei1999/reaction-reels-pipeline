"""Ищет лицо в person-видео и считает параметры кропа.

Печатает JSON:
  circle_x/circle_y — левый верхний угол квадрата SIZE x SIZE для круга в part1
  talk_crop_x       — x для crop 1080x1920 в part2 (после scale=-1:1920)

Сэмплит N кадров по всей длине, берёт медиану найденных лиц — так один
неудачный кадр (человек отвернулся) не сдвигает рамку.
"""
import argparse, json, statistics, sys
import cv2

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--size", type=int, default=500, help="сторона квадрата под круг")
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=0.0, help="0 = до конца")
    ap.add_argument("--model", default="models/face_detection_yunet_2023mar.onnx")
    ap.add_argument("--conf", type=float, default=0.6)
    ap.add_argument("--headroom", type=float, default=0.50,
                    help="во сколько раз квадрат шире лица (0.55 => лицо занимает ~55%)")
    a = ap.parse_args()

    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    f0 = int(a.start * fps)
    f1 = int(a.end * fps) if a.end else total
    step = max(1, (f1 - f0) // a.samples)

    # YuNet: OpenCV 5 выкинул Haar-каскады, зато детектит профиль и опущенную голову
    det = cv2.FaceDetectorYN_create(a.model, "", (W, H), a.conf, 0.3, 5000)

    cx, cy, sz = [], [], []
    for f in range(f0, f1, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, img = cap.read()
        if not ok: continue
        _, faces = det.detect(img)
        if faces is None or not len(faces): continue
        x, y, w, h = max(faces, key=lambda r: r[2]*r[3])[:4]
        cx.append(x + w/2); cy.append(y + h/2); sz.append((w+h)/2)
    cap.release()

    if len(cx) < 3:
        print(json.dumps({"error": "лицо не найдено", "hits": len(cx),
                          "w": W, "h": H}), file=sys.stderr)
        sys.exit(1)

    mx, my, ms = (float(statistics.median(v)) for v in (cx, cy, sz))
    # квадрат вокруг лица, чуть выше центра — чтобы влез лоб и подбородок
    box = ms / a.headroom
    scale = a.size / box
    # координаты в исходном разрешении: кропаем box, но render ждёт готовый size
    half = box / 2
    x0 = int(round(mx - half)); y0 = int(round(my - half * 1.30))
    x0 = max(0, min(W - int(box), x0)); y0 = max(0, min(H - int(box), y0))

    # part2: scale=-1:1920 => коэффициент 1920/H, кроп 1080 по центру лица
    k = 1920 / H
    talk_x = int(round(mx * k - 540))
    talk_x = max(0, min(int(W * k) - 1080, talk_x))

    print(json.dumps({
        "video_w": W, "video_h": H, "hits": len(cx),
        "face_cx": round(mx), "face_cy": round(my), "face_size": round(ms),
        "crop_box": int(round(box)), "crop_x": x0, "crop_y": y0,
        "circle_scale": round(scale, 3),
        "talk_crop_x": talk_x,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
