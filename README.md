# coherent_lasers

This repository contains python driver packages for various lasers manufactured by coherent. To facilitate
communication with the devices, the drivers utilize:

1. low level SDKs provided by coherent
2. Serial communication via `RS232` and equivalent protocols

## Supported Lasers

1. [Genesis MX](src/coherent_lasers/genesis_mx/README.md)

Repository is organized by laser model. Each laser model has its own directory containing the driver code.

   ```text
   coherent_lasers/
   ├── src/
   │   ├── common/
   │   │   ├── hops/
   │   │   │   ├── dll/
   │   │   │   │   └── (DLL files go here)
   │   │   │   └── hops_device.py
   │   │   ├── serial/
   │   │   │   └── serial_device.py
   │   ├── genesis_mx/
   │   │   ├── genesis_mx.py
   │   │   ├── genesis_mx_voxel.py
   │   │   └── README.md
   └── setup.py
   ```

## Installation

### Option 1: Install from GitHub Release

You can install the `coherent_lasers` package directly from a GitHub release using `pip`.

**Install Using the ZIP Archive:**

```bash
pip install https://github.com/AllenNeuralDynamics/coherent_lasers/archive/refs/tags/v0.1.0.zip
```

**Install Using the Tarball Archive:**

```bash
pip install https://github.com/AllenNeuralDynamics/coherent_lasers/archive/refs/tags/v0.1.0.tar.gz
```

**Note**: Replace v0.1.0 with the tag of the release you want to install.

### Option 2: Clone the Repository and Install Locally

If you prefer to clone the repository and install it locally, follow these steps:

1. Clone the Repository:

   ```bash
   git clone https://github.com/your-username/coherent_lasers.git
   cd coherent_lasers
   ```

2. Install the Package:
   For regular use:

   ```bash
   pip install .
   ```

   For development (includes dev dependencies):

   ```bash
   pip install -e .[dev]
   ```
