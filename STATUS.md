# wayne 迁移进度（UniXNU format-2 模式）

更新时间：2026-10-30

## 结论一句话

wayne（小米 6X，SDM660）**已经能用 UniXNU/Mu-Silicium 的 UEFI 固件启动、点亮屏幕、进入 UniXNU 菜单，
并从 eMMC 上的 FAT 卷读到 payload（菜单里有 xnu 条目，音量键可上下移动）**。
下一步是把 DarwinBoot 编进固件卷，让 xnu 条目真正交接给 XNU。

## 已达成（真机验证）

| 项 | 证据 |
| --- | --- |
| **format-2 内核链跑通** | `Build kernel` run `40977839827` success：`kernel.macho` 49.52 MB（补丁 → 组件 → XNU 编译 → 链接 → prelink） |
| **payload + bootimg 链跑通** | run `40983535356` success：`payload.img` 54 MiB、`boot.img` 54.86 MiB，头部 `ANDROID!` v0 / page 4096 / `kernel@0x10008000` / `ramdisk@0x11000000` / `tags@0x10000100`，与 stock 一致 |
| **payload 被 UniXNU 认出** | `fastboot flash cache payload.img` 后启动 1.4 MiB 固件镜像，真机 UniXNU 菜单出现 **xnu 条目**，音量键可上下移动 |
| waynePkg 固件可编译 | `SILICIUM_UEFI.fd` = 3145728 B = 0x300000 |
| UEFI 在真机运行 | 屏幕出现 Silicium **"Si"** logo + 顶部白字；`fastboot devices` 显示 `xnuloader` |
| **UniXNU 菜单** | 内嵌 `UniXNU.inf` + `UniXNUDxe.inf` 后菜单出现（标题 + 列表） |
| format-2 配置可解析 | `out/wayne/ipados-17.7.11-21H461/wayne`，组件 = ArmDTPlatform, ArmCpu, SoftwareAES, RamBlock, XnuPrelink, DarwinBoot |
| 回退安全 | stock boot 备份在 `backup/boot.img`；`backup/` 另有 persist/modemst1-2/fsg/fsc/misc |



## 关键设计决策

1. **不写 wayne 专属 DisplayDxe**：wayne 的 ABL 已经把 nt36672 面板点亮并把
   splash 放在 `0x9D400000`（36 MiB），因此 `USE_CUSTOM_DISPLAY_DRIVER = 0`
   走 `SimpleFbDxe`，直接把 splash 缓冲当 GOP。这是点屏成功的原因。
2. **复用 lavender 的 SDM660 厂商 DXE 二进制**（`Binaries/lavender`）：时钟、PMIC、
   TLMM、USB、eMMC（`SdccDxe`）、UFS 全部同 SoC。内存映射与 lavender 逐项相同
   （含 `Display Reserved 0x9D400000+0x02400000`、`UEFI FD 0x9FC00000+0x300000`）。
3. **boot header 用 v0 / page 4096**：wayne 的 ABL 只接受 stock 形态
   （gz kernel + 追加 DTB），lavender 用的 v1 不适用。为此给 `build_uefi.py`
   的 `[boot_image]` 参数表补了 `pagesize`。

## 仓库状态

| 仓库 | 内容 | 状态 |
| --- | --- | --- |
| `gs240333/Mu-Silicium` | `Platforms/Xiaomi/waynePkg`、`Resources/Configs/wayne.toml`、`Resources/DTBs/wayne.dtb`、`.github/workflows/wayne.yml`（只编 wayne） | 已推送，构建通过 |
| `gs240333/UniXNU-wayne` | 仍是旧的 format-1（clover 派生）内容 | 待替换为本地 `wayne-f2/`（format 2 草案） |
| 待建 `gs240333/UniXNU-sdm660-common` | 本地 `sdm660-soc/`：`soc.toml` + `configs/sdm660.config` + `patches/xnu/series` | 草案 |

## 已知现象

- `fastboot boot` 之后，`fastboot reboot` / `reboot bootloader` 会**再次进入
  xnuloader**（UEFI 的 reset 是热复位，ABL 仍从 DDR 里的镜像启动）。
  要回到 Android 必须**长按电源键 10 秒强制关机**再开机。
- UEFI 的 fastboot 不支持 `continue` / `oem poweroff`。
- 固件里嵌了 UniXNU 之后，USB 不再枚举成 `xnuloader`：BDS 直接按 `BootOrder`
  启动了 UniXNU，所以 `fastboot devices` 会变空，这是正常现象。

