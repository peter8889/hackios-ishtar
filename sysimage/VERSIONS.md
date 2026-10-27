# Running iOS 16.7.16 on the iOS 16.5 kernel

The system image is made of files taken out of an IPSW: the iPhone X's own **iOS 16.5 (20F66)**
by default. The **iOS 16.7.16 (20H392)** of the same phone works on the same kernel, and this
document says how, and what had to be changed in the kernel for it.

## Why it can work

The kernel is xnu-8796.121.2, the iOS 16 generation's, and it runs a 16.7 userland: the
*ios-sweet* project (github.com/dipa-software/ios-sweet) boots the unmodified **16.7.16**
userland of the iPhone X on xnu-8796, and so does this. A userland of another **major** version
does not fit: iOS 17 brought signed cryptexes, iOS 18 a different boot volume layout, and both
new system calls and new structures in the kernel's interfaces.

What the 16.7 userland asks of the kernel that the 16.5's userland does not is the **hardware
target**. `dyld` needs it to know what it is running on, and gives up without it:

```
pid 1 exited -- exit reason namespace 35 subcode 0x6, description failed to query hardware target: 22
panic(cpu 0 caller ...): initproc failed to start
```

The message comes from `dyld` (it is in `rootfs/usr/lib/dyld`), and the 22 is `EINVAL` from the
kernel's `hw.target` sysctl.

## The two changes in the kernel

Both are in `xnu/port-16.7/` and are applied to the kernel's source tree
(`xnu-src/xnu-8796.121.2`):

| Script | What it does |
|---|---|
| `fix-hw-target.py` | `bsd/kern/kern_mib.c`: `hw.target` falls back to the device tree |
| `fix-targettype.py` | `iokit/Kernel/IOPMrootDomain.cpp`: `hw.targettype` reads the device tree |

**Why `hw.target` failed.** XNU answers it with `PEGetTargetName()`, which asks the platform
expert. Apple's `IOPlatformExpert` is not in the open source, so on this port `gIOPlatform` is
null, the call fails, and the sysctl returns `EINVAL`. The device tree's root does say the target
type (`target-type`, which the loader copies from the phone's own device tree, so it is the phone's
own answer: `d22ap`), and that is what is used instead.

**Why `hw.targettype` failed.** XNU has that sysctl too (`iokit/Kernel/IOPMrootDomain.cpp`:
`SYSCTL_PROC(_hw, OID_AUTO, targettype, ...)`), but its handler takes the value from the property
`target-type` of the root domain in the IORegistry's **service plane**, and nothing puts it there
on this port: the device tree's tree hangs in the device tree's **plane**. So the handler is
taught to read the device tree itself.

```sh
cd xnu-src/xnu-8796.121.2
python3 ../../xnu/port-16.7/fix-hw-target.py .
python3 ../../xnu/port-16.7/fix-targettype.py .
```

## And the loader has to know the phone

`xnuloader/mkidentity.sh` makes `xnuloader/identity.h` from the phone's own device tree, which
is where `target-type` comes from. The loader copies that property into the device tree it writes
for the kernel (`dt_identity`), so **the loader has to be built after the identity is made**:

```sh
xnuloader/mkidentity.sh              # from the IPSW's DeviceTree.d22ap.im4p
xnuloader/build.sh                   # the loader with the identity in it
```

A loader built with the placeholder identity (`PLACEHOLDER=1 xnuloader/mkidentity.sh`) has no
`target-type` in it, and then the kernel cannot answer, and `dyld` gives up.

## Getting the files of the 16.7.16

Everything the fetch needs is known for it (checked on 2026-10-27; the archive was listed with
`sysimage/list-ipsw.py`, which reads the archive's directory with a couple of range requests and
downloads nothing):

