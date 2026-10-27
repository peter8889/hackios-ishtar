# 交接日志 —— HakiOS 移植到小米 13 Ultra (ishtar / SM8550)

> 交接给下一班模型/人。日期：2026-10-27。  
> 仓库：`C:\Users\818\WorkBuddy\2026-10-27-04-29-38\hakios`（上游 <https://github.com/oosexgang/hakios-os）>  
> WSL 内的构建树：`~/work/hakios`（rsync 同步，**不要**反向覆盖 Windows 侧的构建产物）

---

## 0. 用户底线（硬约束，务必遵守）

> **"要确保完全不损害我澎湃系统正常启动和保留所有数据的前提下进行，这个是底线"**

据此，以下操作**一律不得**在用户手机上执行，除非用户明确逐条确认：

| 禁止                             | 原因                             |
| ------------------------------ | ------------------------------ |
| `fastboot flash` 任何东西          | 会写入闪存分区                        |
| **创建 / 修改 `darwin` 分区**（改 GPT） | 唯一真正会威胁澎湃系统与数据的操作；仓库不提供脚本，风险极高 |
| `ufs_write=1`                  | 开启内核写闪存（`/dev/rufs_darwin`）    |
| `var_store=1`                  | 数据卷持久化，会写 darwin 分区            |
| 解锁 bootloader                  | **已解锁，无需再动**（用户 2026-10-27 确认） |

安全的默认姿态：**只读采集**（`adb pull`）+ **QEMU 仿真**（完全不碰手机）。  
HakiOS 启动方式是 `fastboot boot`（载入 RAM），不刷写；系统镜像走 `./xl ramdisk` 进 RAM。  
`ufs_write` 默认关闭时，内核不提供任何可写分区，块设备一律 `EROFS`。

---

## 1. 任务目标

把 HakiOS（跑 iOS 16.5 用户态的定制 XNU 内核）移植到用户的小米 13 Ultra  
（`ishtar`，Snapdragon 8 Gen 2 / SM8550-AB），第一台参考机是 POCO X5 Pro（`redwood`，SM7325）。

**当前结论：移植尚未完成，真机跑不起来。** 详见第 4 节。

---

## 2. 已完成且已验证的工作

### 2.1 Linux 构建环境打通 ✅ 内核编译成功

WSL Ubuntu 24.04 上产出了 `mach.development.bcm2837`（15,290,096 字节，Mach-O 64-bit arm64），  
35 个 HakiOS 驱动（`hakios.*.o`）全部编译进内核。

**修了 5 个真实的 Linux 移植缺陷**（都已写入仓库）：

| 文件                   | 问题                                                                                                        | 修法                                                                                                               |
| -------------------- | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `xnu-deps/setup.sh`  | macOS SDK 解包 `tar -xJf file $wild pattern` 中 `--wildcards` 位置错（GNU tar 要求在文件名之前）                          | 改为 `tar -xJf macos-sdk.tar.xz --wildcards 'pattern'`                                                             |
| `xnu-deps/setup.sh`  | `mig` 的选项循环丢弃 `-I <path>` 的**路径值**（只留下 `-I`），导致编译器看不到 include 路径，`.defs` 文件互相找不到（`<mach/std_types.defs>`） | 用内嵌 Python 给 `host/bin/mig` 打补丁，新增 `-I ) cppflags=(... "$1" "$2" ); shift; shift;;`                              |
| `xnu-deps/setup.sh`  | 同上                                                                                                        | 同一个补丁把 `arch=("-target" "${2}-apple-darwin")` 改成 `arm64-apple-ios${XNU_SDK_VERSION:-16.5}`（内核是 iOS 目标，不是 darwin） |
| `xnu-env.sh`         | `MIGCC` 未设置时 `mig` 回落到系统 `cc`（无法交叉编译到 Apple 目标）                                                           | `export MIGCC=${MIGCC:-xnu-clang}` / `export MIGCOM=${MIGCOM:-migcom}`                                           |
| `.gitattributes`（新增） | 仓库在 Windows 克隆时被 `core.autocrlf` 转成 CRLF，`.sh` 在 Linux 下无法执行                                              | 强制 `*.sh/*.py/*.c/*.h/... text eol=lf`                                                                           |

