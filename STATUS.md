# wayne 迁移进度（UniXNU format-2 模式）

更新时间：2026-10-30

## 结论一句话

wayne（小米 6X，SDM660）**已经能用 UniXNU/Mu-Silicium 的 UEFI 固件启动、点亮屏幕，并进入 UniXNU 启动菜单**。
下一步是把 format-2 内核编译出来，做 payload 与 bootimg，然后让 DarwinBoot 把 XNU 拉起来。

## 已达成（真机验证）

| 项 | 证据 |
| --- | --- |
| waynePkg 固件可编译 | CI run `40967306785` success，产物 `SILICIUM_UEFI.fd` = 3145728 B = 0x300000（与 `[uefi_fd] size` 精确一致） |
| boot.img 结构正确 | `ANDROID!` v0, page 4096, kernel `0x10008000`, tags `0x10000100`, gzip 后接 `d00dfeed` DTB（873326 偏移），与 wayne stock 完全一致 |
| BootShim + UEFI 在真机运行 | `fastboot boot` 后设备重新枚举为 fastboot 设备 **`xnuloader`**（product=xnuloader, version 0.5, max-download-size 0x3f00000） |
| 显示链路打通 | 屏幕出现 Silicium **"Si"** logo，顶部有白色 UEFI 文本 |
| **UniXNU 菜单在真机出现** | 把 `UniXNU.inf` + `UniXNUDxe.inf` 编进 FV 后（run `40972038089`，FD 仍为 3145728 B），真机屏幕显示 **UniXNU 菜单（标题 + 列表）**，设备不再枚举 fastboot，说明 BDS 按 `BootOrder` 自动启动了 UniXNU |
| format-2 配置可解析 | `gs240333/UniXNU-wayne` Actions `Resolve configuration` 成功：`schema_version=2`、`out/wayne/ipados-17.7.11-21H461/wayne`、组件 = ArmDTPlatform, ArmCpu, SoftwareAES, RamBlock, GopFramebuffer, XnuPrelink, DarwinBoot |
| 回退安全 | boot 分区从未写入；`backup/boot.img` 为 stock 备份 |


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

