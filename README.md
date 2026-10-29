# UniXNU-wayne

UniXNU device repository for the Xiaomi MI 6X (`wayne`), Qualcomm SDM660 with
eMMC storage and a 1080x2160 `nt36672` panel.

This repository is a format 2 port (`schema_version = 2`). It replaces the
earlier shim-based bring-up, which drove the kernel directly from a custom boot
image and stalled on the eMMC controller.

## Scope

The first stage boots through the standard UniXNU chain:

```
boot.img -> BootShim -> waynePkg (Mu-Silicium UEFI) -> UniXNU.efi
         -> DarwinBoot -> XNU
```

Storage is not wired into XNU yet. The selection uses `RamBlock` for a RAM-backed
block device and `GopFramebuffer` to hand the bootloader-initialized splash
buffer to the kernel, so the kernel console works before any display or storage
driver exists.

## Hardware

| Item | Value |
| --- | --- |
| SoC | SDM660 (`qcom,msm-id 317`), 4x Kryo 260 Gold + 4x Kryo 260 Silver |
| Memory | 4 GiB, banks `0x80000000 + 0x80000000` and `0x100000000 + 0x7e4c0000` |
| Storage | eMMC, `sdhci@c0c4000`; `userdata` is `mmcblk0p64` |
| Panel | `nt36672` tianma FHD video, 1080x2160, single DSI |
| Splash buffer | `cont_splash_mem` at `0x9D400000`, 36 MiB |
| Firmware volume | `0x9FC00000 + 0x300000` |
| Boot image | header v0, page 4096, gzip kernel, board DTB appended |
| Touch | FocalTech FTS at I2C `0xc175000`, address `0x38` (not wired yet) |
| Bootloader | unlocked, no A/B slots |

## Firmware

The UEFI platform is `waynePkg` in the Mu-Silicium fork
[gs240333/Mu-Silicium](https://github.com/gs240333/Mu-Silicium). It derives from
`lavenderPkg` (Redmi Note 7, same SDM660) and reuses the vendor DXE binaries for
clocks, PMIC, TLMM, USB and eMMC. Board changes are the SMBIOS identity, the
1080x2160 framebuffer and `USE_CUSTOM_DISPLAY_DRIVER = 0`, which keeps
`SimpleFbDxe` on the splash buffer instead of running lavender's panel init.

## Build

```sh
./unixnu defconfig wayne_defconfig -D ../UniXNU-wayne
./unixnu fetch
./unixnu status --json
./unixnu build kernel
./unixnu build package
./unixnu build firmware --uefi ../Mu-Silicium
./unixnu bootimg --uefi ../Mu-Silicium --dtb dts/wayne.dtb
```

The kernel step needs macOS. On a Linux host use `scripts/linux/setup-toolchain.py`
as described in the build documentation.

## Boot

Always start with a non-writing boot:

```sh
fastboot boot boot.img
```

`backup/boot.img` holds the stock boot image for recovery.
