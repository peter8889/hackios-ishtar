# Porting HakiOS to the Xiaomi 13 Ultra (ishtar, SM8550)

The first phone this runs on is the POCO X5 Pro 5G (`redwood`, Snapdragon 778G / SM7325). This
document is the work list for the Xiaomi 13 Ultra (`ishtar`, Snapdragon 8 Gen 2 / SM8550-AB), what
each step needs, and how to tell that a step is done.

Nothing here is guessed where it can be read: the addresses come from the phone's own device tree
(`pull-soc.sh`) or from upstream Linux's `sm8550.dtsi`; the rest is marked "on the phone".

## What is different about this phone

| | POCO X5 Pro (`redwood`) | Xiaomi 13 Ultra (`ishtar`) |
|---|---|---|
| SoC | SM7325 ("yupik"), ARMv8.4 | SM8550-AB ("kalama"), ARMv9 |
| GPU | Adreno 642L (A6xx) | Adreno 740 (A7xx) -- a different architecture |
| IPA | v4.11, GSI 2.11 | **v5.5, GSI 5.5** -- different registers, channels, memory map |
| Storage | UFS 2/3 | UFS 4.0 |
| Display | 1080x2400 | 1440x3200 LTPO |
| Touch | Goodix / FocalTech over SPI | a different controller over SPI |
| Cameras | 4 (OV02B10, S5KHM2SD, OV16A1Q, S5K4H7) | 5 (50MP main + 50MP ultrawide + 2x periscope + 32MP front) |
| Wi-Fi | WCN6750 | WCN7850 |
| Haptics | Awinic AW86927 | a different motor and driver |

The good news, from reading the two device trees: the **register bases that do not move** are
many -- the GPU's (`0x3d00000`), the GPU clock controller's (`0x100000`), the IPCC's (`0x408000`),
the UFS host controller's (`0x1d84000`), the display clock controller's (`0xaf00000`), the
TLMM's (`0xf100000`), the AOSS mailbox's (`0xc300000`) and the application processors' SMMU's
(`0x15000000`) are the same on both. So are the SMEM item numbers (the modem's 428/435, the audio
DSP's 429/443, the Wi-Fi's 616/617) and the IPCC client numbers (MPSS 2, LPASS 3, WPSS 24).

The bad news: the **IPA** is a different version, and that is where the real work is.

## The order to work through

### 1. The build (done, on Linux)

The kernel builds from source on Linux with the toolchain this repository sets up: theos for the
cctools linker and the iPhoneOS 16.5 SDK, `xnu-deps/setup.sh` for the rest. Three things had to be
fixed for it to work on Linux, and they are fixed in this tree:

- `xnu-deps/setup.sh` unpacks the macOS SDK with the pattern before the file name, which GNU tar
  wants and BSD tar takes;
- `xnu-env.sh` points `MIGCC` at our compiler, because mig otherwise falls back to the system's
  `cc`, which cannot target an Apple machine;
- `xnu-deps/setup.sh` patches mig itself: it drops the path of an `-I <path>` option, so the
  compiler never sees the include paths, and it asks for a darwin target where the kernel needs
  the iOS one.

### 2. The device tree and the SoC addresses (done, needs the phone)

```sh
devices/ishtar/pull-soc.sh      # the phone in Android, on adb
```

This writes `devices/ishtar/soc.args`. The generator (`tools/soc-args.py`) was made to read both
trees: it matches a compatible by family (`qcom,ipa` also matches `qcom,sm8550-ipa`), reads the
IPA's regions by name (`ipa-reg`/`ipa-base`, `ipa-shared`, `gsi`/`gsi-base`), counts the address
and size cells from the tree, and finds the reserved-memory nodes by what they hold rather than
by their names.

`devices/ishtar/reference-sm8550.dts` is a reduced tree with the same shape as this phone's, so
the generator can be tested without the phone:

```sh
dtc -I dts -O dtb -o /tmp/sm8550.dtb devices/ishtar/reference-sm8550.dts
python3 tools/soc-args.py /tmp/sm8550.dtb
```

### 3. The UEFI (the phone's own firmware)

