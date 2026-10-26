#!/bin/bash
# Produce the final narrated mp4 from the demo video + narration track.
# Uses the ffmpeg that ships inside the project venv (pip package imageio-ffmpeg),
# so it needs NO Homebrew / system ffmpeg.
#
#   bash merge_narration.sh
#
# Output: scamscope_demo_narrated.mp4  (1280x720 H.264 + AAC, web-ready)
set -e
cd "$(dirname "$0")"

VENV_PY="../../.venv/bin/python"
VIDEO="scamscope_demo.webm"
AUDIO="narration.m4a"
OUT="scamscope_demo_narrated.mp4"

# Resolve the bundled ffmpeg (installed via: pip install imageio-ffmpeg)
FF="$("$VENV_PY" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null || true)"
if [ -z "$FF" ] || [ ! -x "$FF" ]; then
  echo "Bundled ffmpeg not found. Install it into the venv:"
  echo "    $VENV_PY -m pip install imageio-ffmpeg"
  echo "or use your own: brew install ffmpeg && ffmpeg -i $VIDEO -i $AUDIO -c:v copy -c:a aac -shortest $OUT"
  exit 1
fi

echo "Muxing $VIDEO + $AUDIO -> $OUT (ffmpeg: $FF)"
"$FF" -y -i "$VIDEO" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -pix_fmt yuv420p -preset medium -crf 20 \
  -c:a aac -b:a 160k \
  -movflags +faststart \
  "$OUT"

echo
echo "Done: $OUT"
echo "Upload it to YouTube (public or unlisted) and paste the link in the Builder Center demo field."