```sh
export IPSW_URL='https://updates.cdn-apple.com/2025FallFCS/fullrestores/122-77006/1158E502-D76D-4226-AA06-ED5E30CD1111/iPhone10,3,iPhone10,6_16.7.16_20H392_Restore.ipsw'
export IPSW_SIZE=6171035648
export ROOTFS_DMG=087-86698-044.dmg        # the root filesystem (4,730,814,044 bytes)
export CRYPTEX_DMG=087-86593-047.dmg       # the OS cryptex, with the dyld shared cache (2,743,074,816)
export APP_CRYPTEX_DMG=087-86715-047.dmg   # the App cryptex (10,485,760)
export CACHE=20H392__iPhone10,3_x
export KEEP=1
sysimage/fetch.sh
```

The names of the images differ from the 16.5's (Apple renumbered them from 096-* to 087-*), but
they are the same images by their sizes:

| | 16.5 (20F66) | 16.7.16 (20H392) |
|---|---|---|
| the root filesystem | `096-04088-077.dmg` (4,728,546,953) | `087-86698-044.dmg` (4,730,814,044) |
| the OS cryptex | `096-04666-078.dmg` (2,726,297,600) | `087-86593-047.dmg` (2,743,074,816) |
| the App cryptex | `096-03536-083.dmg` (10,485,760) | `087-86715-047.dmg` (10,485,760) |
| (not used) | `096-03566-084.dmg`, `096-04690-083.dmg` | `087-86719-047.dmg`, `087-86622-047.dmg` |

The archive's SHA-256 is `ece1194f7e233e9109c5790a8d23a4564a10a254e15ec5b09978a343265568fb`.

`CACHE` is not a name in the archive: the dyld shared cache is inside the OS cryptex, and `CACHE`
is the name of the directory it is put in. How many files it has is checked after the unpacking
(`DYLID_FILES`, 43 in the 16.5 and in the 16.7.16).

### Where the URL comes from

Apple's own address for a build ends in a GUID that is different for every release, so it cannot
be written down here. Take it from the download link of the build in question:

- **ipsw.me** lists every build of every device; the download button's link is the address to use;
- the **`ipsw`** tool (`github.com/sickhouse/ipsw`) prints it: `ipsw download ipsw --device iPhone10,3 --version 16.7.16`;
- **Apple's own** `https://mesu.apple.com/assets/.../com_apple_MobileAsset_SoftwareUpdate/...`
  points at the same file.

`IPSW_SIZE` is the size of the archive the server reports; `ipsw download` prints it too, and
`curl -sI "$IPSW_URL" | grep -i content-length` gives it.

## Building and running it

```sh
sysimage/fetch.sh                 # the files of the iOS, from Apple's servers
REST=1 userland/build.sh          # the APFS images: userland/root.apfs and userland/system.apfs
qemu/run-ios.sh 1200 -display gtk # a session on the PC
```

`userland/build.sh` needs to be told where the dyld shared cache was put (`CACHE`), and
`sysimage/fetch.sh` where it is (`CACHE` as well, plus `IPSW_URL`, `IPSW_SIZE` and the three
image names).

What it looks like when it works:

```
libignition: 1:   hardware target     : d22ap
libignition: 1:      goodbye: ignition sequence complete
com.apple.xpc.launchd|... Darwin Bootstrapper Version 7.0.0
com.apple.xpc.launchd|... Restore environment starting.
com.apple.xpc.launchd|... entering ondemand mode
```

## What is still to be done for it

The userland of a later 16 is not the same files as the 16.5's, and this repository's tools know
the 16.5's:

- `sysimage/select-system.py` picks the files of the image. A build with a bundle moved or
  renamed (it says so when it cannot find one) needs that list changed.
- `userland/build.sh` moves the extracted files into the image; a path that moved needs changing
  there too.
- the code injected into `backboardd`, `SpringBoard` and `appstored` (in `userland/src/inject*.c`)
  and the one that makes the App Store work (FairPlay) are written against the 16.5's frameworks.
  They are the parts most likely to need adjusting; the notes in `docs/ru/notes.md` say what each
  one hooks into.

The kernel and the drivers do not change (apart from the two sysctls above). So does the build,
and neither does the way the phone is booted: the image goes into RAM, nothing is written to the
flash.

## The injection library, and the addresses it needed (2026-10-27)