> **注意 `.gitignore` 是白名单式的**（`/*` 忽略根目录一切，只有 `!` 列举的才跟踪）。  
> 所以新增根目录文件（如 `.gitattributes`）**必须同时在 `.gitignore` 里加 `!/文件名`**，  
> 否则 `git status` 根本看不到它、`git add .` 也不会带上。
>
> **CRLF 是本项目最大的隐形坑**。Windows 侧仓库必须 `git config core.autocrlf false` +  
> 新增的 `.gitattributes`。任何时候在 Windows 侧新建/修改脚本后，要转成 LF：
>
> ```bash
> python3 -c "p='<file>'; d=open(p,'rb').read().replace(b'\r\n',b'\n'); open(p,'wb').write(d)"
> ```

**另有两个坑不在代码里，在环境里**（下一班务必知道）：

- `rsync` 同步会**覆盖 WSL 里已编译好的二进制**（`host/bin/migcom`、`unifdef`、`tcsh` 被 Windows  
  侧的旧副本污染 → 段错误 → "missing section headers"）。用 `sync-to-wsl.sh`（工作目录根），  
  它排除了 `xnu-deps/host/`、`xnu-src/` 等构建产物目录。
- 旧的失败运行会在 `xnu-src/xnu-8796.121.2/BUILD/` 下留**残缺生成物**（0 字节的  
  `bsd.syscalls.master`、44 行的 `sysproto.h`）。症状是 `#endif without #if` 或  
  `exported name not in import list`。删掉重生成即可：
  ```bash
  find BUILD -name 'bsd.syscalls.master' -size -1c -delete
  grep -rl 'created from /bsd.syscalls.master' BUILD/ | xargs rm -f
  ```

### 2.2 `tools/soc-args.py` 改造为 SoC 无关 ✅

原版硬编码了 SM7325 的设备树写法。改造后能同时读两种树：

- compatible **按族匹配**：`qcom,ipa` 也匹配 `qcom,sm8550-ipa`（去掉 SoC 型号前缀）
- IPA 区域**按 `reg-names` 取**：`ipa-reg`（SM8550，直接就是寄存器地址）vs `ipa-base`  
  （SM7325，区域起点，寄存器在其后 0x40000）
- **按设备树的 `#address-cells` 解析 reg**：两棵树分别是 1 和 2 个地址单元，  
  多单元时高字在前
- 保留内存节点**按"存什么"找**而非按名字（`cmd_db@` vs `aop-cmd-db-region@`，  
  `mpss@` vs `mpss-region@`，`ipa_gsi@` vs `ipa-gsi-region@`）
- apps SMMU **通过 iommus 的 phandle 定位**（上游树里它叫 `iommu@15000000` 而非 `apps-smmu@`）
- 输出顺序严格保持与首台手机一致（`soc_apps_smmu` 在 `soc_rsc` 之后）
- `sys.stdout.reconfigure(newline='\n')`：输出不随平台改变换行

**验证**：

- `sh tools/soc-args-test.sh` ✅ —— POCO 的 16 项数值**逐字节不变**
- SM8550 参考树输出全部正确（见 `devices/ishtar/soc.args`）

### 2.3 `devices/ishtar/` 设备目录 ✅

| 文件                     | 内容                                                           |
| ---------------------- | ------------------------------------------------------------ |
| `README.md`            | 设备说明、两台手机差异对照表、每个 `soc_*` 的来源与取值表                            |
| `PORTING.md`           | **移植作业指导书**：工作量排序、IPA v5.5 寄存器/端点/内存偏移对照表、UEFI 需要哪些文件、每步怎么验收 |
| `soc.args`             | 由参考设备树生成的 SM8550 地址（15 项）                                    |
| `reference-sm8550.dts` | 精简的 SM8550 设备树，用于无真机时测试生成器                                   |
| `pull-soc.sh`          | `adb pull /sys/firmware/fdt` → 生成 `soc.args`                 |
| `pull-firmware.sh`     | 拉 GPU/WiFi/音频/马达/调制解调器/摄像头固件到 `fw-*/`                        |

### 2.4 iOS 16.7.16 在 16.5 内核上跑通 ✅（2026-10-27，最重要的一条）

**iOS 16.7.16 (20H392) 的未修改用户态，已在本机的 16.5 内核（xnu-8796.121.2）上启动成功。**

launchd、backboardd（service state: running）、SpringBoard、用户会话 (user/501)、日志系统全部起来了。

**为此改了三处**（细节见 `hakios/sysimage/VERSIONS.md`，补丁脚本在 `hakios/xnu/port-16.7/`）：

