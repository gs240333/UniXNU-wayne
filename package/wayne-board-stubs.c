/* SPDX-License-Identifier: BSD-2-Clause-Patent
 *
 * Placeholders for the board hooks the PMGR nub calls.
 *
 * sheng_pmgr_run() publishes the ApplePMGRNub AMFI waits for and then calls the
 * board's own drivers: eMMC, input, power and DSP. wayne has none of them yet,
 * and a missing symbol fails the kernel link rather than the boot, so the hooks
 * live here as empty functions until each driver is ported. Each one returns
 * nothing and takes nothing, which is the signature the nub calls.
 *
 * Replace a stub with the real driver's entry point as it lands; do not add
 * behaviour here.
 */

void clover_emmc_run(void);
void clover_input_run(void);
void clover_power_run(void);
void clover_dsp_run(void);
void clover_unattended_begin(void);

void
clover_emmc_run(void)
{
}

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

void
clover_unattended_begin(void)
{
}
