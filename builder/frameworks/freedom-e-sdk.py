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
from os.path import isdir, join

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()

FRAMEWORK_DIR = env.PioPlatform().get_package_dir("framework-freedom-e-sdk")
assert FRAMEWORK_DIR and isdir(FRAMEWORK_DIR)


def is_valid_target(target):
    target_dir = join(FRAMEWORK_DIR, "bsp", target)
    return isdir(target_dir)


env.SConscript("_bare.py", exports="env")

target = env.BoardConfig().get(
    "build.freedom-e-sdk.variant", env.subst("sifive-${BOARD}"))
if env.subst("$BOARD") == "e310-arty":
    target = "freedom-e310-arty"

env.Append(
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
        ("VERSION", '\\"v0.1.2\\"')
    ],

    CPPPATH=[
        join("$BUILD_DIR"),
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

env.Prepend(LIBS=libs)
