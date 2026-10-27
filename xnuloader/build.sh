#!/bin/bash
# Build the XNU loader as a freestanding AArch64 UEFI application.
set -e
cd "$(dirname "$0")"
# the iPhone's identity for XNU, from the device tree of the builder's own IPSW (not in the repository)
[ -f identity.h ] || ./mkidentity.sh

# The picture the display shows: the iPhone X's 1125 x 2436 by default. PHONE_WIDTH and PHONE_HEIGHT
# make it smaller -- 750 x 1624 with the kernel's boot-arg fbscale=2, which is 2.25 times fewer pixels
# for the processor to draw under QEMU, and a window that fits on a screen.
clang --target=aarch64-unknown-windows -ffreestanding -fno-builtin -fno-stack-protector -fshort-wchar \
  -mgeneral-regs-only -O1 -Wall -Wextra -Wno-unused-parameter \
  ${PHONE_WIDTH:+-DPHONE_WIDTH=$PHONE_WIDTH} ${PHONE_HEIGHT:+-DPHONE_HEIGHT=$PHONE_HEIGHT} \
  -c loader.c -o loader.obj
# /base: UEFI loads an image at its preferred address when that is free. The PE default (0x140000000)
# is in the middle of the phone's largest block of RAM, which XNU needs in one piece.
lld-link /subsystem:efi_application /entry:efi_main /nodefaultlib /base:0xA1000000 /out:loader.efi loader.obj
ls -la loader.efi
