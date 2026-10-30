# ArmCpu (wayne board copy)

Upstream `UniXNU/ArmCpu`, with one board change: the arch timer interrupt line
is taken from the `armcpu-timer-intid` boot argument instead of the hard-coded
PPI 27.

On SDM660 the device tree numbers the timer PPIs 1, 2, 3, 0, so the PPI number
plus 16 gives 17, 18, 19, 16, and `enableCPUTimeBase` arms `CNTV_CTL_EL0`, whose
line is **19**. The base driver arms PPI 27, which nothing raises, so the counter
runs but no tick ever arrives: every timed wait hangs, including the one that
starts the bootstrap thread.

`board.toml` passes `armcpu-timer-intid=19`. The default (27) keeps the upstream
behaviour for every other board that selects this component.