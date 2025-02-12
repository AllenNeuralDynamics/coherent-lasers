# coherent_lasers

Python drivers for Coherent lasers.

## Project Overview

Repository is organized by laser model. Each laser model has its own directory containing the driver code.

   ```text
   coherent_lasers/
   ├── src/
   │   ├── app/
   │   │   ├── frontend/build/(build files from webgui)
   │   │   ├── messaging/
   │   │   ├── cli.py
   │   │   ├── server.py
   │   ├── genesis_mx/
   │   │   ├── commands.py
   │   │   ├── mock.py
   │   │   └── driver.py
   │   │   ├── hops/
   │   │   │   ├── CohrFTCI2C.h
   │   │   │   ├── CohrHOPS.h
   │   │   │   ├── (DLL files for each .h file)
   │   │   │   ├── lib.py
   ├── setup.py
   └── webgui (web frontend for controlling the laser)
   ```

### Supported Lasers

1. [Genesis MX](https://www.coherent.com/lasers/cw-solid-state/genesis)
   The `GenesisMX` class provides a comprehensive API for controlling the laser.
   Supports connection via USB using the HOPS SDK provided by Coherent.

## Usage

>: **Note:** Installing the package from a wheel file will ensure that the necessary dll files are included. If you install the package from source, you will need to download the dll files and add them to the `src/coherent_lasers/src/hops` directory.

### Running from a wheel file

Download the latest release from the [releases page](https://github.com/AllenNeuralDynamics/coherent_lasers/releases).

```bash
pip install <path_to_downloaded_wheel>
```

Alternatively you can install the `coherent_lasers` package directly from a GitHub release using `pip`.

```bash
coherent_version=0.2.0
pip install https://github.com/AllenNeuralDynamics/coherent_lasers/releases/download/v${coherent_version}/coherent_lasers-${coherent_version}-py3-none-any.whl
```

To launch a web GUI for controlling the laser, run the following command:

```bash
genesis-mx
```

### Running from source

```bash
git clone
```

```bash
cd coherent_lasers
```

```bash
uv sync
```

```bash
cd webgui && pnpm i && pnpm run build && cd ..
```

```bash
genesis-mx
```

alternatively, you can run the server using fastapi cli:

```bash
cd src/coherent_lasers/app

```bash
uv run fastapi dev server.py
```

### Building the Web GUI

```bash
cd webgui
```

> **Note:** You can also use `npm` or `yarn` in place of `pnpm` below, to install the dependencies and build the project.

```bash
pnpm i
```

```bash
pnpm run build
```

```bash
cd ../src/coherent_lasers/app
```

```bash
uv run fastapi dev server.py
```
