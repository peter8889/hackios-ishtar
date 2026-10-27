# hackios ishtar (Xiaomi 13 Ultra)

本仓库为 [hackios-xnu-kernel](https://github.com/oosexgang/hackios-xnu-kernel) 的移植分支，目标设备为
小米 13 Ultra（`ishtar`，SM8550-AB "kalama"）；参考设备为 POCO X5 Pro（`redwood`，SM7325）。

## 1. 运行约束

| 项 | 规定 |
|---|---|
| 真机写入 | 禁止：`fastboot flash` / `erase` / `format` / `set_active` / GPT 修改 / `ufs_write=1` / `var_store=1` |
| 真机允许 | `fastboot boot`（RAM 载入）、`fastboot getvar`、`adb pull`、`adb shell` 只读命令 |
| 数据分区 | 不触碰 `userdata` / `metadata` / `super` / `persist` / `misc` |
| bootloader | 已解锁（`unlocked: yes`），不再变更 |

## 2. 状态

| 路径 | 状态 | 判据 |
|---|---|---|
| QEMU（aarch64 TCG） | iOS 16.5 用户态至主屏，可交互 | `logs/` 截图 1125×2436，18281 色 |
| 真机 ishtar | 未启动 | 无可用 UEFI 固件 |

## 3. 已验证产物

| 产物 | 规格 | 位置 |
|---|---|---|
| 内核 | `mach.development.bcm2837`，15,290,096 B，Mach-O arm64 | `xnu-src/.../BUILD/obj/DEVELOPMENT_ARM64_BCM2837/` |
| 驱动 | 35 个 `hakios.*.o` | 同上 |
| 用户态镜像 | `root.apfs` 5,447,680 B；`system.apfs` 2,482,319,360 B | `userland/` |
| 设备树 | `fdt.dtb` 901,987 B（真机） | 采集产物，不入库 |
| UEFI 固件卷 | `uefi_a` 分区 5,242,880 B，FV `0x2CD000` @ `0x1000` | 同上 |

## 4. 真机参数

`devices/ishtar/soc.args`（来源：`/sys/firmware/fdt`）：

| 参数 | 值 | 参考树值 | 差异 |
|---|---|---|---|
| `soc_ipa_base` | `0x3e40000` | `0x3f40000` | 参考树错误 |
| `soc_gsi_base` | `0x3e04000` | 同 | — |
| `soc_mpss_mem` | `0x89800000` | `0x8a800000` | 参考树错误 |
| `soc_ipa_fw` | `ipa_fws` | `kalama_ipa_fws` | 参考树错误 |
| `soc_smem` | `0x81d00000` | 缺 | — |
| `modem_ipa_fw_at` | `0x9b090000` | 同 | — |
| `soc_ipcc` / `soc_rss` / `soc_apps_smmu` / `soc_cmd_db` / `soc_imem` / `soc_ipa_stream` / `soc_ipa_stream_uc` / `soc_pas_ipa` | 与参考树一致 | — | — |

平台常量（`xnuloader/loader.c`，`platform_ishtar`）：

| 项 | 值 |
|---|---|
| `io_base` / `io_size` | `0x00400000` / `0x3FC00000` |
| `gic_dist` / `gic_redist` | `0x17100000` / `0x17180000` |
| `cores` / `core_shift` | 8 / 8 |
| `small_cores` | `0x07` |
| `fb_base`（GOP，平台识别依据） | `0xB8000000` |
| 面板 | 1440×3200，stride 5760 B |

分区表：128 项；无 `darwin`。`xbl_a` 8,388,608 B；`boot_a` 201,326,592 B；`vendor_boot_a` 100,663,296 B；
`modem_a` 469,762,048 B；`uefi_a` 5,242,880 B。

## 5. 内核侧改动

| 文件 | 改动 | 原因 |
|---|---|---|
| `xnuloader/loader.c` | ramfb 请求不再以回读 `control` 判定成功 | QEMU 在 MMIO 写内完成 DMA 并清零该字；回读为缓存旧值，判定失败后 `SCREEN` 保留固件 800×600 与旧缓冲地址，内核将画面写入非显示内存 |
| `xnuloader/loader.c` | 新增 `platform_ishtar`，按 `fb_base == 0xB8000000` 选择 | 真机平台参数 |
| `xnuloader/build.sh` | `PHONE_WIDTH` / `PHONE_HEIGHT` 编译期可设 | 面板尺寸 |
| `userland/src/inject_sb.c` | `also_in_16_7_16[]` 14 项地址表，校验接受 16.5 与 16.7.16 | 16.7.16 共享缓存中同名方法地址全部位移 |
| `tools/soc-args.py` | SoC 无关化（compatible 按族匹配、reg 按 `#address-cells` 解析、保留内存按内容定位） | SM7325 / SM8550 两棵树 |
| `xnu-deps/setup.sh` | `tar --wildcards` 位置；`mig` 保留 `-I <path>`；目标三元组改 `arm64-apple-ios16.5` | Linux 构建 |
| `xnu-env.sh` / `xnu-build.sh` | `MIGCC` / `MIGCOM` 显式指向交叉编译器 | mig 默认回落系统 `cc` |
| `.gitattributes` | 强制 `*.sh/*.py/*.c/*.h` 为 LF | Windows 克隆的 CRLF 使脚本不可执行 |

## 6. 构建与运行（QEMU）

```sh
sysimage/fetch.sh                 # 默认 iOS 16.5（20F66）；版本切换见 sysimage/VERSIONS.md
REST=1 GL=1 userland/build.sh     # root.apfs + system.apfs
qemu/run-ios.sh 1800 -display gtk,zoom-to-fit=on
```

启动参数：`cpus=4 gl=1`。分辨率取默认 1125×2436。

## 7. 已知缺陷

| 现象 | 条件 | 状态 |
|---|---|---|
| guest 死锁：日志中途截断、屏幕冻结、CPU 占用约 190%、无 panic | `cpus=8`；或 `tb-size=1G` 且移除 wifid | 未修复；`cpus=4` + 默认 `tb-size` 可规避 |
| 启动标志出现后转黑，日志继续、屏幕单色 `#000000` | SpringBoard 拉起 `WallpaperKit.CollectionsPoster` 之后 | 未修复；重启可恢复，非必然复现（同一镜像曾到主屏） |
| 黑屏 | `fbscale=1`（375×812）或 `fbscale=2`（750×1624） | 未修复；仅默认 1125×2436 可用 |
| SpringBoard 阻塞于 FrontBoard 同步 XPC | iOS 16.7.16 用户态 | 未修复 |
| `check_all_exports` 失败 | `make kernel` 后置校验 | 未修复，绕过方式为手工 `mkpayload.py` |

## 8. 真机待办

| 项 | 依赖 | 状态 |
|---|---|---|
| UEFI（`ishtarPkg`） | Mu-Silicium 无 ishtar 平台；需以 `nuwaPkg` 为模板 + `uefi_a` 内 98 个 DXE 驱动 + 47 个面板 XML + `DisplayDxe` DSI 补丁 | 未开始 |
| 显示 | UEFI 线性帧缓冲（`splash_region`），不依赖 Adreno | 未开始 |
| 触摸 | Goodix GT9916，I2C `0x5d`，reset gpio 24，irq gpio 25 | 未开始 |
| GPU | Adreno 740（A7xx），与 `hakios.adreno.c` 的 A6xx 不同架构 | 未开始 |
| IPA | v5.5，`modem_ipa=0` 可先绕开数据面 | 未开始 |

## 9. 外部项目边界

与本仓库并行存在 UniXNU（iPadOS 17 / 组件 catalog 架构）的 ishtar 移植。两者代码与启动产物不共享；
本仓库取用的仅为设备事实（寄存器基址、面板参数、ABL 行为）与厂商固件。
