#!/bin/bash
# Pull the phone's own firmware out of its Android into the fw-*/ directories at the top of the
# repository (never committed: it is the vendor's). The phone is on adb, in Android.
#
# The files are the ones this phone's Android uses: the Adreno 740's firmware (an A7xx one, the
# first phone's an A6xx one), the Wi-Fi's, the audio DSP's, the vibration motor's, the modem's and
# the camera modules'. A file that is not there is told, not fatal: the lists are the ones this
# phone's own vendor tree names, and a different region of the same phone may have others.
set -e
cd "$(dirname "$0")/../.."
pull() { # DIR SOURCE...  (missing files are told, not fatal)
	local dir=$1; shift
	mkdir -p "$dir"
	for f in "$@"; do adb pull "$f" "$dir/" >/dev/null 2>&1 || echo "pull-firmware.sh: $f: not on the phone"; done
	echo "pull-firmware.sh: $dir: $(ls -1 "$dir" | wc -l | tr -d ' ') files"
}
adb get-state >/dev/null

# the GPU: an Adreno 740's firmware is the A7xx one (a740_sqe.fw, gmu_gen70200.bin, a740_zap.*)
pull fw-gpu /vendor/firmware/a740_sqe.fw /vendor/firmware/gmu_gen70200.bin /vendor/firmware/a740_zap.mdt \
	$(for i in $(seq -w 0 8); do echo /vendor/firmware/a740_zap.b$i; done)

# the Wi-Fi (the WCN7850's, in the WPSS partition)
pull fw-wifi $(for i in mdt b02 b03 b04 b05 b06 b07; do echo /vendor/firmware_mnt/image/wpss.$i; done)

# the audio DSP: the battery and the charging come through it too
pull fw-audio /vendor/firmware_mnt/image/adsp.mdt $(for i in $(seq -w 2 40); do echo /vendor/firmware_mnt/image/adsp.b$i; done)

# the vibration motor (this phone's own model; the first phone's was an Awinic AW86927)
pull fw-haptic $(adb shell 'ls /vendor/firmware/*haptic* /vendor/firmware/*aw* 2>/dev/null' | tr -d '\r')

# the modem
pull fw-modem /vendor/firmware_mnt/image/modem.mdt $(for i in $(seq -w 0 30); do echo /vendor/firmware_mnt/image/modem.b$i; done)
mkdir -p fw-modem/image && adb pull /vendor/firmware_mnt/image fw-modem/ >/dev/null 2>&1 && echo "pull-firmware.sh: fw-modem/image: the modem's own files (TFTP)"

# the camera modules
pull fw-camera $(adb shell ls /vendor/lib64/camera/com.qti.sensormodule.hakios_*.bin /vendor/lib64/camera/com.qti.tuned.hakios_*.bin 2>/dev/null | tr -d '\r')

echo "pull-firmware.sh: done; Wi-Fi also wants fw-wifi/mac (the radio's address) and fw-wifi/network (the network's name and passphrase)"
