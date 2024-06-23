# HOPS DLL Device

This directory contains base class and utilities for lasers that use HOPS DLL files.

## Setting Up DLL Files

To use the HOPS DLL utilities, you need to add the necessary DLL files to the `dll` folder.

### Steps:

1. **Download DLL Files:**
   - Go to the [Releases]() section of the GitHub repository.
   - Find the latest release that includes the HOPS DLL files.
   - Download the DLL files from the release assets.

2. **Add DLL Files to the Repository:**
   - Create a folder named `dll` inside the `hops` directory if it doesn't already exist.
   - Move the downloaded DLL files into the `dll` folder.

### Example:

```
coherent_lasers/
├── common/
│   ├── hops/
│   │   ├── dll/
│   │   │   └── (DLL files go here)
│   │   ├── hops_device.py
│   │   └── README.md
└── setup.py
```

After placing the DLL files in the `dll` folder, the utilities in `hops_device.py` will be able to use them.

## Usage

You can now use the classes and functions defined in `hops_device.py` as follows:

```python
from coherent_lasers.common.hops import HOPSDevice

device = HOPSDevice(serial='123456')
device.initialize()
device.send_command('some_command')
```

For more detailed usage instructions, refer to the documentation in hops_device.py.

### Summary:

1. **Ensure the `__init__.py` file contains necessary setup code and documentation.**
2. **Provide detailed setup instructions in the `README.md` file within the `hops_dll` directory.**
3. **Include a clear example of how to use the package in both the `__init__.py` and `README.md` files.**

This approach ensures that users have all the information they need to properly set up and use the HOPS DLL utilities, making the repository more user-friendly and maintainable.