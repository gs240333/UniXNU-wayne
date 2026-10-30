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