## 上游耦合（SDM660 发现的第一个通用坑）

`profiles/os/ipados-17.7.11-21H461/patches/xnu/series` 里的
`zzz-boot-progress.patch`，其 `bsd/kern/bsd_init.c` hunk 以 **sheng 的 PMGR 代码块
作为上下文**：

```
#if defined(XNU_SHENG_PMGR) && XNU_SHENG_PMGR
	extern void sheng_pmgr_run(void);
	sheng_pmgr_run();
#endif
```

也就是说 OS profile 的补丁被绑死在 SM8550 的 SoC 补丁上。任何新 SoC 仓库都必须在
`bsd_init()` 的同一位置插入**逐字相同**的 5 行，否则内核补丁序列在最后一步失败。
已在 `UniXNU-sdm660-common` 的 `sdm660-platform-power.patch` 里按此对齐，并在
README 记录。长期应向 UniXNU 上游提 issue：该 hunk 应改为不依赖具体 SoC 的上下文。

## 下一步

1. 内核：`Build kernel` workflow 跑通 `unixnu build kernel`（当前卡在补丁序列，
   已修 SoC 平台电源钩子，见上）。
2. `build package`（UniXNUPkg）→ `build payload`（`--unique-chip-id` + trust cache）
   → `bootimg`，产出带 payload 的 boot.img，让 UniXNU 菜单里出现 `xnu` 条目并交给
   DarwinBoot。
3. 用 `DarwinBoot` 把 XNU 拉起来：先看入口色带 / panic 屏，再补 `RamBlock` 根。
4. 之后才是 XNU 侧 eMMC（NativeSdhci 类组件）与触摸（focaltech fts @0x38）。

## 复现命令

```powershell
# 1. 固件（CI，含 UniXNU）
gh workflow run wayne.yml -R gs240333/Mu-Silicium
gh run download <run-id> -R gs240333/Mu-Silicium -D wayne-uefi

# 2. 内核 / 配置（CI）
gh run list -R gs240333/UniXNU-wayne

# 3. 真机（不写分区；先冷启动进 fastboot）
tools\platform-tools\fastboot.exe boot wayne-uefi\wayne-uefi\Mu-wayne.img
```


## 真机踩到的三个坑（都已定位）

1. **ABL 的 RAM 启动有尺寸上限**：`fastboot boot` 1.4 MiB 镜像正常；17/25/55 MiB 镜像
   `Booting OKAY` 但**不跳转**，并让 ABL 进入"拒绝一切启动"状态
   （后续任何镜像都回 `Failed to load/authenticate boot image: 00000050`）。
   清状态必须**拔 USB 线 + 长按电源 15 秒**（普通重启只复位，DDR 里的镜像还在）。
   → 因此 payload 不能塞进 boot.img，改放 eMMC 的 `cache` 分区（256 MiB），
   boot.img 只保留 ~1.4 MiB 的固件。这也是 UniXNU 的正常形态（sheng 同样把
   payload 放在分区里，208 MiB）。

2. **刷未签名 boot 镜像会触发 ABL 校验失败**：`fastboot flash boot` 我们的镜像后，
   机器进不了系统也拒绝 RAM 启动；`fastboot erase misc` + 刷回 stock 可恢复，
   但最终仍需一次真正的断电（拔线）。**在 bring-up 阶段不要写 boot 分区**。

3. **ARM64 头 image_size 语义不一致**：Mu-Silicium 的 BootShim 写 `FD_SIZE`，
   UniXNU 的 `bootimg` 要求 `len(shim)+FD_SIZE` 才放行。已在 fork 里改成
   `FD_SIZE + (_Payload - _Head)`，两边的语义都对得上。

## xnu 条目点了没反应的原因

`[payload] loader = "firmware"` 表示由固件里的 **DarwinBoot** 负责加载内核，
而现在的 `waynePkg` 只内嵌了 `UniXNU.inf` + `UniXNUDxe.inf`，**没有 DarwinBoot**。
所以菜单能列出 xnu 条目，选中却什么都不发生。

下一步：把 `UniXNU/DarwinBoot`（revision `3325e352d7df68a9f9ad74832ed94a6acbbd7390`，
`drivers/DarwinBoot`，EDK2 包 `DarwinBootPkg`）克隆进 Mu-Silicium 检出目录，
在 `wayne.dsc` / `wayne.fdf` 里加入 `DarwinBootPkg/Driver/DarwinBoot.inf`，重建 FD。