1. **`bsd/kern/kern_mib.c` 的 `hw.target`**：XNU 用 `PEGetTargetName()` 回答它，而那是问平台专家的
   ——Apple 的 IOPlatformExpert 不在开源里，所以本移植上 `gIOPlatform` 为 NULL，调用失败，
   sysctl 返回 EINVAL(22)。**dyld 需要它，拿不到就退出**，于是 launchd 随之中止：
   `failed to query hardware target: 22`。改法：失败时回退到设备树根的 `target-type`
   （loader 从手机自己的设备树复制的，所以是手机自己的答案：D22AP）。
2. **`iokit/Kernel/IOPMrootDomain.cpp` 的 `hw.targettype`**：XNU 本来就有这个 sysctl
   （`SYSCTL_PROC(_hw, OID_AUTO, targettype, ...)`），但它的 handler 从 IORegistry **service plane**
   的 root domain 属性取，而本移植上没人把设备树根的属性放到那个 plane（设备树挂在 **DT plane**）。
   改法：handler 直接读设备树。
3. **loader 必须用真身份重编**：`xnuloader/mkidentity.sh` 生成的 identity.h 里有 `target-type`，
   loader 通过 `dt_identity()` 把它写进给内核的设备树。**用 placeholder identity 编的 loader
   没有这个属性**，内核就答不出来。（我在这上面绕了很久：先改了内核才发现 loader 是旧的。）

**教训**：`/tmp` 在不同的 `wsl -e` 调用之间**不共享**，调试文件要放在工作目录里。

### 2.5 QEMU 路径在 WSL2 上完全跑通 ✅

用户选的路线（不下载 IPSW）。**已实测**：

```
Darwin Kernel Version 22.5.0: ... xnu-8796.121.2 ... DEVELOPMENT_ARM64_BCM2837
load_init_program: attempting to load /sbin/launchd
Hello from user space on Darwin!
I am process 1, uid 0, console fd 0.
```

即：**UEFI → loader → XNU 内核 → mockfs root → 用户空间程序作为 pid 1 执行**，整条链路通。

- 内核引导到用户空间约 **5–6 秒**（TCG 软件模拟，比预期快）
- `hello` 打印完 `exit(0)` → 内核 panic（init 进程不允许退出）——**这是演示程序的正常终态，不是故障**

**已装好的 WSL 依赖**：`qemu-system-arm` 8.2.2、`qemu-efi-aarch64`（AAVMF 固件）、  
`7zip` 23.01（**必须 23+ 才能读 APFS**，Ubuntu 的 `7zip` 包正好满足，不要装老的 `p7zip-full`）、  
`lz4`、theos（`~/theos`，cctools + iPhoneOS16.5 SDK）、`xnu-deps` 全部构建产物。

**`qemu/run.sh` 已改进**：自动探测 UEFI 固件路径（Arch 的 `/usr/share/edk2/aarch64/` 或  
Debian/Ubuntu 的 `/usr/share/AAVMF/`），不再需要手动设 `QEMU_EFI`/`QEMU_VARS`。

跑法（**注意 `make qemu-open` 会失败**，见第 5 节）：

```bash
cd ~/work/hakios
# 内核（若已构建则跳过）
./xnu-build.sh -j16 -k
# loader 与 hello
PLACEHOLDER=1 xnuloader/mkidentity.sh && xnuloader/build.sh
. ./xnu-env.sh && xnu-clang -arch arm64 -Os -static -nostdlib -ffreestanding \
  -fno-stack-protector -fno-builtin -Wl,-e,_start -Wl,-pagezero_size,0x100000000 \
  -o userland/hello userland/src/hello.c
# payload 并启动
xnuloader/mkpayload.py -o qemu/payload.bin \
  kernel=xnu-src/xnu-8796.121.2/BUILD/obj/DEVELOPMENT_ARM64_BCM2837/mach.development.bcm2837 \
  ramdisk=userland/hello --cmdline='cpus=1'
qemu/run.sh 60
```

---

## 3. 环境与路径速查

| 东西               | 位置                                                          |
| ---------------- | ----------------------------------------------------------- |
| Windows 仓库       | `C:\Users\818\WorkBuddy\2026-10-27-04-29-38\hakios`         |
| WSL 构建树          | `~/work/hakios`（`rsync -a --delete` 同步，脚本 `sync-to-wsl.sh`） |
| theos            | `~/theos`（cctools 在 `~/theos/toolchain/linux/iphone/bin`）   |
| iPhoneOS16.5 SDK | `~/theos/sdks/iPhoneOS16.5.sdk`                             |
| 主机内存             | **16 GB**（WSL 默认只分到 8 GB，`.wslconfig` 未设 `memory`）          |
| 主机 CPU           | i5-14490F，16 核                                              |
| adb / fastboot   | `C:\platform-tools`（用户自带，v37.0.1）                           |
| WSL 发行版          | `Ubuntu-24.04`                                              |

