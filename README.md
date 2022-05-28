# SiFive: development platform for [PlatformIO](https://platformio.org)

[![Build Status](https://github.com/platformio/platform-sifive/workflows/Examples/badge.svg)](https://github.com/platformio/platform-sifive/actions)

SiFive brings the power of open source and software automation to the semiconductor industry, making it possible to develop new hardware faster and more affordably than ever before.

* [Home](https://registry.platformio.org/platforms/platformio/sifive) (home page in the PlatformIO Registry)
* [Documentation](https://docs.platformio.org/page/platforms/sifive.html) (advanced usage, packages, boards, frameworks, etc.)

# Usage

1. [Install PlatformIO](https://platformio.org)
2. Create PlatformIO project and configure a platform option in [platformio.ini](https://docs.platformio.org/page/projectconf.html) file:

## Stable version

```ini
[env:stable]
platform = sifive
board = ...
...
```

## Development version

```ini
[env:development]
platform = https://github.com/platformio/platform-sifive.git
board = ...
...
```

# Configuration

Please navigate to [documentation](https://docs.platformio.org/page/platforms/sifive.html).