## 真机里程碑：DarwinBoot → XNU 入口（2026-10-30）

手机屏幕实拍（用户提供）显示 UniXNU 菜单 + DarwinBoot 日志：

```
UniXNU  version 0.1.0
config: \EFI\UniXNU\unixnu.toml
1  xnu

DARWINBOOT: ARM64 va=0xFFFFFFF00427C000 pa=0xA007C000 args=0xA41B4000 entry=0xA31F0488 owned=0x10000000
DARWINBOOT: video base=0x9D400000 display=1 row=4320 width=1080 height=2160 depth=32
DARWINBOOT: command line: -v serial=3 debug=0x14e keepsyms=1
DARWINBOOT: inputs validated; exiting boot services
```

关键结论：

- **payload 从 eMMC `cache` 分区的 FAT 卷加载成功**（`\EFI\UniXNU\unixnu.toml`），说明 UEFI 侧
  eMMC（SdccDxe）→ PartitionDxe → Fat 全链路可用。
- **DarwinBoot 拿到了正确的帧缓冲**：`0x9D400000`、1080x2160、depth 32 —— 正是"复用 ABL
  已初始化 splash 缓冲、不写 wayne 专属 DisplayDxe"这个决策的结果。
- `exiting boot services` 是 DarwinBoot 的最后一行，之后控制权交给 XNU 入口
  （`entry=0xA31F0488`）。屏幕上没有出现内核输出，原因有二：
  1. 第一版内核**没有显示组件**（`GopFramebuffer` 及其设备侧 `build-gop-legacy-display.py`
     被暂时移除，因为该脚本依赖设备专属的内核符号探测）；
  2. `serial=3` 走 UART `ttyMSM0`，但没有接串口线。

## 下一阶段（内核 bring-up）

1. 写 wayne 版 `build-gop-legacy-display.py`（或等价的 ADT `/chosen/video` 注入），把 DarwinBoot
   已经拿到的 `0x9D400000` 帧缓冲交给 XNU `video_console`，这样内核日志能直接显示在屏幕上。
2. XNU 侧 eMMC：把 `CloverSdhci`/`CloverBlock`（同 SDM660 sdhci@0xc0c4000）做成 format-2 组件，
   替换 `RamBlock`；之后再谈 APFS root。
3. 触摸（focaltech fts @0xc175000 addr 0x38）与 FRC/显示时序。
4. 每轮都要注意：**不要写 boot 分区**，ABL 对未签名镜像会让机器进"拒绝启动"状态，
   恢复需要拔线断电。

## 内核 bring-up 二分记录（真机，每行一次构建）

参照对象：`qine233/UniXNU-clover`（同 SDM660 / 同 eMMC）。参数与 ADT 值已逐项照搬：
`chip_id=0x13d`、`owned_memory_size=0x40000000`、`dram_size=0x80000000`（只用低 2GB）、
`armcpu-timer-intid=19`、`boot-progress=2` 与 `offline-legacy-*` 全套。

| 探针（`entry_probe_reset_*`） | 结果 | 结论 |
| --- | --- | --- |
| stage 3（MMU 打开后 10 s 复位） | **重启** | MMU 使能与页表 OK |
| `--reset-after _arm_vm_init --in _arm_init` | **重启** | `arm_vm_init` 正常返回 |
| `--reset-after _bsd_init --in _kernel_bootstrap_thread` | 不重启 | 未到 BSD 初始化 |
| `--reset-before _bsd_init --in _kernel_bootstrap_thread` | 不重启 | 未到 `bsd_init` 调用点 |
| `--reset-before _machine_startup --in _arm_init` | 不重启 | 未到 `machine_startup` 调用点 |
| `--reset-before _PE_init_cpu --in _arm_init` | 不重启 | 卡在 `PE_init_cpu` **之前** |

结论：卡点在 `arm_vm_init` 返回之后、`PE_init_cpu` 之前的两次调用里，即
`PE_init_printf` 或第二次 `PE_init_platform`（`ArmDTPlatform` 的 configure）。
下一步只需再两次构建即可定位到具体那一个。

### 关键发现（来自 clover 源码注释，已照搬修复）

- 上游 `ArmCpu` 把架构定时器中断固定为 **PPI 27**，而 SDM660 的设备树编号是
  `16 + 3 = 19`（`CNTV_CTL_EL0`）。27 这条路永远不触发，所以计时器一次 tick 都不来。
  `drivers/ArmCpu` 里的板级副本通过 `armcpu-timer-intid` 修正；当前**尚未选中**
  （选中后 bootstrap pass 不产出 `startup.o.json`，见下）。
