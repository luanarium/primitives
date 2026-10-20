#!/bin/bash
# Normalised band profile: each band relative to the file's own overall level.
band() { ffmpeg -hide_banner -ss $2 -t 58 -i "$1" -af "$3,volumedetect" -f null - 2>&1 | grep mean_volume | sed 's/.*mean_volume: //;s/ dB//'; }
all=$(band "$1" "$2" anull)
out=""
for f in 250 500 1000 2000 4000; do
  hp="highpass=f=$f:poles=2,highpass=f=$f:poles=2,highpass=f=$f:poles=2"
  got=$(band "$1" "$2" "$hp")
  out="$out $(python3 -c "print(f'{$got - ($all):.1f}')")"
done
echo "$all |$out"