`.wslconfig`（`C:\Users\818\.wslconfig`）当前只有 `processors=16` / `swap=8GB` / 网络设置，  
**没有 `memory` 项**。跑完整 iOS 需要把它加到 12GB 左右。

---

## 4. 移植的真实状态：未完成

### 4.1 拦路虎：IPA 版本不同

|         | POCO X5 Pro           | 小米 13 Ultra             |
| ------- | --------------------- | ----------------------- |
| SoC     | SM7325（yupik），ARMv8.4 | SM8550-AB（kalama），ARMv9 |
| **IPA** | **v4.11**，GSI 2.11    | **v5.5**，GSI 5.5        |
| GPU     | Adreno 642L（A6xx）     | Adreno 740（A7xx，新架构）    |
| 摄像头     | 4 颗                   | 5 颗                     |

**IPA v4.11 → v5.5 是最大工作量**，20+ 个寄存器偏移、GSI 整个窗口地址、4 个端点的通道号、  
本地内存 canary 表、资源组全部要重写，**没有任何 boot-arg 能绕过**。  
逐项对照表已写在 `devices/ishtar/PORTING.md`，数据来源是 Linux 的  
`drivers/net/ipa/data/ipa_data-v5.5.c`、`reg/ipa_reg-v5.5.c`、`reg/gsi_reg-v5.0.c`。

好消息：GPU/GCC/IPCC/UFS 控制器/DISPCC/TLMM/AOSS/SMMU 的**基址两台手机完全相同**，  
SMP2P 项号与 IPCC client 号也相同 → UFS 驱动一行都不用改。

### 4.2 第二个拦路虎：UEFI

Mu-Silicium 没有 `ishtar` 平台。需以同 SoC 的 `nuwaPkg`（小米 13 Pro）为模板，  
但**必须从本机自己的 `xbl.img` 提取 UEFI DXE 驱动**（UEFIReader）。  
四个地方的 FD 地址必须一致：`ishtar.toml`、`MemoryMapLib.c`、`.dsc` 的 `PcdCPUCoresStackBase`、  
`mkxnuimg.py` 的 `FD_BASE`/`FD_SIZE`。细节见 `PORTING.md` 第 3 节。

### 4.3 建议的推进顺序

1. 只读采集（不动手机任何状态）：设备树、固件、`xbl.img`
2. UEFI 移植 → 能启动到 loader
3. 触摸 + 显示 → 有画面
4. CPU 频率 / 声音 / Wi-Fi
5. 调制解调器**控制面**（`modem_ipa=0 modem_ipa_fw=0` 绕开数据面，这部分与 IPA 版本无关）
6. GPU
7. 摄像头 + 震动
8. **IPA v5.5 数据面**（最难，放最后）

---

## 5. 已知未解决的问题

### 5.1 `check_all_exports` 失败（阻塞 `make kernel`）

构建内核本体成功，但构建后的 KPI 符号校验失败：

```
exported name not in import list: OSObject::_Dispatch(OSObject*, IORPC)
exported name not in import list: IOService::_Dispatch(IOService*, IORPC)
... (数十条 DriverKit 符号)
make[5]: *** [config/Makefile:121: check_all_exports] Error 1
```

原因：Apple 的 `iig`（DriverKit 接口生成器）是闭源的，仓库用 `xnu-deps/host/bin/iig` 垫片  
从 macOS 13.3 SDK 拷贝预生成头文件。这些头文件声明了 `_Dispatch` 系列方法，  
而 HakiOS 的 `config/Libkern.exports`、`IOKit.exports` 里没有这些符号。

**影响**：不影响内核镜像（`mach.development.bcm2837` 已完整产出），但 `make kernel` /  
`make qemu-open` 会返回失败。  
**绕过办法**（本轮用的）：跳过 make，手工跑 `mkpayload.py` + `qemu/run.sh`（见第 2.4 节）。  
**可能的真修**：给 `config/*.exports` 补上这些符号，或让 iig 垫片用更接近的 SDK 版本。

### 5.2 Windows 侧仓库的 `prebuilt/` 与 WSL 构建树不同步

Windows 侧 `prebuilt/mach.development.bcm2837` 是上游预构建的 16.8 MB 版本；  
WSL 里新构建的是 15.3 MB（差值是未构建的 ath11k Wi-Fi 驱动对象）。  
`git status` 会显示这些二进制被改动。**要不要提交由用户定**。