`userland/src/inject_sb.c` replaces methods of SpringBoard's classes, and it checks the address of
each method before replacing it: what a replacement does depends on what the original did, so the
address is the proof that this is the method the replacement was written for. The addresses were
the 16.5 ones (20F66). On the 16.7.16 userland **every one of the fourteen was refused** --
`found 0x…, expected 0x…; left alone` for each, and the summary line read `activation NOT replaced,
setup assistant NOT replaced, …`. SpringBoard therefore ran with no answer to activation and no
refusal of the setup assistant, and never got to its first scene.

Each refusal prints the address it did find, so the table wrote itself: `also_in_16_7_16` in that
file now holds both, and the check accepts either (a third build is still refused).

| Method | 16.5 (20F66) | 16.7.16 (20H392) |
|---|---|---|
| `-[SBLockdownManager _setupActivationState]` | `0x1c4bc8dfc` | `0x1c5991a78` |
| `-[SBSetupManager _setSetupRequiredReason:]` | `0x1c4cdd3a4` | `0x1c5aa608c` |
| `+[XBApplicationSnapshotManifestImpl _outputFormatForSnapshot:]` | `0x1f1c91480` | `0x1f287f320` |
| `-[SBLockHardwareButton longPress:]` | `0x1c4f6ab44` | `0x1c5d339b0` |
| `-[SBMainDisplayPolicyAggregator _allowsCapabilityPosterSwitcherWithExplanation:]` | `0x1c507e0fc` | `0x1c5e46f8c` |
| `-[SBAppSwitcherPageView _createOrDestroyWallpaperOverlayView]` | `0x1c4af7860` | `0x1c58c0460` |
| `-[UIDevice batteryLevel]` | `0x1897021b0` | `0x18970b8bc` |
| `-[UIDevice batteryState]` | `0x189209794` | `0x189212b64` |
| `-[_UIBatteryView showsPercentage]` | `0x189a9370c` | `0x189a9d1c8` |
| `-[_UIBatteryView setShowsPercentage:]` | `0x18926e150` | `0x189277520` |
| `-[_UIBatteryView _shouldShowBolt]` | `0x189203e28` | `0x18920d1f8` |
| `-[_UIBatteryView chargePercent]` | `0x189a935d8` | `0x189a9d094` |
| `-[_UIBatteryView setChargePercent:]` | `0x18928d310` | `0x1892966e0` |
| `-[CSBatteryChargingRingView batteryChargingLevel]` | `0x1c48c2cf4` | `0x1c568bd24` |

With the table in place all fourteen apply, and the summary line says so:

```
hakios: SpringBoard: activation answered here, setup assistant refused, application snapshots as
JPEG, the side button's long press checked, battery level from QG, battery state from QG, poster
switcher not offered
```

**Effect.** SpringBoard's main thread moved from a CoreServices run-loop call to FrontBoard's
synchronous scene call (`FrontBoard` -> `BackBoardServices` -> `BoardServices` -> `libxpc` ->
`mach_msg`), with four threads. The picture is one colour, `#000000`, at 2.5, 5 and 7.5 minutes
(`logs/shot-c-*.png`); backboardd draws three quads a frame and copies one picture out, with no
client surface as its texture (`0 textures refilled from IOSurfaces`).

**Next candidate: `userland/src/inject.c`.** Its hooks are vtable slots of
`CA::WindowServer::AppleCLCDDisplay` (`0x1d5b44520`) and `EAGLServer` (`0x1d5b45c58`), 16.5
addresses; the run prints `found 0xffffffffe012c000` for each. `my_renderer` is functional, not
diagnostic: it caches the failure to create a Metal or OpenGL ES context so that the server stops
retrying it every frame and draws with `sw_renderer()`. Refused, the server retries a context every
frame: 5 frames/s in that run against 16.

**On timing screenshots.** A capture taken before the interface exists measures the boot picture, not
the display path: the three that concluded "black screen" were taken 1.5 and 0 minutes after launchd
started. The 16.7.16 interface did not appear within 7 minutes, and 16.5 needed about 7 minutes at
1125x2436.

