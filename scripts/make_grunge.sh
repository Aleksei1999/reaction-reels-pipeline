#!/bin/bash
# Генерирует grunge-переход (плёночное зерно + царапины + вспышка) в RGBA qtrle.
# Стоковый футаж не нужен. Результат: assets/grunge_trans.mov
#   bash scripts/make_grunge.sh [DUR] [OUT]
set -e
cd "$(dirname "$0")/.."
FFMPEG="${FFMPEG:-ffmpeg}"
DUR="${1:-0.6}"
OUT="${2:-assets/grunge_trans.mov}"
mkdir -p "$(dirname "$OUT")"

"$FFMPEG" -y \
  -f lavfi -i "color=c=black:s=1080x1920:r=30:d=$DUR" \
  -f lavfi -i "color=c=white:s=1080x1920:r=30:d=$DUR" \
  -filter_complex "
    [0:v]format=gray,
      noise=alls=100:allf=t+u,
      geq=lum='clip(
          ( lum(X,Y)*1.2
            + if(lt(abs(X-mod(N*217,1080)),2),255,0)
            + if(lt(abs(X-mod(N*631+400,1080)),1),210,0)
            + if(lt(abs(X-mod(N*89+800,1080)),3),150,0)
            + 90*sin(PI*T/$DUR)
          ) * pow(sin(PI*T/$DUR),0.7) * 1.5
        ,0,255)',
      gblur=sigma=0.5[mask];
    [1:v]format=gbrp[wht];
    [wht][mask]alphamerge,format=rgba[vout]
  " \
  -map "[vout]" -c:v png -t "$DUR" "$OUT"
echo "OK: $OUT"
