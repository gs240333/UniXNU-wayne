/* SPDX-License-Identifier: BSD-2-Clause-Patent
 *
 * Placeholders for the board hooks the PMGR nub calls, plus weak definitions of
 * the block-stack contract the offline owner mount asks for.
 *
 * sheng_pmgr_run() publishes the ApplePMGRNub AMFI waits for and then calls the
 * board's drivers. The eMMC side is real (drivers/CloverSdhci provides
 * clover_emmc_run and clover_unattended_begin), so only input, power and the
 * DSP remain empty. A missing symbol fails the kernel link.
 *
 * The block-stack contract entries below are weak: the
 * first pass of the kernel build links without any archive, and kern_exec.c and
 * IOKitBSDInit.cpp reference them once the owner mount is switched on. The real
 * definitions live in drivers/CloverBlock and win at the final link. Do not add
 * behaviour here.
 */
#include <sys/types.h>

void clover_input_run(void);
void clover_power_run(void);
void clover_dsp_run(void);

int native_verified_block_root_authorized(dev_t device);
int native_verified_block_volume_device(const char *uuid, dev_t *device, char *path, size_t size);
int native_verified_block_manifest_sha384(const char *name, unsigned char *digest,
                                          unsigned long long *offset, unsigned long long *bytes);
int native_ram_block_volume_seed(unsigned char *seed, size_t *bytes);
int native_ram_block_gpu_addon(const char *path, unsigned long long offset, size_t size);

void
clover_input_run(void)
{
}

void
clover_power_run(void)
{
}

void
clover_dsp_run(void)
{
}

__attribute__((weak)) int
native_verified_block_root_authorized(dev_t device)
{
	(void)device;
	return 0;
}

__attribute__((weak)) int
native_verified_block_volume_device(const char *uuid, dev_t *device, char *path, size_t size)
{
	(void)uuid;
	(void)device;
	(void)path;
	(void)size;
	return 0;
}

__attribute__((weak)) int
native_verified_block_manifest_sha384(const char *name, unsigned char *digest,
                                      unsigned long long *offset, unsigned long long *bytes)
{
	(void)name;
	(void)digest;
	(void)offset;
	(void)bytes;
	return 0;
}

__attribute__((weak)) int
native_ram_block_volume_seed(unsigned char *seed, size_t *bytes)
{
	(void)seed;
	(void)bytes;
	return 0;
}

__attribute__((weak)) int
native_ram_block_gpu_addon(const char *path, unsigned long long offset, size_t size)
{
	(void)path;
	(void)offset;
	(void)size;
	return 0;
}
