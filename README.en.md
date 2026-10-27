<p align="center">
  <img alt="HakiOS ishtar" src="assets/logo.png" width="180">
</p>

<p align="center">
  <a href="https://t.me/petegroup"><img alt="Telegram" src="https://img.shields.io/badge/Telegram-%40petegroup-26A5E4?logo=telegram&logoColor=white&style=for-the-badge"></a>
</p>

<p align="center">
  <a href="README.md">简体中文</a> | English
</p>

# HakiOS · ishtar

Port of HakiOS to the Xiaomi 13 Ultra (`ishtar`, Qualcomm SM8550-AB "kalama"): the **iOS 16.5
userland** on a custom XNU kernel. Derived from
[hackios-xnu-kernel](https://github.com/oosexgang/hackios-xnu-kernel); the reference device is the
POCO X5 Pro (`redwood`, SM7325).

Two tracks: **QEMU** verifies everything that does not depend on this phone's hardware, and the
**port** covers what does. The first reaches the home screen; the second still lacks a UEFI. Nothing
is written to the phone: `fastboot boot` (RAM only) and read-only collection are the only permitted
operations.

## Status

| Path | State | Evidence |
| --- | --- | --- |
| QEMU (aarch64 TCG) | iOS 16.5 to the home screen, interactive | 1125×2436, 18281 colours, 10–16 fps |
| ishtar hardware | not booted | no usable UEFI firmware |

| Part | State |
| --- | --- |
| Kernel, boot chain, display (linear framebuffer) | implemented, verified in QEMU |
| iOS 16.5 userland, injection library | implemented, verified |
| iOS 16.7.16 userland | partial: SpringBoard blocks in FrontBoard's synchronous XPC |
| UEFI (`ishtarPkg`), touch, GPU, IPA | not started |

## Findings

**The black screen was the loader's panel hand-off.** QEMU completes the fw_cfg DMA inside the MMIO
write and clears the descriptor's control word in memory; the loader read back the processor's
cached copy, took the request for refused, and left the screen at the firmware's 800×600 and at the
firmware's buffer. The kernel then drew a 1125×2436 picture into memory no display shows. The
request is now taken as done once written. The defect is independent of the iOS version and of the
renderer.

**A 16.7.16 userland needs fourteen addresses moved.** The library verifies the address of each
method before replacing it, and all fourteen were the 16.5 ones; every hook was refused and
SpringBoard never answered activation. Each refusal prints the address it found, which is the table
`also_in_16_7_16[]`: both builds are accepted now, a third is still refused.

**Panel size and core count have hard limits.** Only the default 1125×2436 works: `fbscale=2`
(750×1624) and `fbscale=1` (375×812) hit a defect in the display path. `cpus=8` deadlocks the guest
(log truncated mid-line, screen frozen, no panic); `cpus=4` is stable.

## Device parameters

`devices/ishtar/soc.args` comes from this phone's device tree and corrects three values of the
reference tree: `soc_ipa_base` `0x3e40000` (not `0x3f40000`), `soc_mpss_mem` `0x89800000` (not
`0x8a800000`), `soc_ipa_fw` `ipa_fws` (not `kalama_ipa_fws`).

Platform (`platform_ishtar`): GIC `0x17100000`/`0x17180000`, 8 cores at MPIDR shift 8, `small_cores
0x07`, display base `0xB8000000`, panel 1440×3200 at 5760 bytes per row. 128 partitions, no
`darwin`.

## Build and run

```sh
sysimage/fetch.sh                 # iOS 16.5 (20F66) by default; see sysimage/VERSIONS.md
REST=1 GL=1 userland/build.sh     # root.apfs and system.apfs
qemu/run-ios.sh 1800 -display gtk,zoom-to-fit=on
```

Boot arguments `cpus=4 gl=1`, default resolution. About eight minutes to the home screen; the
interface is rasterised by Mesa on the emulated processors, the host GPU takes no part.

## Known defects

| Symptom | Condition | State |
| --- | --- | --- |
| Guest deadlock: log truncated, screen frozen, ~190% CPU, no panic | `cpus=8`; or `tb-size=1G` without wifid | open; `cpus=4` and the default `tb-size` avoid it |
| Black screen after the boot logo | `fbscale=1`, `fbscale=2` | open; only the default resolution works |
| SpringBoard blocks in FrontBoard's synchronous XPC | iOS 16.7.16 | open |
| `check_all_exports` fails | after `make kernel` | open; `mkpayload.py` by hand is the way round |

## Documentation

- [ISHTAR.md](ISHTAR.md) — state, parameters, per-change reasons, device work list
- [devices/ishtar/PORTING.md](devices/ishtar/PORTING.md) — work order, IPA v4.11→v5.5 tables, UEFI inventory
- [sysimage/VERSIONS.md](sysimage/VERSIONS.md) — the sysctls and addresses 16.7.16 needs
- [README.upstream.md](README.upstream.md) — the upstream project

## Contact

Port discussion: Telegram [@petegroup](https://t.me/petegroup). Results and hardware observations
belong in `ISHTAR.md` or the issue tracker; the group is a conversation channel.

## Upstream and licence

Derived from [oosexgang/hackios-xnu-kernel](https://github.com/oosexgang/hackios-xnu-kernel) under the
upstream licence ([LICENSE](LICENSE), [LICENSE.APSL](LICENSE.APSL)). The repository holds no Apple
system files, IPSW components or vendor firmware; those are fetched by script from the device or from
the vendor and stay out of version control.
