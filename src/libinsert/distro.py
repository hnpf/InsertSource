import os
import subprocess
import logging

logger = logging.getLogger("DistroManager")

class DistroManager:
    def __init__(self):
        self.id = self._detect_distro()
        self.family = self._get_family()
        self.pkg_mgr = self._get_pkg_mgr()
        logger.info(f"Distro detected: {self.id} (Family: {self.family}), Package Manager: {self.pkg_mgr}")

    def _sudo_wrap(self, cmd):
        if os.getuid() == 0:
            return cmd
        logger.debug(f"Wrapping command with pkexec: {' '.join(cmd)}")
        return ["pkexec"] + cmd

    def refresh_database(self):
        """Update package manager database."""
        logger.info(f"Refreshing package database for {self.pkg_mgr}")
        if self.pkg_mgr == "pacman":
            return self._sudo_wrap(["pacman", "-Sy"])
        elif self.pkg_mgr == "dnf":
            return self._sudo_wrap(["dnf", "check-update"])
        elif self.pkg_mgr == "apt":
            return self._sudo_wrap(["apt", "update"])
        elif self.pkg_mgr == "zypper":
            return self._sudo_wrap(["zypper", "refresh"])
        return []

    def _detect_distro(self):
        if not os.path.exists("/etc/os-release"):
            return "unknown"
        
        with open("/etc/os-release") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("ID="):
                    return line.strip().split("=")[1].strip('"')
        return "unknown"

    def _get_family(self):
        families = {
            "arch": "arch",
            "manjaro": "arch",
            "endeavouros": "arch",
            "fedora": "fedora",
            "nobara": "fedora",
            "opensuse": "suse",
            "opensuse-tumbleweed": "suse",
            "opensuse-leap": "suse",
            "debian": "debian",
            "ubuntu": "debian",
            "pop": "debian",
            "linuxmint": "debian",
            "void": "void",
            "gentoo": "gentoo",
            "solus": "solus",
            "alpine": "alpine"
        }
        return families.get(self.id, "arch")

    def _get_pkg_mgr(self):
        mapping = {
            "arch": "pacman",
            "manjaro": "pacman",
            "fedora": "dnf",
            "opensuse": "zypper",
            "opensuse-tumbleweed": "zypper",
            "debian": "apt",
            "ubuntu": "apt",
            "void": "xbps",
            "gentoo": "emerge",
            "solus": "eopkg",
            "alpine": "apk"
        }
        return mapping.get(self.id, mapping.get(self.family, "unknown"))

    def get_install_command(self, packages):
        if self.pkg_mgr == "pacman":
            return self._sudo_wrap(["pacman", "-S", "--needed", "--noconfirm"] + packages)
        elif self.pkg_mgr == "dnf":
            return self._sudo_wrap(["dnf", "install", "-y"] + packages)
        elif self.pkg_mgr == "apt":
            return self._sudo_wrap(["apt", "install", "-y"] + packages)
        elif self.pkg_mgr == "zypper":
            return self._sudo_wrap(["zypper", "install", "-y"] + packages)
        elif self.pkg_mgr == "xbps":
            return self._sudo_wrap(["xbps-install", "-S", "-y"] + packages)
        elif self.pkg_mgr == "eopkg":
            return self._sudo_wrap(["eopkg", "install", "-y"] + packages)
        elif self.pkg_mgr == "apk":
            return self._sudo_wrap(["apk", "add"] + packages)
        return []

    def get_query_command(self, package):
        if self.pkg_mgr == "pacman":
            return ["pacman", "-Qs", f"^{package}$"]
        elif self.pkg_mgr == "dnf":
            return ["rpm", "-q", package]
        elif self.pkg_mgr == "apt":
            return ["dpkg", "-s", package]
        elif self.pkg_mgr == "zypper":
            return ["rpm", "-q", package]
        elif self.pkg_mgr == "xbps":
            return ["xbps-query", "-S", package]
        elif self.pkg_mgr == "eopkg":
            return ["eopkg", "info", package]
        elif self.pkg_mgr == "apk":
            return ["apk", "info", "-e", package]
        return []

    def is_package_installed(self, package):
        cmd = self.get_query_command(package)
        if not cmd:
            return False
        try:
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False

    def get_orphans_command(self):
        if self.pkg_mgr == "pacman":
            return ["pacman", "-Qdtq"]
        elif self.pkg_mgr == "dnf":
            return ["dnf", "repoquery", "--unneeded"]
        elif self.pkg_mgr == "apt":
            return ["apt-mark", "showauto"]
        return []

    def get_orphans(self):
        cmd = self.get_orphans_command()
        if not cmd:
            return []
        try:
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            return [line.strip() for line in output.strip().split("\n") if line.strip()]
        except:
            return []

    def get_remove_command(self, packages):
        if self.pkg_mgr == "pacman":
            return self._sudo_wrap(["pacman", "-Rs", "--noconfirm"] + packages)
        elif self.pkg_mgr == "dnf":
            return self._sudo_wrap(["dnf", "remove", "-y"] + packages)
        elif self.pkg_mgr == "apt":
            return self._sudo_wrap(["apt", "autoremove", "-y"] + packages)
        elif self.pkg_mgr == "zypper":
            return self._sudo_wrap(["zypper", "remove", "-y"] + packages)
        elif self.pkg_mgr == "xbps":
            return self._sudo_wrap(["xbps-remove", "-R", "-y"] + packages)
        elif self.pkg_mgr == "eopkg":
            return self._sudo_wrap(["eopkg", "remove", "-y"] + packages)
        elif self.pkg_mgr == "apk":
            return self._sudo_wrap(["apk", "del"] + packages)
        return []

    def get_cleanup_tasks(self):
        tasks = []
        if self.pkg_mgr == "pacman":
            tasks.append({"name": "Package Cache", "cmd": self._sudo_wrap(["pacman", "-Sc", "--noconfirm"]), "description": "Clear old package downloads"})
        elif self.pkg_mgr == "dnf":
            tasks.append({"name": "DNF Cache", "cmd": self._sudo_wrap(["dnf", "clean", "all"]), "description": "Clear DNF metadata and cache"})
        elif self.pkg_mgr == "apt":
            tasks.append({"name": "APT Cache", "cmd": self._sudo_wrap(["apt", "clean"]), "description": "Clear APT package cache"})
        if os.path.exists("/usr/bin/journalctl"):
            tasks.append({"name": "System Logs", "cmd": self._sudo_wrap(["journalctl", "--vacuum-time=7d"]), "description": "Remove logs older than 7 days"})
        tasks.append({"name": "Temporary Files", "cmd": self._sudo_wrap(["rm", "-rf", "/tmp/*"]), "description": "Clear system /tmp directory"})
        
        return tasks
