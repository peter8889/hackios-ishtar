<p align="center">
  <img alt="hackios ishtar" src="assets/logo.png" width="180">
</p>

<p align="center">
  <a href="https://t.me/petegroup"><img alt="Telegram" src="https://img.shields.io/badge/Telegram-%40petegroup-26A5E4?logo=telegram&logoColor=white"></a>
</p>

<p align="center">
  简体中文 | <a href="README.en.md">English</a>
</p>

# hackios ishtar

小米 13 Ultra（代号 `ishtar`，SoC 为高通 SM8550-AB "kalama"）的 hackios 移植，目标是把
**iOS 16.5 用户态**运行在定制 XNU 内核上。本仓库派生自
[hackios-xnu-kernel](https://github.com/oosexgang/hackios-xnu-kernel)，参考设备为
POCO X5 Pro（`redwood`，SM7325）。

工作分为两条线：**QEMU 仿真**验证与硬件无关的软件栈；**真机移植**验证硬件相关的部分。
前者已完成到主屏，后者尚缺一道 UEFI 关卡。所有真机操作以不写闪存、不改分区表为前提，
只允许 `fastboot boot`（纯内存载入）与只读采集。

## 状态

| 路径 | 状态 | 判据 |
| --- | --- | --- |
| QEMU（aarch64 TCG） | iOS 16.5 至主屏，可交互 | 1125×2436，18281 色，10–16 fps |
| 真机 ishtar | 未启动 | 无可用 UEFI 固件 |

| 部分 | 状态 |
| --- | --- |
| 内核、启动链、显示（线性帧缓冲） | 已实现并验证（QEMU） |
| iOS 16.5 用户态、注入库 | 已实现并验证 |
| iOS 16.7.16 用户态 | 部分：SpringBoard 阻塞于 FrontBoard 同步 XPC |
| UEFI（`ishtarPkg`）、触摸、GPU、IPA | 未开始 |

## 本轮结论

**黑屏的根因在 loader 的面板交接。** QEMU 在 fw_cfg 的 MMIO 写内完成 DMA 并清零描述符的
控制字，loader 回读到的是处理器缓存中的旧值，将请求判为失败，于是 `SCREEN` 保留固件的
800×600 与固件缓冲地址；内核据此把 1125×2436 的画面写入无显示的内存。改为"请求写出即
视为完成"后，画面恢复。此缺陷与 iOS 版本、渲染后端无关，所有构建均受影响。

**16.7.16 用户态需要 14 个方法地址的迁移。** 注入库在替换前校验目标方法的地址，14 个地址
全部取自 16.5；在 16.7.16 上逐一被拒绝，激活与开机向导均未接管。拒绝信息同时给出实际地址，
据此建立 `also_in_16_7_16[]` 双版本表，两版均可命中，第三版仍被拒绝。

**分辨率与核数存在硬边界。** 面板仅默认 1125×2436 可用；`fbscale=2`（750×1624）与
`fbscale=1`（375×812）会触发显示路径缺陷。`cpus=8` 会在 guest 内部死锁（日志中途截断、
屏幕冻结、无 panic），`cpus=4` 稳定。

## 真机参数

`devices/ishtar/soc.args` 取自本机设备树（`/sys/firmware/fdt`），修正了参考树的三处错误：

| 参数 | 本机 | 参考树 |
| --- | --- | --- |
| `soc_ipa_base` | `0x3e40000` | `0x3f40000` |
| `soc_mpss_mem` | `0x89800000` | `0x8a800000` |
| `soc_ipa_fw` | `ipa_fws` | `kalama_ipa_fws` |

平台常量（`platform_ishtar`）：GIC `0x17100000` / `0x17180000`，8 核，MPIDR shift 8，
`small_cores 0x07`，显示基址 `0xB8000000`，面板 1440×3200、行跨度 5760 字节。分区表 128 项，
无 `darwin` 分区。

## 结构

| 路径 | 内容 |
| --- | --- |
| `ISHTAR.md` | 移植状态、参数、已知缺陷的完整登记 |
| `devices/ishtar/` | 设备目录：`PORTING.md`、`README.md`、`soc.args`、取数脚本 |
| `xnuloader/` | UEFI loader：平台描述、ramfb 交接、内核载入 |
| `xnu/` | 内核补丁与 `port-16.7/` 的两个 sysctl 脚本 |
| `sysimage/` | iOS 组件获取（版本参数化）、镜像选择、`VERSIONS.md` |
| `userland/` | 用户态镜像构建、注入库、测试程序 |
| `qemu/` | 仿真运行、截图、输入、日志符号化 |
| `tools/soc-args.py` | 由设备树生成 SoC 引导参数（同时支持两代写法） |

## 构建与运行

```sh
sysimage/fetch.sh                 # 默认 iOS 16.5（20F66）；版本切换见 sysimage/VERSIONS.md
REST=1 GL=1 userland/build.sh     # 生成 root.apfs 与 system.apfs
qemu/run-ios.sh 1800 -display gtk,zoom-to-fit=on
```

启动参数 `cpus=4 gl=1`，分辨率取默认值。首次至主屏约 8 分钟；界面绘制由 Mesa 软件光栅化
完成，主机 GPU 不参与。

## 已知缺陷

| 现象 | 条件 | 状态 |
| --- | --- | --- |
| guest 死锁：日志截断、屏幕冻结、CPU 约 190%、无 panic | `cpus=8`；或 `tb-size=1G` 且移除 wifid | 未修复，`cpus=4` + 默认 `tb-size` 规避 |
| 黑屏（仅启动画面） | `fbscale=1`、`fbscale=2` | 未修复，仅默认分辨率可用 |
| SpringBoard 阻塞于 FrontBoard 同步 XPC | iOS 16.7.16 | 未修复 |
| `check_all_exports` 失败 | `make kernel` 后置校验 | 未修复，绕过方式为手工 `mkpayload.py` |

## 文档

- [ISHTAR.md](ISHTAR.md) —— 状态、参数、内核侧改动逐条原因、真机待办
- [devices/ishtar/PORTING.md](devices/ishtar/PORTING.md) —— 工作量排序、IPA v4.11→v5.5 对照表、UEFI 清单
- [sysimage/VERSIONS.md](sysimage/VERSIONS.md) —— 16.7.16 运行所需的 sysctl 与地址表
- [README.upstream.md](README.upstream.md) —— 上游项目说明

## 联系

移植讨论在 Telegram 群 [@petegroup](https://t.me/petegroup)。构建结果与硬件观察请写入
`ISHTAR.md` 或 issue，群组仅作讨论渠道。

## 上游与许可

派生自 [oosexgang/hackios-xnu-kernel](https://github.com/oosexgang/hackios-xnu-kernel)，许可证随上游
（[LICENSE](LICENSE)、[LICENSE.APSL](LICENSE.APSL)）。仓库不包含 Apple 系统文件、IPSW 组件或厂商
固件；相关文件由脚本从本机或官方服务器获取，且不纳入版本控制。
