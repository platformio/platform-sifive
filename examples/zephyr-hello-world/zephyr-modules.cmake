# Put this in a file with a name like "zephyr-modules.cmake"
set(ZEPHYR_MODULES $ENV{ZEPHYR_BASE}my-modules/hal_stm32 CACHE STRING "pre-cached modules")
message($ENV{ZEPHYR_BASE}my-modules/hal_stm32)