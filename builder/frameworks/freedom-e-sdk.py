# Copyright 2019-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Freedom E RISC-V SDK

Open Source Software for Developing on the Freedom E Platform

https://github.com/sifive/freedom-e-sdk
"""

from shutil import copyfile
from os import makedirs
from os.path import isdir, isfile, join

from SCons.Script import COMMAND_LINE_TARGETS, DefaultEnvironment

env = DefaultEnvironment()

try:
    import jinja2
    import pyparsing
except ImportError:
    env.Execute(
        env.VerboseAction(
            # Note: a specific version of MarkupSafe is requrired to avoid
            # the ImportError of 'soft_unicode' in Jinja2
            "$PYTHONEXE -m pip install pyparsing==2.4.5 MarkupSafe==2.0.1 Jinja2==2.10.1",
            "Installing Freedom E SDK's Python dependencies",
        )
    )

FRAMEWORK_DIR = env.PioPlatform().get_package_dir("framework-freedom-e-sdk")
assert FRAMEWORK_DIR and isdir(FRAMEWORK_DIR)

env.SConscript("_bare.py", exports="env")

board_config = env.BoardConfig()


def is_valid_target(target):
    target_dir = join(FRAMEWORK_DIR, "bsp", target)
    return isdir(target_dir)


def generate_freertos_header(config):
    freertos_config_dir = env.subst(join("$BUILD_DIR", "FreeRTOS", "include"))
    freertos_config_header = "Bridge_Freedom-metal_FreeRTOS.h"
    if isfile(join(freertos_config_dir, freertos_config_header)):
        return
    if not isdir(freertos_config_dir):
        makedirs(freertos_config_dir)

    cmd = [
        "$PYTHONEXE",
        '"%s"' % join(
            FRAMEWORK_DIR, "FreeRTOS-metal", "scripts", "parser_auto_header.py"),
        "--input_file",
        join(FRAMEWORK_DIR, "FreeRTOS-metal", "templates",
             freertos_config_header + ".in"),
        "--output_dir",
        join("$BUILD_DIR", "FreeRTOS", "include")
    ]

    env["ENV"]["MAKE_CONFIG"] = " ".join(
        ["freeRTOS.define.%s = %s" % (k, v) for (k, v) in config.items()])

    env.Execute(env.VerboseAction(
        " ".join(cmd), "Generating FreeRTOS bridge header..."))


def _get_mtime_rate():
    debug_tool = board_config.get_debug_tool_name(env.GetProjectOption("debug_tool"))
    if "debug" in COMMAND_LINE_TARGETS and debug_tool in ("qemu", "renode"):
        return 10000000
    return 1000000 if env.subst("$BOARD") == "hifive-unleashed" else 32768


def _get_freertos_config(use_segger_systemview=False, use_mpu_wrappers=False):
    config = {
        "portHANDLE_INTERRUPT": board_config.get(
            "build.freertos.interrupt_handler", "FreedomMetal_InterruptHandler"),
        "portHANDLE_EXCEPTION": board_config.get(
            "build.freertos.exception_handler", "FreedomMetal_ExceptionHandler"),
        "MTIME_CTRL_ADDR": board_config.get(
            "build.freertos.mtime_ctrl_addr", "0x2000000"),
        "MTIME_RATE_HZ": str(_get_mtime_rate())
    }

    if use_mpu_wrappers:
        config["portUSING_MPU_WRAPPERS"] = "1"

    if use_segger_systemview:
        config["configUSE_SEGGER_SYSTEMVIEW"] = "1"
        config["SYSVIEW_RECORD_ENTER_ISR"] = board_config.get(
            "build.freertos.sysview_record_enter_isr", "SEGGER_SYSVIEW_RecordEnterISR")
        config["SYSVIEW_RECORD_EXIT_ISR"] = board_config.get(
            "build.freertos.sysview_record_exit_isr", "SEGGER_SYSVIEW_RecordExitISR")
        config["SYSVIEW_RECORD_EXIT_ISR_TO_SCHEDULER"] = board_config.get(
            "build.freertos.sysview_record_exit_isr_to_scheduler",
            "SEGGER_SYSVIEW_RecordExitISRToScheduler"
        )

    return config


def build_freertos_libs():

    libs = []

    mpu_wrappers_enabled = board_config.get(
        "build.freertos.mpu_wrappers", "") == "enable"

    systemview_enabled = board_config.get(
        "build.freertos.systemview", "") == "enable"

    generate_freertos_header(_get_freertos_config(
        systemview_enabled, mpu_wrappers_enabled))

    env.Append(
        CPPDEFINES=[("WAIT_MS", 1000)],

        CPPPATH=[
            "$PROJECT_SRC_DIR",
            join("$BUILD_DIR", "FreeRTOS", "include"),
            join(FRAMEWORK_DIR, "FreeRTOS-metal", "FreeRTOS-Kernel", "include"),
            join(FRAMEWORK_DIR, "FreeRTOS-metal", "FreeRTOS-Kernel", "portable", "GCC",
                 "RISC-V"),
            join(FRAMEWORK_DIR, "FreeRTOS-metal", "FreeRTOS-Kernel", "portable", "GCC",
                 "RISC-V", "chip_specific_extensions", "RV32I_CLINT_no_extensions")
        ]
    )

    src_filter = [
        "-<*>",
        "+<*.c>",
        "+<portable/GCC>",
        "+<portable/MemMang/%s.c>" % board_config.get(
            "build.freertos.heap_model", "heap_4")
    ]

    if systemview_enabled:
        libs.append(build_system_view_lib())

    if mpu_wrappers_enabled:
        src_filter.append("+<portable/Common>")

    envsafe = env.Clone()
    envsafe.Append(ASFLAGS=["-D__ASSEMBLY__"])
    libs.append(envsafe.BuildLibrary(
        join("$BUILD_DIR", "FreeRTOS"),
        join(FRAMEWORK_DIR, "FreeRTOS-metal", "FreeRTOS-Kernel"),
        src_filter=src_filter
    ))

    return libs


def build_system_view_lib():
    env.Append(
        CPPPATH=[
            join(FRAMEWORK_DIR, "Segger_SystemView-metal", "SystemView", "SEGGER"),
            join(FRAMEWORK_DIR, "Segger_SystemView-metal", "SystemView", "Config"),
        ]
    )

    envsafe = env.Clone()
    envsafe.Append(ASFLAGS=["-D__ASSEMBLY__"])
    return envsafe.BuildLibrary(
        join("$BUILD_DIR", "SystemView"),
        join(FRAMEWORK_DIR, "Segger_SystemView-metal", "SystemView"),
        src_filter=[
            "-<*>",
            "+<SEGGER/SEGGER_SYSVIEW.c>",
            "+<SEGGER/SEGGER_RTT.c>",
            "+<SEGGER/SEGGER_RTT_printf.c>"
        ]
    )


target = board_config.get(
    "build.freedom-e-sdk.variant", env.subst("sifive-${BOARD}"))
if env.subst("$BOARD") == "e310-arty":
    target = "freedom-e310-arty"

env.Append(
    ASPPFLAGS=[
        "--specs=nano.specs"
    ],
    CCFLAGS=[
        "-ffunction-sections",
        "-fdata-sections",
        "--specs=nano.specs"
    ],

    LINKFLAGS=[
        "-nostdlib"
    ],

    CPPDEFINES=[
        ("PACKAGE_NAME", '\\"freedom-metal\\"'),
        ("PACKAGE_TARNAME", '\\"freedom-metal\\"'),
        ("PACKAGE_VERSION", '\\"v0.1.2\\"'),
        ("PACKAGE_STRING", '\\"freedom-metal v0.1.2\\"'),
        ("PACKAGE", '\\"freedom-metal\\"'),
        ("VERSION", '\\"v0.1.2\\"'),
        ("MTIME_RATE_HZ_DEF", _get_mtime_rate())
    ],

    CPPPATH=[
        "$BUILD_DIR",
        join(FRAMEWORK_DIR, "freedom-metal")
    ],

    LIBPATH=[
        "$BUILD_DIR",
        join(FRAMEWORK_DIR, "bsp", target)
    ],

    LIBS=["gcc", "m"]
)

if not is_valid_target(target):
    print ("Could not find BSP package for %s" % target)
    env.Exit(1)

#
# Configure stack and heap sizes
#

if board_config.get("build.freedom-e-sdk.stack_size", ""):
    env.Append(
        LINKFLAGS=[
            "-Wl,--defsym,__stack_size=" + board_config.get(
                "build.freedom-e-sdk.stack_size")
        ]
    )

if board_config.get("build.freedom-e-sdk.heap_size", ""):
    env.Append(
        LINKFLAGS=[
            "-Wl,--defsym,__heap_size=" + board_config.get(
                "build.freedom-e-sdk.heap_size"),
        ]
    )

#
# Copy target header files
#

include_path = join(env.subst("$BUILD_DIR"), "metal", "machine")
if not isdir(include_path):
    makedirs(include_path)


copyfile(
    join(FRAMEWORK_DIR, "bsp", target, "metal.h"),
    join(env.subst("$BUILD_DIR"), "metal", "machine.h")
)

copyfile(
    join(FRAMEWORK_DIR, "bsp", target, "metal-platform.h"),
    join(include_path, "platform.h")
)

copyfile(
    join(FRAMEWORK_DIR, "bsp", target, "metal-inline.h"),
    join(include_path, "inline.h")
)

#
# Target: Build Metal Libraries
#

libs = [
    env.BuildLibrary(
        join("$BUILD_DIR", "metal"),
        join(FRAMEWORK_DIR, "freedom-metal", "src")
    ),

    env.BuildLibrary(
        join("$BUILD_DIR", "metal-gloss"),
        join(FRAMEWORK_DIR, "freedom-metal", "gloss")
    )
]

if "freertos" in env.subst("$PIOFRAMEWORK"):
    libs.extend(build_freertos_libs())

if not board_config.get("build.ldscript", ""):
    ldscript = board_config.get("build.freedom-e-sdk.ldscript", "")
    if "freertos" in env.subst("$PIOFRAMEWORK"):
        ldscript = board_config.get(
            "build.freertos.ldscript", "metal.freertos.lds")
    env.Replace(LDSCRIPT_PATH=ldscript)

env.Prepend(LIBS=libs)
