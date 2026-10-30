/* SPDX-License-Identifier: BSD-2-Clause-Patent
 *
 * Placeholders for the board hooks the PMGR nub calls that have no driver yet.
 *
 * sheng_pmgr_run() publishes the ApplePMGRNub AMFI waits for and then calls the
 * board's drivers. The eMMC side is real now (drivers/CloverSdhci provides
 * clover_emmc_run and clover_unattended_begin), so only input, power and the
 * DSP remain as empty definitions. A missing symbol fails the kernel link.
 *
 * Replace a stub with the real driver's entry point as it lands; do not add
 * behaviour here.
 */

void clover_input_run(void);
void clover_power_run(void);
void clover_dsp_run(void);

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
