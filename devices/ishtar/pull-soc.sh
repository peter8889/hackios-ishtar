#!/bin/bash
# Pull the phone's own device tree over adb and turn it into the SoC boot-args HakiOS needs on this
# device (tools/soc-args.py). Needs the phone in Android with adb (root not required:
# /sys/firmware/fdt is world-readable).
set -e
cd "$(dirname "$0")/../.."
PATH=$PWD/tools/macos-bin/platform-tools:$PATH
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
adb pull /sys/firmware/fdt "$tmp/fdt" >/dev/null || { echo "pull-soc.sh: cannot read /sys/firmware/fdt over adb"; exit 1; }
tools/soc-args.py "$tmp/fdt" | tee "$(dirname "$0")/soc.args"
echo "pull-soc.sh: wrote $(dirname "$0")/soc.args"