- `panic_screen` 与 stage-4 探针**放不进**内核入口 padding（panic 屏 0xa1f 字节），
  两者只能二选一。
- UniXNU 的 `bootstrap pass` 会在链接处失败（mockfs 等符号未定义），这是**设计如此**，
  只要 `startup.o.json` 生成就会被容错——不要把它当成构建错误。

## 最新一次二分结果（2026-10-30 05:50）

在照搬 clover 全套参数（`chip_id=0x13d`、`owned=0x40000000`、`dram_size=0x80000000`、
`armcpu-timer-intid=19`、`boot-progress=2`、`offline-legacy-*`）之后：

| 构建 | 内容 | 真机结果 |
| --- | --- | --- |
| p19/p20 | 无 `serial=3` + `_PE_init_cpu` 前探针 | 停在色条（未到该调用点） |
| p21 | 加上板级 ArmCpu（定时器改 19） | 仍停在色条 |
| p22 | 只开 panic 屏、去掉探针 | **没有 panic 文字** → 是真挂死，不是 panic |

结论：卡点是 `arm_vm_init` 返回后、`PE_init_cpu` 调用前的那两次调用，即
`PE_init_printf` 或 `PE_init_platform(TRUE)`（`ArmDTPlatform::configure()`）。
因为 `PE_init_cpu` 还没执行，ArmCpu 还没 start，定时器/GIC 也还没初始化，
所以这段里的任何 `IOSleep` 类定时等待都会永久挂住。

### 下一步（已缩小到很小的范围）

1. 分别在 `_PE_init_printf`、第二次 `_PE_init_platform` 的调用点加探针，确定是哪一个。
2. 若是 `configure()`：把 stock `wayne.dts` 里的 timer / uart / sdhci 等节点按
   `unixnu,adt-name` 补进 `dts/wayne.dts`（clover 的 ADT 节点更全），再测。
3. 存储：clover 的 `CloverSdhci.cpp`(397KB) / `CloverBlock.cpp`(145KB) 是重度设备定制，
   且 `CloverBlock` 硬编码了自己的 userdata 窗口常量（wayne 的分区号与之不同），
   要移植必须按 wayne 的 `mmcblk0p64` 改常量，不能直接照抄。

## 内核已跑到 root 挂载（2026-10-30 08:40）

真机 panic 屏依次被逐个击破，每一行都是一次已验证的进展：

| panic / 现象 | 根因 | 修复 |
| --- | --- | --- |
| 停在色条，无输出 | `check_for_panic_log()` 映射并读 `PLATFORM_PANIC_LOG_PADDR`（0x3c0f0000），SDM660 上是空 MMIO | `CONFIG_XNU_DT_PANIC_REGION=y`（sheng 也开着） |
| `can't has cs_enforcement_disable` @AppleMobileFileIntegrity.cpp:5261 | AMFI 不接受该启动参数（clover 靠自己的 AMFI 补丁） | 去掉 `cs_enforcement_disable=1` |
| `AMFI: No PMGR?` @ConfigurationSettings.cpp:235 | 没有 `ApplePMGRNub` 服务 | `CONFIG_XNU_SHENG_PMGR=y` + `scripts/build-clover-pmgr.py`（两遍构建：先出 kernel.macho 供审计）+ 把 `clover_emmc_run` 等板级钩子做成空桩 |
| 同上，nub 仍未发布 | `sheng_pmgr_run()` 在 `clover-pmgr != 2` 时直接 return | 加 `clover-pmgr=2` |
| **`Failed to mount root device` @IOKitBSDInit.cpp:984** | 没有任何块设备/根文件系统 | **下一步：eMMC 驱动**（CloverSdhci + CloverBlock，按 wayne 的 GPT） |

顺带确认：内核 console 已经能在 wayne 的 nt36672 面板上画字（panic 屏就是它画的），
所以之后所有故障都能直接看屏幕。

### 下一堵墙：root 设备

clover 的路线：
1. `drivers/CloverSdhci`（PIO eMMC 读）→ 提供 `clover_emmc_run`、`clover_emmc_block_*`、`clover_unattended_begin`；
2. `drivers/CloverBlock` → 把 eMMC 发布成 `IOBlockStorageDevice`（`clover_block_run`）；
3. ADT 里给 `root-match`：APFS 容器里 OS 卷的 UUID；或先用 mockfs + RAM disk 起 launchd。
3. 打开 `CONFIG_XNU_NATIVE_LEGACY_DISPLAY`（clover round180）才能把 GOP 帧缓冲交给 iOS 显示栈。