The loader is a UEFI application; the UEFI itself is a port of
[Project Silicium](https://github.com/Project-Silicium/Mu-Silicium). The SoC part of it is shared
with the Xiaomi 13 Pro (`nuwaPkg`, the same SM8550-AB), so that is the template; what has to come
from this phone is its own `xbl.img`:

```sh
# with the phone in fastboot, or the xbl.img from its firmware package
xbl.img -> Binaries/ishtar/   (UEFIReader: the DXE drivers and the RawFiles)
```

The parts of the port that are this phone's:

| What | From where |
|---|---|
| `files/Binaries/ishtar/` | the phone's `xbl.img`, with UEFIReader |
| `files/Resources/DTBs/ishtar.dtb` | the phone's `vendor_boot` (or `adb pull /sys/firmware/fdt`) |
| `files/Resources/Configs/ishtar.toml` | the UEFI FD's base and size (from the phone's `uefiplat.cfg`) |
| `files/Platforms/Xiaomi/ishtarPkg/Library/MemoryMapLib/MemoryMapLib.c` | the phone's `uefiplat.cfg` |
| `files/Platforms/Xiaomi/ishtarPkg/Library/ConfigurationMapLib/ConfigurationMapLib.c` | the phone's `uefiplat.cfg` |
| `files/Platforms/Xiaomi/ishtarPkg/Include/APRIORI.inc`, `DXE.inc` | the order of the DXE drivers in the phone's `xbl.img` |
| `files/Platforms/Xiaomi/ishtarPkg/Include/RAW.inc` | the phone's panel XML, `SecParti.cfg`, `uefipil.cfg` |

**The four places the FD's address has to agree**: `ishtar.toml`'s `uefi_fd.base`/`size`, the
memory map's `{"UEFI FD", ...}`, the `.dsc`'s `PcdCPUCoresStackBase`, and `mkxnuimg.py`'s
`FD_BASE`/`FD_SIZE`. If they disagree, the UEFI does not start or the loader does not find the
kernel.

The parts that are shared with `nuwaPkg` (the same SoC): the SoC package (`KailuaPkg`), the
ACPI tables, the `XnuLoader.[ch]` bridge and the `BootShim.S` patch that copies our "XNUP"
container to 0xF0000000.

### 4. The kernel's drivers, one at a time

The drivers are in `xnu/files/bsd/dev/hakios_*.c`. Each file's head says where its numbers come
from. In order of how much work they are:

| Driver | What changes | How it is checked |
|---|---|---|
| `hakios.ufshc.c` | **nothing**: the UFS host controller's base and its registers are the same | the kernel finds the LUNs by reading the GPT |
| `hakios.ufs.c` | the GPT layout constants (`UFS_DARWIN_FIRST`, `UFS_DARWIN_BLOCKS`, `UFS_WRITE_FIRST`) and the partition's name | on the phone: `adb shell df` and the partition table |
| `hakios.adsp.c` | the SMEM, the command DB, the RPMh controller, the ADSP's memory and its region | on the phone: the sound |
| `hakios.wifi.c` | the same, the WPSS's memory, the radio's registers (WCN7850, not WCN6750) | on the phone: the Wi-Fi |
| `hakios.cpufreq.c` | the EPSS's base and **the map from the cores to the frequency domains** (this SoC has four clusters and three domains) | on the phone: the frequency in `sys/devices/system/cpu` |
| `hakios.goodix.c` | the SPI serial engine, the GPIO numbers, the touch controller, the panel's size | on the phone: the touch |
| `hakios.haptic.c` | the I2C controller, the GPIO numbers, the motor | on the phone: the vibration |
| `hakios.camera.c` | the whole sensor table: five sensors instead of four, with their own CCI, GPIO, MCLK and CSIPHY | on the phone: the camera app |
| `hakios.adreno.c` | the most: A740 is an A7xx, a different architecture from the A6xx | on the phone: the picture |
| `hakios.ipa.c`, `hakios.mpss.c` | the IPA v5.5: see below | on the phone: the modem |

### 5. The IPA: the big one

SM7325 is IPA v4.11; SM8550 is IPA **v5.5**. Nothing in the data path can be passed as a
boot-arg; it is all in the source. What changes:

**The registers** (`hakios.ipa.c`) -- the offsets move:

