# wayne 迁移进度（UniXNU format-2 模式）

更新时间：2026-10-30

## 结论一句话

wayne（小米 6X，SDM660）**已经能用 UniXNU/Mu-Silicium 的 UEFI 固件启动并点亮屏幕**。
下一步是把 `UniXNU.efi` 嵌进固件、再走正式 format-2 链（kernel/package/payload/bootimg）。

## 已达成（真机验证）

| 项 | 证据 |
| --- | --- |
| waynePkg 固件可编译 | CI run `40967306785` success，产物 `SILICIUM_UEFI.fd` = 3145728 B = 0x300000（与 `[uefi_fd] size` 精确一致） |
| boot.img 结构正确 | `ANDROID!` v0, page 4096, kernel `0x10008000`, tags `0x10000100`, gzip 后接 `d00dfeed` DTB（873326 偏移），与 wayne stock 完全一致 |
| BootShim + UEFI 在真机运行 | `fastboot boot` 后设备重新枚举为 fastboot 设备 **`xnuloader`**（product=xnuloader, version 0.5, max-download-size 0x3f00000） |
| 显示链路打通 | 屏幕出现 Silicium **"Si"** logo，顶部有白色 UEFI 文本 |
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

## 下一步

1. 把 `UniXNU.inf` / `UniXNUDxe.inf` / `DarwinBoot.inf`（+ `UniXNURamDiskDxe`、
   DiskIo、FAT）加进 `wayne.dsc`/`wayne.fdf`，重建 FD，确认出现 UniXNU 菜单。
2. 用 `unixnu status --json` 在构建机验证 `wayne-f2` 的 format-2 配置。
3. 正式链：`build kernel`（macOS/CI）→ `build package` → `build firmware` →
   `build payload` → `bootimg`。
4. 之后才谈 XNU 侧 eMMC（NativeSdhci/CloverSdhci 类组件）与触摸。

## 复现命令

```powershell
# 1. 固件（CI）
gh workflow run wayne.yml -R gs240333/Mu-Silicium
gh run download <run-id> -R gs240333/Mu-Silicium -D wayne-uefi

# 2. 真机（不写分区）
tools\platform-tools\fastboot.exe boot wayne-uefi\wayne-uefi\Mu-wayne.img
```