### 5.3 QEMU 里看不到画面（**已更正：不是 GL 的问题**，2026-10-27 09:50 后重测）

`GL=1` 的镜像早就建好并跑过三次（08:59 / 09:05 / 09:09）。GL 通路本身是健康的：Mesa 软件渲染、
一个 1125×2436 的 IOSurface 当纹理、4 个 shader、**0 个 GL 错误**，backboardd 稳定出帧。

那三张全黑截图**拍早了**：`screen-gl3.png` 的时间戳（09:09）甚至早于 launchd 启动（09:10:48），
`screen-gl2.png` 只比 launchd 晚 1 分 44 秒，而笔记写明锁屏要 2–3 分钟才出来。结论：
**截图时间点必须晚于启动两分钟以上**，否则测的是黑屏的早期启动画面。

真正的黑屏原因，以及已经做掉的一处修复，见 `sysimage/VERSIONS.md` 的
“The injection library, and the addresses it needed”：注入库的 14 个 hook 全是 16.5 的地址，
在 16.7.16 上一个都没挂上；补上 16.7.16 的地址后 SpringBoard 才走到场景创建（现卡在 FrontBoard
的同步 XPC），画面仍未出来。下一个可疑点是 `userland/src/inject.c` 里 backboardd 的两个 vtable
地址（`0x1d5b44520` / `0x1d5b45c58`，同样是 16.5 的）。

### 5.4 `make qemu-open` 不能直接用

因为 5.1，它会在 `make kernel` 阶段就失败。手工步骤见第 2.4 节。  
（在修好 5.1 之前，考虑给 Makefile 加个 `kernel-only` 目标或 `SKIP_EXPORTS_CHECK` 开关。）

---

## 6. 仓库里被本轮修改的文件清单

```
新增：  .gitattributes
新增：  devices/ishtar/{README.md,PORTING.md,HANDOFF.md,soc.args,reference-sm8550.dts,pull-soc.sh,pull-firmware.sh}
修改：  .gitignore                     （加 !/.gitattributes，否则它被 /* 白名单规则忽略、永远提交不了）
修改：  tools/soc-args.py            （SoC 无关化，见 2.2）
修改：  xnu-deps/setup.sh             （tar 参数、mig 补丁，见 2.1）
修改：  xnu-env.sh                   （MIGCC/MIGCOM，见 2.1）
修改：  xnu-build.sh                 （MIGCC/MIGCOM 传给 make）
修改：  qemu/run.sh                  （UEFI 固件路径自动探测）
```

工作目录（**不在仓库里**）：

```
sync-to-wsl.sh           同步脚本（排除构建产物）
rebuild-host-tools.sh    重建 tcsh/unifdef/mig/migcom
fix-unifdef.sh           单补 unifdef
dbg-mig.sh / dbg-migflags.sh   mig 排查用
setup-theos.sh / fix-order.py  工具
HANDOFF.md               本文件
```

---

## 7. 给下一班的建议动作（按优先级）

1. **先决定 `check_all_exports` 怎么修**——它挡着 `make` 的正常流程。  
   建议给 `config/*.exports` 补符号，或加个跳过开关。
2. ~~**把 `.wslconfig` 的 `memory` 加到 12GB**（跑完整 iOS 前必须做）~~ 已完成（`memory=12GB`，
   WSL 内可见 11 GB；`run-ios.sh` 7 GB 的 guest 起得来）。
3. **只读采集真机材料**：连上手机（USB 调试），跑 `devices/ishtar/pull-soc.sh` 与  
   `pull-firmware.sh`；从官方线刷包取 `xbl.img`（**不要**改手机任何状态）。
4. 如果只是想看 iOS 界面：`sysimage/fetch.sh`（7.4 GB）→ `REST=1 userland/build.sh` →  
   `qemu/run-ios.sh`。**先评估 TCG 下的速度**（内核引导 5–6 秒，但用户态会慢很多）。
5. 推进 ishtar 的 UEFI 移植（`PORTING.md` 第 3 节有完整清单）。

---

## 8. 一句话总结

**构建环境已通、内核已编译成功、SoC 地址生成器已 SoC 无关化、QEMU 链路已验证；  
但小米 13 Ultra 的真机移植卡在 IPA v4.11→v5.5 的重写和缺 ishtar 的 UEFI 上，  
且用户在真机上的底线（不写闪存、不动分区表、保留所有数据）要求全程只做只读采集。**
