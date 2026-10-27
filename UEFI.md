# ishtar 的 UEFI：从手机固件到可启动镜像

本文记录把手机自己的 UEFI 驱动装配成一个可 `fastboot boot` 的固件卷的完整流程，以及每一步
踩到的坑。全部在主机侧完成，真机只做 `fastboot boot`（纯内存）。

## 0. 结论

| 项 | 结果 |
|---|---|
| 固件卷 | `SILICIUM_UEFI.fd`，3,145,728 B（`0x300000`），153 个 FFS |
| 启动镜像 | `ishtar-boot.img`，1,687,552 B，`ANDROID!` v1 |
| 真机 | ABL 接受镜像（`Sending/Booting OKAY`），bootloader 在约 45 ms 后交出控制，镜像持续运行 ≥60 s 不返回 |

## 1. 原料

| 材料 | 来源 | 规格 |
|---|---|---|
| UEFI 固件卷 | 手机 `uefi_a` 分区（`adb root`，`dd` 读取） | 5,242,880 B，FV `0x2CD000` @ `0x1000` |
| 设备树 | 官改包 `images/vendor_boot.img` 内首个 FDT | 464,090 B |
| Mu-Silicium 源码 | `codeload` tarball（**不要用 git clone**，见 2.1） | — |

## 2. 构建环境

### 2.1 用 tarball，不用 git clone

`git clone` 在本链路被限速（38 MB 后停滞），`codeload` 可达 5 MB/s：

```
https://codeload.github.com/<owner>/<repo>/tar.gz/<commit>
```

### 2.2 子模块必须按钉住的提交取

Mu-Silicium 的 `.gitmodules` 只给分支，实际钉的是具体提交。取分支最新会导致它自带的补丁
（如 `Resources/MuPatches/AsmMacroLib.patch`）因上下文差异打不上。钉住的提交用
`api.github.com/repos/<repo>/contents/<path>` 的 `sha` 字段查询。

需要的外部树：

| 路径 | 仓库 | 说明 |
|---|---|---|
| `Mu_Basecore` | microsoft/mu_basecore | Mu 核心，含 BaseTools |
| `Common/Mu` | microsoft/mu_plus | `MsCorePkg`、`MsWheaPkg` 在此 |
| `Common/Mu_OEM_Sample` | microsoft/mu_oem_sample | — |
| `Silicium-ACPI` | Project-Silicium/Silicium-ACPI | — |
| `Mu_Basecore/MdePkg/Library/MipiSysTLib/mipisyst` | MIPI-Alliance/public-mipi-sys-t | `.dec` 引用其 include |
| 其余 8 个 | cmocka / oniguruma / brotli / googletest / subhook / libfdt / libspdm | `tools/fetch-submodules.py` 一次取全 |

### 2.3 两处补丁

1. `build_uefi.py` 的 `update_local_repo()`：tarball 解出的树没有 `.git`，`git pull` 与
   `git submodule update` 必然失败，改为直接返回。
2. `Mu_Basecore/BaseTools/Plugin/OverrideValidation/OverrideValidation.py`：
   `override_detect_process()` 对 `filepath is None` 调用 `os.path.normpath` 抛异常，整轮构建
   中止；加一处空值保护。

### 2.4 依赖

`./setup_env.sh -p apt`（装 `edk2-pytool-extensions` 等）+ `mono`（`mu_nasm` 需要）+
`gcc-aarch64-linux-gnu`、`nasm`、`clang`、`lld`、`mtools`。

## 3. 建 ishtarPkg

`Platforms/Xiaomi/nuwaPkg` 是小米 13 Pro（同 SM8550）的模板，复制后全量替换 `nuwa`→`ishtar`、
`NUWA`→`ISHTAR`，并改 `FdtBlob/sm8550-xiaomi-ishtar.dtb`。

`Resources/Configs/ishtar.toml` 沿用 nuwa 的 FD 配置（对本机同样正确）：

```toml
[uefi_fd]
base = 0xA7100000
size = 0x300000
```

## 4. 把手机的驱动放进 Binaries

`tools/ffs-extract.py` 把固件卷拆成 EDK2 期望的二进制树：

```
Binaries/ishtar/<Name>/<Name>.efi      PE32 节，原样
Binaries/ishtar/<Name>/<Name>.inf      BASE_NAME / FILE_GUID / MODULE_TYPE（取自 FFS 类型）
Binaries/ishtar/RawFiles/<Name>        面板 XML 等数据文件
```

结果：**98 个驱动 + 57 个数据文件（其中 47 个面板 XML）**。

