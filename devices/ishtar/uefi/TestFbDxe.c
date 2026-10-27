/** @file
  Fill the panel's framebuffer with a solid colour, as early as the dispatcher will run it.

  The 13 Ultra's UEFI leaves the panel's memory at 0xB8000000 (see platform_ishtar in the XNU
  loader, and splash_region in the device tree). Whether writing there changes what the panel
  shows decides two very different next steps: if it does, the framebuffer is ours and only a
  GraphicsOutput protocol is missing; if it does not, the panel has to be brought up over DSI
  before any pixel reaches it.
**/

#include <Uefi.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/DebugLib.h>

#define FB_BASE   0x0B8000000ULL
#define FB_WIDTH  1440U
#define FB_HEIGHT 3200U

EFI_STATUS
EFIAPI
TestFbEntry (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  volatile UINT32  *Fb;
  UINTN            Index;
  UINTN            Pixels;

  Fb     = (volatile UINT32 *)(UINTN)FB_BASE;
  Pixels = (UINTN)FB_WIDTH * FB_HEIGHT;

  //
  // A colour no part of the boot chain uses: anything visible proves the panel is scanning this
  // memory out and that writes reach it.
  //
  for (Index = 0; Index < Pixels; Index++) {
    Fb[Index] = 0x00FF00FFU;   /* magenta, XRGB8888 */
  }

  DEBUG ((DEBUG_ERROR, "TestFbDxe: filled %u pixels at 0x%lx\n", (UINT32)Pixels, FB_BASE));
  return EFI_SUCCESS;
}
