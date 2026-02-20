# Insert

A friendly system utility and driver installer for most Linux distributions, built with Python and Libadwaita.

## Features
- **Hardware Detection**: Uses `lspci` and `lsusb` to scan your hardware.
- **Driver Database**: Mapped via `data/drivers.json` across multiple distros.
- **Libadwaita UI**: A native GNOME look with rounded corners and adaptive views.
- **Non-blocking Operations**: Uses a background task worker which handles installations without freezing the UI.
- **Multi-Distro**: Supports Arch, Fedora, and Debian/Ubuntu, and possibly more, out of the box.

## Project Structure
- `src/libinsert/`: Backend logic (Distro detection, Hardware probing, Task worker).
- `src/ui/`: GTK4/Libadwaita interface.
- `data/`: Driver database and desktop files.

## Running
Be sure that you have the following installed (so things don't break):
- `python3-gobject`
- `libadwaita`
- `pciutils` (for lspci)
- `usbutils` (for lsusb)

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 src/ui/main.py
```

## Testing
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 tests/test_probe.py
```

## Adding new drivers
Edit `data/drivers.json` to add new hardware IDs and their corresponding package names for different distros.