素材已下载到 `clover-drivers/`（CloverSdhci.cpp 405KB、CloverBlock.cpp 147KB、各自构建脚本）。

## 存储栈已通（2026-10-30 09:50）

| panic | 含义 | 处理 |
| --- | --- | --- |
| `CloverBlock r137: udwindow 0` | `CloverSdhci` 里硬编码的 userdata 窗口与卡上 GPT 不符 | wayne 的 userdata 起始 LBA 是 `0xdc0000`(14417920)，末日 LBA 恰好与 clover 相同(122142686)；已改常量 |
| `CloverBlock r137: root-magic 2615634631` | 分区读到了，但开头不是 `N4KROOT` 根镜像 | **下一阶段：userdata 镜像**（从 iPadOS IPSW 生成 OS/SystemOS 窗口并刷入） |

这条链路已经证明可用：eMMC PHY/时钟 → PIO 读 → GPT 解析 → 窗口匹配 → IOBlockStorageDevice → kernel 读到扇区。

### 最后一段管道

1. `unixnu build userdata`（macOS runner 上跑）：把 IPSW 里 **未改动的 OS 与 SystemOS 磁盘镜像**
   写成 userdata 镜像（带 manifest、按 `[ipsw.sha256]` 校验、检查是否放得进分区）。
   wayne 的 userdata 是 `mmcblk0p64`，51GB，够放 iPadOS 17.7.11。
2. 刷进 userdata（`fastboot flash userdata`）。
3. ADT 里加 `root_match_volume_uuid` 指向我们镜像里的 OS 卷；内核就能挂载 APFS root。
4. 之后 dyld/launchd 起来；要**看到** iOS 界面还需要 `CONFIG_XNU_NATIVE_LEGACY_DISPLAY=y`
   （clover round180 的做法：原版 IOMobileFramebufferLegacy 直接用 GOP 帧缓冲当扫描输出）。

IPSW 已本地下载完成（`ipad-17.7.11.ipsw`，6.37GB）。

## iOS 镜像已进机（2026-10-30 12:40）

userdata 里现在是真正的 iPadOS 17.7.11 OS 与 SystemOS 镜像，内核在真机上逐级读通了：

| 阶段 | 真机 panic | 说明 |
| --- | --- | --- |
| 清单 | `root-magic 2615634631` → 消失 | `SHNGROOT` 清单被接受 |
| OS 窗口 | `systemwin 1` → 消失 | OS 窗口的 APFS 容器被识别 |
| SystemOS 窗口 | `datawin 2` | OS/SystemOS 都在，缺可写的 Data 窗口 |

刷写方式（关键经验）：
- `fastboot` 会把整个镜像读进内存，8.74GiB 在 12GB 机器上直接 `std::bad_alloc`；
  **platform-tools 34.0.5** 的 sparse 分块路径可用（37.0.1 不行）。
- 先用 `make-sparse.py` 把 raw 镜像转 Android sparse；再用 `--skip` 把已写入的窗口
  标记为 DONT_CARE，只传输新增窗口（SystemOS 只传了 2.91GB）。

### 剩下的最后一块：Data 窗口

`clover-apfs=3`（真正的启动模式）要求清单里有三个窗口，第三个是**可写的 Data 卷**
（clover 用 32MiB APFS 容器，UUID `FC1A580E-2D67-48FC-B8CF-87422A319340`）。
clover 仓库里 `append-data-window.py` 引用的 `scripts/prepare-owner-data-fixture.py`
**并未提交**，所以这个 32MiB seed 需要我们自己造：

1. macOS CI：`hdiutil create -size 32m -fs APFS` + `diskutil apfs addVolume` 建 Data 卷，
   打印它的 UUID（要回填到 `CloverBlock.cpp` 的 `kDataVolumeUuid`）。
2. 用 `append-data-window.py`（改 wayne 的 MAX_BYTES）把它作为第 3 个窗口附加到镜像。
3. 本地只刷"清单 + Data 窗口"（约 32MiB，用 `--skip` 跳过 OS/SystemOS）。
4. 重编 payload（改 UUID 常量）→ 引导 → 内核应能挂上 APFS root。

同时要核对 `kSystemOsVolumeUuid`（clover 写死 `8846FE78-2910-4297-AF97-D59BB6F8FC16`）
是否等于我们 SystemOS 卷的真实 UUID，不一致要回填。
