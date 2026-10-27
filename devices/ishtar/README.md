# Device: Xiaomi 13 Ultra (ishtar)

Everything in HakiOS that belongs to one phone is here. The kernel, loader and user space above
know nothing about the phone: addresses, interrupts, power rails and firmware come from its device
tree and its Android. A port to another Qualcomm phone is another directory like this one.

| What | Where |
|---|---|
| SoC | Qualcomm Snapdragon 8 Gen 2 (SM8550-AB, "kalama" in the device tree) |
| GPU | Adreno 740 (A7xx -- a different architecture from the first phone's A6xx) |
| Storage | UFS 4.0 |
| Display | 1440x3200 LTPO AMOLED |
| UEFI for the phone | `uefi/`: a port of Mu-Silicium (a patch and files; `apply.sh` clones and applies, `export.sh` saves) |
| Prebuilt UEFI images | `prebuilt/`: `SILICIUM_UEFI.fd`, `BootShim.bin`, the device tree `device-tree.dtb` (the phone's Android kernel's), `ramdisk` |
| The phone's firmware | **not in the repository**: `pull-firmware.sh` pulls it off your phone over `adb` into `fw-*/` at the top |
| Tools | `tools/` |

## Status

This port is **not finished**. What is done and what is not:

| Done | Not done |
|---|---|
| The SoC address generator reads an SM8550 device tree (`tools/soc-args.py`, tested against `reference-sm8550.dts`) | The IPA data path: SM8550 is IPA v5.5, the first phone is v4.11 -- different registers, channels and memory map |
| The UEFI port's skeleton (`uefi/`), based on Mu-Silicium's `nuwaPkg` (Xiaomi 13 Pro, the same SoC) | The UEFI binaries from this phone's own `xbl.img` (they must come from the phone) |
| The device tree, the firmware and the SoC addresses pulled off the phone by script | The GPU: Adreno 740 is A7xx, a different architecture from the first phone's A6xx |
| The address-carrying drivers read their addresses from boot-args where the first phone allowed it | The touch, the cameras, the haptic motor, the audio and the Wi-Fi: all different on this phone |

Read `PORTING.md` for the order to work through and for what each step needs.

## Firmware

```sh
devices/ishtar/pull-firmware.sh      # the phone in Android, on adb
```

Pulls the GPU (`fw-gpu/`), Wi-Fi (`fw-wifi/`), the audio DSP (`fw-audio/`, battery and charging
come through it), the vibration motor (`fw-haptic/`), the modem (`fw-modem/`, with `image/` for its
TFTP) and the cameras (`fw-camera/`). All of it is the vendor's and stays out of git.

## The SoC addresses

The kernel's modem and IPA drivers carry the first phone's register and memory addresses as
defaults and take any that differ from boot-args `soc_*` (`hakios.mpss.c`, `hakios.ipa.c`, and
`soc_override()` in the first). To bring up this phone, pull its own device tree and turn it into
those arguments:

```sh
devices/ishtar/pull-soc.sh      # adb pull /sys/firmware/fdt, then tools/soc-args.py -> devices/ishtar/soc.args
```

The run scripts append `devices/<name>/soc.args` to the kernel command line automatically
(`SOC_ARGS=` to point elsewhere).

### Every soc_* argument

What `tools/soc-args.py` reads from a phone's device tree, and where each comes from. The values
are what SM8550 gives; the first phone's (the POCO X5 Pro's) are the kernel's built-in defaults, so
a port passes only what differs.

| Argument | Device-tree source | SM8550 value |
|---|---|---|
| `soc_ipa_base` | the IPA's `ipa-reg` (the registers; the first phone's tree names the region `ipa-base` and the registers are 0x40000 into it) | `0x3f40000` |
| `soc_gsi_base` | the IPA's `gsi` | `0x3e04000` |
| `soc_ipa_sram` | the IPA's `ipa-shared` | `0x3f50000` |
| `soc_ipcc` | `qcom,ipcc` reg | `0x408000` |
| `soc_aoss` | the AOSS QMP mailbox reg | `0xc300000` |
| `soc_rsc` | `qcom,rpmh-rsc` reg drv-2 (the apps DRV) | `0x17a20000` |
| `soc_apps_smmu` | the SMMU the IPA's iommus point at | `0x15000000` |
| `soc_cmd_db` | the reserved-memory `qcom,cmd-db` | `0x81c60000` |
| `soc_mpss_mem` | the reserved-memory `mpss-region` | `0x8a800000` |
| `modem_ipa_fw_at` | the reserved-memory `ipa-gsi-region` | `0x9b090000` |
| `soc_smem` | the reserved-memory the /soc/qcom,smem points at | `0x81d00000` |
| `soc_imem` | `qcom,msm-imem`, rounded down to its 2 MB block | `0x14600000` |
| `soc_ipa_stream` | the IPA's iommus, the application processors' stream | `0x4a0` |
| `soc_ipa_stream_uc` | the IPA's iommus, the modem's own processor's stream | `0x4a2` |
| `soc_pas_mpss` | `qcom,mss` `qcom,pas-id` | `0x4` |
| `soc_pas_ipa` | `qcom,ipa_fws` `qcom,pas-id` | `0xf` |
| `soc_ipa_fw` | `qcom,ipa_fws` `qcom,firmware-name` | `kalama_ipa_fws` |

The values above are from upstream Linux's `sm8550.dtsi` and from `reference-sm8550.dts` in this
directory; the ones that come off the phone itself (`pull-soc.sh`) are the ones to trust.

### What is still hardcoded (IPA-version specific)

The IPA's SRAM region layout, the SMEM filter-table item (`ipa_4_11_mem_part`), the resource
groups and the Qtime values the IPA is programmed with are the IPA **version**'s, not the phone's.
SM7325 is IPA v4.11; SM8550 is IPA **v5.5**, so all of these change and none of them can be
passed as boot-args. This is the largest single piece of work in the port: see `PORTING.md`.
