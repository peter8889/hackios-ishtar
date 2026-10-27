#!/bin/bash
# Pack the current FD into a boot image and load it with `fastboot boot`, timing how long the
# device stays away: it disconnects while the image runs and comes back to fastboot when the
# image faults or exits. A short absence is an early fault, a long one means it got further.
#
# usage: attempt.sh TAG [FD] [DTB]
set -u
TAG=$1
FD=${2:-$HOME/work/mu-src/Build/ishtarPkg/RELEASE_CLANGPDB/FV/SILICIUM_UEFI.fd}
DTB=${3:-$HOME/work/vb-splash.dtb}
GZ=$HOME/work/mu-src/Build/ishtarPkg/RELEASE_CLANGPDB/FV/SILICIUM_UEFI.fd-bootshim.gz
MK=/mnt/c/Users/818/WorkBuddy/2026-10-27-04-29-38/hakios/devices/poco-x5-pro/prebuilt/mkbootimg.py
FB=/mnt/c/platform-tools/fastboot.exe
OUT_IMG=/mnt/c/Users/818/WorkBuddy/2026-10-27-04-29-38/try-$TAG.img
LOG=$HOME/work/attempts.log

cat "$GZ" "$DTB" > "$HOME/work/k-$TAG.bin"
python3 "$MK" --kernel "$HOME/work/k-$TAG.bin" --header_version 1 --pagesize 4096 --output "$OUT_IMG" >/dev/null 2>&1 || {
  echo "$(date +%T) $TAG pack failed" | tee -a "$LOG"; exit 1; }

# make sure the device is in fastboot before we start
"$FB" devices 2>/dev/null | grep -q fastboot || { echo "$(date +%T) $TAG no device" | tee -a "$LOG"; exit 1; }

"$FB" boot "$OUT_IMG" >/dev/null 2>&1
t0=$(date +%s%3N)

gone=0; back=0
for i in $(seq 1 200); do
  now=$(date +%s%3N); el=$((now - t0))
  if "$FB" devices 2>/dev/null | grep -q fastboot; then
    if [ $gone -eq 1 ]; then back=$el; break; fi
  else
    if [ $gone -eq 0 ]; then gone=$el; fi
  fi
  sleep 0.25
done

# keep watching a little: the screen may stay on after a run that did not come back
if [ $back -eq 0 ]; then
  sleep 6
  if "$FB" devices 2>/dev/null | grep -q fastboot; then back=$(( $(date +%s%3N) - t0 )); fi
fi

echo "$(date +%T) $TAG fd=$(stat -c %s "$FD") dtb=$(stat -c %s "$DTB") gone=${gone}ms back=${back}ms" | tee -a "$LOG"
