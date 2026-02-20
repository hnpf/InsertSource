import subprocess
import json
import os
import platform
import re
import logging

logger = logging.getLogger("SysProbe")

class SysProbe:
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, "data", "drivers.json")
        else:
            self.db_path = db_path
        logger.info(f"Initializing SysProbe with DB: {self.db_path}")
        self.drivers_db = self._load_db()
    def _load_db(self):
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, "r") as f:
                    return json.load(f)
            logger.warning(f"Database file not found: {self.db_path}")
        except Exception as e:
            logger.error(f"Error loading database: {e}")
        return {}

    def get_pci_devices(self):
        if not os.path.exists("/usr/bin/lspci") and not os.path.exists("/bin/lspci"):
            logger.error("lspci not found! Please install pciutils.")
            return []
        try:
            logger.debug("Running lspci -nnmm")
            # -nn adds numeric IDs like [0300]
            output = subprocess.check_output(["lspci", "-nnmm"], text=True)
            return output.strip().split("\n")
        except Exception as e:
            logger.error(f"Failed to get PCI devices: {e}")
            return []
    def get_usb_devices(self):
        if not os.path.exists("/usr/bin/lsusb") and not os.path.exists("/bin/lsusb"):
            logger.error("lsusb not found! Please install usbutils.")
            return []
        try:
            logger.debug("Running lsusb")
            output = subprocess.check_output(["lsusb"], text=True)
            return output.strip().split("\n")
        except Exception as e:
            logger.error(f"Failed to get USB devices: {e}")
            return []
    def get_firmware_updates(self):
        """Check for firmware updates using fwupdmgr."""
        try:
            logger.info("Checking for firmware updates...")
            cmd = ["pkexec", "fwupdmgr", "get-updates", "--json"]
            if os.getuid() == 0:
                cmd = ["fwupdmgr", "get-updates", "--json"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if data and isinstance(data, dict) and data.get("Devices"):
                        return data
                    logger.info("fwupdmgr returned 0 but no devices were found in JSON.")
                    return None
                except Exception as e:
                    logger.error(f"Failed to parse fwupdmgr JSON: {e}")
                    return None
            elif result.returncode == 2:
                logger.info("No firmware updates available (fwupdmgr returned 2).")
                return None
            else:
                logger.warning(f"fwupdmgr failed with code {result.returncode}: {result.stderr}")
        except FileNotFoundError:
            logger.info("fwupdmgr not found, skipping firmware check.")
        except Exception as e:
            logger.error(f"Error checking firmware updates: {e}")
        return None

    def get_system_info(self):
        logger.info("Collecting system info...")
        info = {
            "os": platform.freedesktop_os_release().get("PRETTY_NAME", platform.system()),
            "kernel": platform.release(),
            "cpu": self._get_cpu_info(),
            "gpu": self._get_gpu_info(),
            "ram": self._get_ram_info(),
            "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "Unknown"),
            "session": os.environ.get("XDG_SESSION_TYPE", "Unknown")
        }
        return info

    def _get_cpu_info(self):
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()
            return platform.processor()
        except:
            return "Unknown CPU"

    def _get_gpu_info(self):
        try:
            pci = self.get_pci_devices()
            gpus = []
            for dev in pci:
                if "[0300]" in dev or "[0302]" in dev: # VGA/3D controller
                    parts = re.findall(r'\"(.*?)\"', dev)
                    if len(parts) >= 3:
                        vendor_str = parts[1]
                        device_str = parts[2]
                        # get content of first set of brackets in vendor_str (e.g. [AMD/ATI])
                        vendor_match = re.search(r'\[(.*?)\]', vendor_str)
                        vendor = vendor_match.group(1) if vendor_match else vendor_str
                        # get content of first set of brackets in device_str (e.g. [model_name])
                        device_match = re.search(r'\[(.*?)\]', device_str)
                        device = device_match.group(1) if device_match else device_str
                        gpus.append(f"{vendor} {device}")
            return ", ".join(gpus) if gpus else "Unknown GPU"
        except:
            return "Unknown GPU"

    def _get_ram_info(self):
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = int(line.split(":")[1].strip().split()[0])
                        gb = round(kb / (1024 * 1024), 1)
                        return f"{gb} GB"
            return "Unknown RAM"
        except:
            return "Unknown RAM"

    def find_needed_packages(self, distro_id):
        pci_devices = self.get_pci_devices()
        usb_devices = self.get_usb_devices()
        all_devices = pci_devices + usb_devices
        results = []
        logger.info(f"Scanning for missing packages across {len(self.drivers_db)} categories")
        for cat, drivers in self.drivers_db.items():
            if not isinstance(drivers, list):
                continue
            logger.debug(f"Scanning category: {cat}")
            for driver in drivers:
                if not isinstance(driver, dict) or "search_patterns" not in driver:
                    continue
                class_id = driver.get("class_id")
                for device in all_devices:
                    # the device string should contain it in brackets if class_id is available (from -nn)
                    if class_id and f"[{class_id}]" not in device:
                        continue
                    if any(pattern.lower() in device.lower() for pattern in driver["search_patterns"]):
                        pkgs = driver["packages"].get(distro_id) or driver["packages"].get("arch")
                        if pkgs:
                            logger.info(f"Matched device '{device}' to driver '{driver['name']}' ({cat})")
                            results.append({
                                "driver_name": driver["name"],
                                "device_raw": device,
                                "packages": pkgs,
                                "category": cat
                            })
                        break # move to next driver entry

        return results