`nuwaPkg` 的 `Include/*.inc` 仍写厂商路径（`Binaries/<dev>/QcomPkg/Drivers/TzDxe/TzDxeLA.inf`），
`tools/fix-include.py` 按名字把它们改写到扁平布局，并保留原有顺序（DXE 分发顺序有语义）。
厂商名与 UI 名不一致的 12 个用别名表处理，例如 `ChipInfoDxe`→`ChipInfo`、`HALIOMMUDxe`→`HALIOMMU`、
`PmicDxeLa`→`PmicDxe`、`TLMMDxe`→`DALTLMM`、`XhciPciEmulationDxe`→`XhciPciEmulation`。

## 5. 设备树里的 `splash_region`

`vendor_boot` 的 DTB **没有** `splash_region`。补一个保留区（1440×3200、stride 5760 →
18,432,000 B = `0x1194000`），并且**必须同时放进 `Platforms/Xiaomi/ishtarPkg/FdtBlob/`**——
UEFI 用的是固件卷里嵌入的那份，不是启动镜像末尾那份：

```dts
splash_region@b8000000 {
    reg = <0x00 0xb8000000 0x00 0x1194000>;
    no-map;
};
```

## 6. 构建与打包

```sh
cd ~/work/mu-src
python3 build_uefi.py -d ishtar -r RELEASE
# -> Build/ishtarPkg/RELEASE_CLANGPDB/FV/SILICIUM_UEFI.fd          (3,145,728 B)
# -> Build/ishtarPkg/RELEASE_CLANGPDB/FV/SILICIUM_UEFI.fd-bootshim.gz
```

启动镜像：`kernel = gzip(BootShim + FD)`（构建已产出 `.gz`），末尾接 DTB。

```sh
cat SILICIUM_UEFI.fd-bootshim.gz ishtar.dtb > kernel-dtb.bin
python3 mkbootimg.py --kernel kernel-dtb.bin --header_version 1 --pagesize 4096 -o ishtar-boot.img
```

真机：

```sh
fastboot boot ishtar-boot.img      # 纯内存；失败时 fastboot reboot 回原系统
```

## 7. 验证方法（无屏幕时）

`fastboot devices` 在镜像运行时**仍然**列出设备（bootloader 的 USB 枚举不会消失），不能用来判断。
用 `fastboot getvar product`：跳转到镜像后 bootloader 不再应答，命令失败即为"已接管"。


## 8.1 显示没有起来的排查记录

| 实验 | 观察 | 结论 |
|---|---|---|
| 原样驱动启动 | 接管后运行数分钟，屏幕保持 ABL 的 fastboot 画面 | UEFI 能跑，显示未初始化 |
| 换 `nuwa` 的 `DisplayDxe.patched.efi`、`PmicDxeLa.patched.efi` | 无变化 | 补丁版不足以点亮 |
| 从固件卷移除 `DisplayDxe` | 仍长时间运行 | 不是卡死，是初始化失败后返回 |
| `DisplayDxe` 排到分发队列末尾 | 无变化 | 不是分发顺序造成的依赖未就绪 |
| 自写 `TestFbDxe` 向 `0xB8000000` 整片填 0xFFFF00FF | 屏幕无任何变化 | **该地址不是面板当前的扫描缓冲**；`splash_region` 只有在 DisplayDxe 重新配置 DSI 之后才会被扫出去 |

由此确定：`0xB8000000` 是"配好之后"的缓冲，不是 ABL 正在显示的那块。要出画面，必须先由显示驱动
把面板重新初始化，单纯写内存无效。

### 未解决的结构问题：DEPEX

固件卷里 71 个驱动带 DEPEX 节，导出为 PE32 + 二进制 INF 后丢失，等于全部无条件立即分发。
EDK2 的 FDF 不接受 `SECTION DEPEX`（`Unknown section type 'DEPEX'`），依赖表达式只能来自 INF 的
`[Depex]`，而那是 **表达式语言**（`BEFORE/AFTER/PUSH/AND/OR/NOT`），不是二进制块。把原始字节反解成
表达式需要正确的栈语义（首次尝试在 `DisplayDxe` 上得到 9 个 GUID 后接 8 个 `AND` 再接 `FALSE`，
不合法），因此没有采用。两条路：把转换器写对，或按参考做法直接给两个显示相关驱动打机器码补丁。

## 8. 尚未完成

| 项 | 说明 |
|---|---|
| 载荷桥接 | Mu-Silicium 上游没有 XNU 载荷（XNUP）的 DXE 桥接，镜像里的 Bds 只会进自带的启动菜单。要让 `xnuloader/loader.efi` 被拉起，需要补一个 DXE 驱动在 `0xF0000000` 找载荷并跳转，或把 loader 作为 FAT 卷里的 EFI 应用嵌入固件卷 |
| 9 个驱动补丁 | 参考记录显示显示相关的 IOMMU 域、面板复位、DSI 初始化需要按 nuwa 的补丁修改；当前用的是手机原样驱动，显示是否点亮未验证 |
| 触摸 | Goodix GT9916，驱动未接入 |
