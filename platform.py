# Copyright 2014-present PlatformIO <contact@platformio.org>
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

from os.path import isfile, join
from platform import system

from platformio.managers.platform import PlatformBase
from platformio.util import get_systype


class SifivePlatform(PlatformBase):

    def configure_default_packages(self, variables, targets): 
        if "zephyr" in variables.get("pioframework", []):
            for p in self.packages:
                if p.startswith("framework-zephyr-") or p in (
                    "tool-cmake", "tool-dtc", "tool-ninja"):
                    self.packages[p]["optional"] = False
            if "windows" not in get_systype():
                self.packages['tool-gperf']['optional'] = False
                
                
        return PlatformBase.configure_default_packages(self, variables,
                                                       targets) 

    def get_boards(self, id_=None):
        result = PlatformBase.get_boards(self, id_)
        if not result:
            return result
        if id_:
            return self._add_default_debug_tools(result)
        else:
            for key, value in result.items():
                result[key] = self._add_default_debug_tools(result[key])
        return result

    def _add_default_debug_tools(self, board):
        debug = board.manifest.get("debug", {})
        upload_protocols = board.manifest.get("upload",
                                              {}).get("protocols", [])
        if "tools" not in debug:
            debug['tools'] = {}

        tools = ("jlink", "qemu", "ftdi", "minimodule",
                 "olimex-arm-usb-tiny-h", "olimex-arm-usb-ocd-h",
                 "olimex-arm-usb-ocd", "olimex-jtag-tiny", "tumpa")
        for tool in tools:
            if tool == "qemu":
                if not debug.get("qemu_machine"):
                    continue
            elif (tool not in upload_protocols or tool in debug['tools']):
                continue
            if tool == "jlink":
                assert debug.get("jlink_device"), (
                    "Missed J-Link Device ID for %s" % board.id)
                debug['tools'][tool] = {
                    "server": {
                        "package": "tool-jlink",
                        "arguments": [
                            "-singlerun",
                            "-if", "JTAG",
                            "-select", "USB",
                            "-speed", "1000",
                            "-jtagconf", "-1,-1",
                            "-device", debug.get("jlink_device"),
                            "-port", "2331"
                        ],
                        "executable": ("JLinkGDBServerCL.exe"
                                       if system() == "Windows" else
                                       "JLinkGDBServer")
                    },
                    "onboard": tool in debug.get("onboard_tools", [])
                }

            elif tool == "qemu":
                machine64bit = "64" in board.get("build.mabi")
                debug['tools'][tool] = {
                    "server": {
                        "package": "tool-qemu-riscv",
                        "arguments": [
                            "-nographic",
                            "-machine", debug.get("qemu_machine"),
                            "-d", "unimp,guest_errors",
                            "-gdb", "tcp::1234",
                            "-S"
                        ],
                        "executable": "bin/qemu-system-riscv%s" % (
                            "64" if machine64bit else "32")
                    },
                    "onboard": True
                }
            else:
                server_args = [
                    "-s", "$PACKAGE_DIR/share/openocd/scripts"
                ]
                sdk_dir = self.get_package_dir("framework-freedom-e-sdk")
                board_cfg = join(
                    sdk_dir or "", "bsp", "sifive-%s" % board.id, "openocd.cfg")
                if isfile(board_cfg):
                    server_args.extend(["-f", board_cfg])
                elif board.id == "e310-arty":
                    server_args.extend([
                        "-f", join("interface", "ftdi", "%s.cfg" % (
                            "arty-onboard-ftdi" if tool == "ftdi" else tool)),
                        "-f", join(
                            sdk_dir or "", "bsp", "freedom-e310-arty", "openocd.cfg")
                    ])
                else:
                    assert "Unknown debug configuration", board.id
                debug['tools'][tool] = {
                    "server": {
                        "package": "tool-openocd-riscv",
                        "executable": "bin/openocd",
                        "arguments": server_args
                    },
                    "onboard": tool in debug.get("onboard_tools", []),
                    "init_cmds": debug.get("init_cmds", None)
                }

        board.manifest['debug'] = debug
        return board