| Register | v4.11 | v5.5 |
|---|---|---|
| `COMP_CFG` | 0x3c | 0x48 |
| `CLKON_CFG` | 0x44 | 0x50 |
| `ROUTE` | 0x48 | 0x54 |
| `SHARED_MEM_SIZE` | 0x54 | 0x5c |
| `FILT_ROUT_HASH_FLUSH` | 0x14c | 0x404 |
| `LOCAL_PKT_PROC_CNTXT` | 0x1e8 | 0x478 |
| `IPA_TX_CFG` | 0x1fc | 0x488 |
| `IDLE_INDICATION_CFG` | 0x240 | 0x4a8 |
| `QTIME_TIMESTAMP_CFG` | 0x24c | 0x4ac |
| `TIMERS_XO_CLK_DIV_CFG` | 0x250 | 0x4b0 |
| `TIMERS_PULSE_GRAN_CFG` | 0x254 | 0x4b4 |
| the source resource groups | 0x400 | 0x500 |
| the destination resource groups | 0x500 | 0x600 |
| `ENDP_INIT_RSRC_GRP` | 0x838 | 0x1038 |

**The GSI** (`hakios.ipa.c`) -- the whole register window moves:

| | v4.11 | v5.5 |
|---|---|---|
| `CH_CNTXT` | 0xf000 | 0x14000 |
| `EV_CNTXT` | 0x10000 | 0x1c000 |
| `CH_DOORBELL` / `EV_DOORBELL` | 0x11000 / 0x11100 | the v5.0 places |
| `GSI_STATUS` | 0x12000 | 0x25000 |
| `CH_CMD` / `EV_CH_CMD` | 0x12008 / 0x12010 | 0x25008 / 0x25010 |
| the gap between two execution environments | 0x4000 | 0x12000 |

`GSI_FROM` (0xc000) and `GSI_SIZE` (0x7000) in `hakios.ipa.c` have to grow to cover 0x14000 to
0x25300.

**The channels and the endpoints** -- the modem's own numbers:

| Endpoint | v4.11 (channel/endpoint) | v5.5 |
|---|---|---|
| the command channel | 5 / 7 | 12 / 14 |
| the LAN receive | 14 / 9 | 13 / 16 |
| the modem's transmit | 2 / 2 | 11 / 2 |
| the modem's receive | 7 / 16 | 1 / 23 |
| the modem's transmit TLV count | 16 | 25 |

**The local memory** (`hakios.mpss.c`, `ipa_memory_init()`) -- the canary table is the IPA
version's, and every offset in it moves: the v4 filter at 0x288 becomes 0x1288, the v4 route at
0x488 becomes 0x1488, the modem's header at 0x688 becomes 0x1708, and the table grows new
entries (the AP's own header, the statistics, the NAT table, the PDN configuration).

**The resources** -- v5.5 has six source groups and eight destination groups (v4.11 had three of
each), the endpoint's resource group is three bits wide instead of two, and the QSB is
programmed differently (no limit on the writes, twelve on the reads).

Where to read all of this: Linux's `drivers/net/ipa/` --
`data/ipa_data-v5.5.c` (the endpoints, the memory and the resources),
`reg/ipa_reg-v5.5.c` (the registers) and `reg/gsi_reg-v5.0.c` (the GSI). They are the same
numbers the kernel here has to use.

### 6. Without the IPA first

The IPA is the last piece, not the first: the modem's control plane (its power up, the SIM, the
network registration, the signal strength) does not go through it. The kernel's arguments can
leave the data path off:

```
modem=1 modem_ipa=0 modem_ipa_fw=0
```

With those, `hakios.mpss.c` brings the modem up and `hakios.qmi.c` can ask it what it sees, which
is enough to tell that the port works before the data path is written.

## The order that works

1. the build (done)
2. the device tree and the addresses (done, needs the phone)
3. the UEFI from the phone's `xbl.img`, so that the loader and the kernel boot at all
4. the touch and the display, so that there is something to look at
5. the CPU's frequency, the sound, the Wi-Fi
6. the modem's control plane (no IPA)
7. the GPU
8. the cameras and the haptics
9. the IPA's data path

## Running it

```sh
make firmware                       # the phone's firmware -> fw-*/
make phone ARGS="..." SECS=600      # a session on the phone, then back to Android
```

`DEVICE=ishtar` selects this device's directory; the default is still `poco-x5-pro`. Nothing is
written to the phone: the loader is booted into memory with `fastboot boot`, and the phone returns
to its own Android when the session ends.
