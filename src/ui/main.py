import sys
import os
import logging
import re
import threading

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.expanduser("~/.cache/insert-source.log"))
    ]
)
logger = logging.getLogger("InsertApp")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib
from libinsert.distro import DistroManager
from libinsert.probe import SysProbe
from libinsert.worker import TaskWorker
from ui.settings import SettingsWindow

CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "insert-source")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

class InsertApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id='io.github.hnpf.InsertSource',
                         flags=Gio.ApplicationFlags.FLAGS_NONE,
                         **kwargs)
        self.distro_mgr = DistroManager()
        self.probe = SysProbe()
        self.setup_done = self._load_config()
        self.force_setup = "--reset-setup" in sys.argv
        
        self.create_actions()

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return False
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("setup_done", False)
        except:
            return False

    def save_config(self):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"setup_done": True}, f)

    def create_actions(self):
        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", self.on_settings_activated)
        self.add_action(settings_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_activated)
        self.add_action(about_action)

    def on_settings_activated(self, action, param):
        settings = SettingsWindow(transient_for=self.win)
        settings.present()

    def on_about_activated(self, action, param):
        about = Adw.AboutWindow(
            transient_for=self.win,
            application_name="Insert-source",
            application_icon="system-software-install",
            developer_name="VIREX",
            version="0.1.0",
            copyright="© 2026",
            website="https://github.com/hnpf/Insert-source"
        )
        about.present()

    def do_activate(self):
        self.win = InsertWindow(application=self)
        self.win.present()

        if os.getuid() != 0:
            toast = Adw.Toast.new("elevated tasks will prompt for password.")
            # no toast, hehe~
            #self.win.toast_overlay.add_toast(toast)
        else:
            toast = Adw.Toast.new("running as root. settings will probably not sync to the root user.")
            self.win.toast_overlay.add_toast(toast)
        
        if not self.setup_done or self.force_setup:
            GLib.timeout_add(500, self.show_setup_wizard)

    def show_setup_wizard(self):
        wizard = SetupWizard(transient_for=self.win)
        wizard.connect("close-request", lambda x: self.save_config())
        wizard.present()
        return False

class SetupWizard(Adw.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Setup Wizard")
        self.set_modal(True)
        self.set_default_size(600, 500)
        self.toolbar_view = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(self.header)
        self.back_btn = Gtk.Button(icon_name="go-previous-symbolic")
        self.back_btn.set_visible(False)
        self.back_btn.connect("clicked", self.on_back_clicked)
        self.header.pack_start(self.back_btn)
        close_btn = Gtk.Button(label="Skip")
        close_btn.connect("clicked", lambda x: self.close())
        self.header.pack_end(close_btn)

        self.carousel = Adw.Carousel()
        self.carousel.set_allow_scroll_wheel(True)
        self.carousel.set_hexpand(True)
        self.carousel.set_vexpand(True)
        self.carousel.connect("page-changed", self.on_page_changed)
        
        def wrap_page(widget):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.set_hexpand(True)
            box.set_vexpand(True)
            clamp = Adw.Clamp()
            clamp.set_maximum_size(450)
            clamp.set_child(widget)
            box.append(clamp)
            return box

        # 1
        page1 = Adw.StatusPage(title="Welcome to Insert!", description="The easy route to manage hardware drivers.")
        emoji_label = Gtk.Label()
        emoji_label.set_markup('<span font_size="64pt">👋</span>')
        emoji_label.set_margin_bottom(24)
        
        p1_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        p1_box.append(emoji_label)
        btn1 = Gtk.Button(label="Continue", halign=Gtk.Align.CENTER)
        btn1.add_css_class("pill")
        btn1.connect("clicked", lambda x: self.carousel.scroll_to(self.carousel.get_nth_page(1), True))
        p1_box.append(btn1)
        page1.set_child(p1_box)

        # 2
        page2 = Adw.StatusPage(title="Detection", description="We scan PCI and USB devices.", icon_name="preferences-desktop-display-symbolic")
        btn2 = Gtk.Button(label="Continue", halign=Gtk.Align.CENTER)
        btn2.add_css_class("pill")
        btn2.connect("clicked", lambda x: self.carousel.scroll_to(self.carousel.get_nth_page(2), True))
        page2.set_child(btn2)

        # 3
        page3 = Adw.StatusPage(title="Ready?", description="Rescan anytime from the sidebar.", icon_name="system-software-install-symbolic")
        btn3 = Gtk.Button(label="Finish Setup", halign=Gtk.Align.CENTER)
        btn3.add_css_class("suggested-action")
        btn3.add_css_class("pill")
        btn3.connect("clicked", lambda x: self.close())
        page3.set_child(btn3)

        self.carousel.append(wrap_page(page1))
        self.carousel.append(wrap_page(page2))
        self.carousel.append(wrap_page(page3))

        dots = Adw.CarouselIndicatorDots(carousel=self.carousel)
        dots.set_margin_bottom(12)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.append(self.carousel)
        vbox.append(dots)

        self.toolbar_view.set_content(vbox)
        self.set_content(self.toolbar_view)

    def on_page_changed(self, carousel, index):
        self.back_btn.set_visible(index > 0)

    def on_back_clicked(self, button):
        current = int(self.carousel.get_position())
        self.carousel.scroll_to(self.carousel.get_nth_page(current - 1), True)

class InsertWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Insert-source")
        self.set_default_size(950, 650)

        # overlay at the very top
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # navigation split View
        self.split_view = Adw.NavigationSplitView()
        self.toast_overlay.set_child(self.split_view)

        # sidebar!
        sidebar_page = Adw.NavigationPage(title="Menu")
        sidebar_toolbar = Adw.ToolbarView()
        sidebar_header = Adw.HeaderBar()
        sidebar_toolbar.add_top_bar(sidebar_header)
        
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.connect("row-selected", self.on_sidebar_row_selected)
        
        self.add_sidebar_row("Overview", "status", "view-pin-symbolic")
        self.add_sidebar_row("Drivers", "drivers", "preferences-system-devices-symbolic")
        self.add_sidebar_row("Essentials", "essentials", "system-run-symbolic")
        self.add_sidebar_row("Optional Tools", "optional", "star-new-symbolic")
        self.add_sidebar_row("Cleanup", "cleanup", "user-trash-symbolic")
        self.add_sidebar_row("System Info", "info", "dialog-information-symbolic")
        
        sidebar_toolbar.set_content(self.sidebar_list)
        sidebar_page.set_child(sidebar_toolbar)
        self.split_view.set_sidebar(sidebar_page)

        # Content
        content_page = Adw.NavigationPage(title="Content")
        self.content_toolbar = Adw.ToolbarView()
        self.header_bar = Adw.HeaderBar()
        
        self.window_title = Adw.WindowTitle()
        self.header_bar.set_title_widget(self.window_title)

        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu = Gio.Menu.new()
        menu.append("Settings", "app.settings")
        menu.append("About", "app.about")
        menu_btn.set_menu_model(menu)
        self.header_bar.pack_end(menu_btn)
        
        self.content_toolbar.add_top_bar(self.header_bar)
        
        self.main_stack = Gtk.Stack()
        self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.setup_pages()
        
        self.content_toolbar.set_content(self.main_stack)
        content_page.set_child(self.content_toolbar)
        self.split_view.set_content(content_page)

        self.worker = TaskWorker(self.on_worker_event)

    def add_sidebar_row(self, title, name, icon):
        row = Adw.ActionRow(title=title)
        row.name = name
        row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        self.sidebar_list.append(row)

    def setup_pages(self):
        # Page 1: Status
        self.status_page = Adw.StatusPage(title="All Clear!", description="System is up to date.", icon_name="object-select-symbolic")
        
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, halign=Gtk.Align.CENTER)
        
        btn = Gtk.Button(label="Scan Hardware", halign=Gtk.Align.CENTER)
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.connect("clicked", self.on_rescan_clicked)
        status_box.append(btn)
        
        refresh_btn = Gtk.Button(label="Refresh Database", halign=Gtk.Align.CENTER)
        refresh_btn.add_css_class("pill")
        refresh_btn.connect("clicked", self.on_refresh_clicked)
        status_box.append(refresh_btn)

        self.fw_update_btn = Gtk.Button(label="Update Firmware", halign=Gtk.Align.CENTER)
        self.fw_update_btn.add_css_class("pill")
        self.fw_update_btn.add_css_class("suggested-action")
        self.fw_update_btn.connect("clicked", self.on_fw_update_clicked)
        self.fw_update_btn.set_visible(False)
        status_box.append(self.fw_update_btn)
        
        self.status_page.set_child(status_box)
        
        # Page 2: Drivers
        self.drivers_stack = Gtk.Stack()
        self.drivers_empty = Adw.StatusPage(title="No Drivers Needed", description="All hardware drivers are installed.", icon_name="object-select-symbolic")
        self.drivers_scroll = Gtk.ScrolledWindow()
        
        self.driver_list = Gtk.ListBox()
        self.driver_list.add_css_class("boxed-list")
        self.driver_list.set_margin_top(12)
        self.driver_list.set_margin_bottom(12)
        
        drivers_clamp = Adw.Clamp()
        drivers_clamp.set_maximum_size(600)
        drivers_clamp.set_child(self.driver_list)
        
        self.drivers_scroll.set_child(drivers_clamp)
        self.drivers_stack.add_named(self.drivers_empty, "empty")
        self.drivers_stack.add_named(self.drivers_scroll, "list")

        # Page 3: Essentials
        self.essentials_scroll = Gtk.ScrolledWindow()
        self.essentials_list = Gtk.ListBox()
        self.essentials_list.add_css_class("boxed-list")
        self.essentials_list.set_margin_top(12)
        self.essentials_list.set_margin_bottom(12)
        
        essentials_clamp = Adw.Clamp()
        essentials_clamp.set_maximum_size(600)
        essentials_clamp.set_child(self.essentials_list)
        self.essentials_scroll.set_child(essentials_clamp)

        # Page 4: Optional
        self.optional_scroll = Gtk.ScrolledWindow()
        self.optional_list = Gtk.ListBox()
        self.optional_list.add_css_class("boxed-list")
        self.optional_list.set_margin_top(12)
        self.optional_list.set_margin_bottom(12)
        
        optional_clamp = Adw.Clamp()
        optional_clamp.set_maximum_size(600)
        optional_clamp.set_child(self.optional_list)
        self.optional_scroll.set_child(optional_clamp)

        # Page 5: Cleanup
        self.cleanup_scroll = Gtk.ScrolledWindow()
        self.cleanup_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.cleanup_status = Adw.StatusPage(title="Cleanup", description="Remove orphaned packages.", icon_name="user-trash-symbolic")
        self.cleanup_btn = Gtk.Button(label="Scan for Orphans", halign=Gtk.Align.CENTER)
        self.cleanup_btn.add_css_class("pill")
        self.cleanup_btn.connect("clicked", self.on_cleanup_scan_clicked)
        self.cleanup_status.set_child(self.cleanup_btn)
        
        self.orphans_list = Gtk.ListBox()
        self.orphans_list.add_css_class("boxed-list")
        self.orphans_list.set_margin_top(12)
        self.orphans_list.set_margin_bottom(12)
        self.orphans_list.set_visible(False)

        self.cleanup_list = Gtk.ListBox()
        self.cleanup_list.add_css_class("boxed-list")
        self.cleanup_list.set_margin_top(12)
        self.cleanup_list.set_margin_bottom(24)

        self.cleanup_vbox.append(self.cleanup_status)
        
        cleanup_clamp = Adw.Clamp()
        cleanup_clamp.set_maximum_size(600)
        
        inner_cleanup_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        inner_cleanup_box.append(self.cleanup_list)
        inner_cleanup_box.append(self.orphans_list)
        
        cleanup_clamp.set_child(inner_cleanup_box)
        self.cleanup_vbox.append(cleanup_clamp)
        self.cleanup_scroll.set_child(self.cleanup_vbox)

        # Page 6: System Info
        self.info_scroll = Gtk.ScrolledWindow()
        self.info_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.info_vbox.set_margin_top(24)
        self.info_vbox.set_margin_bottom(24)
        
        info_header = Gtk.Label(label="System Details")
        info_header.add_css_class("title-1")
        info_header.set_margin_bottom(12)
        self.info_vbox.append(info_header)
        
        self.info_list = Gtk.ListBox()
        self.info_list.add_css_class("boxed-list")
        
        info_clamp = Adw.Clamp()
        info_clamp.set_maximum_size(600)
        info_clamp.set_child(self.info_list)
        
        self.info_vbox.append(info_clamp)
        self.info_scroll.set_child(self.info_vbox)

        self.main_stack.add_named(self.status_page, "status")
        self.main_stack.add_named(self.drivers_stack, "drivers")
        self.main_stack.add_named(self.essentials_scroll, "essentials")
        self.main_stack.add_named(self.optional_scroll, "optional")
        self.main_stack.add_named(self.cleanup_scroll, "cleanup")
        self.main_stack.add_named(self.info_scroll, "info")

    def on_sidebar_row_selected(self, listbox, row):
        if row:
            self.main_stack.set_visible_child_name(row.name)
            self.window_title.set_title(row.get_title())
            if row.name == "essentials":
                self.update_essentials_list()
            elif row.name == "optional":
                self.update_optional_list()
            elif row.name == "drivers":
                self.on_rescan_clicked(None)
            elif row.name == "cleanup":
                self.update_cleanup_page()
            elif row.name == "info":
                self.update_info_page()

    def update_cleanup_page(self):
        # clear general cleanup list
        child = self.cleanup_list.get_first_child()
        while child:
            self.cleanup_list.remove(child)
            child = self.cleanup_list.get_first_child()
            
        tasks = self.get_application().distro_mgr.get_cleanup_tasks()
        for task in tasks:
            row = Adw.ActionRow(title=task["name"], subtitle=task["description"])
            btn = Gtk.Button(label="Clean", valign=Gtk.Align.CENTER)
            btn.add_css_class("flat")
            btn.connect("clicked", lambda x, t=task: self.run_cleanup_task(t))
            row.add_suffix(btn)
            self.cleanup_list.append(row)

        # trigger orphan scan
        self.on_cleanup_scan_clicked(None)

    def run_cleanup_task(self, task):
        self.toast_overlay.add_toast(Adw.Toast.new(f"Running {task['name']}..."))
        self.worker.run_command(task["cmd"])

    def update_info_page(self):
        info = self.get_application().probe.get_system_info()
        
        # clear list
        child = self.info_list.get_first_child()
        while child:
            self.info_list.remove(child)
            child = self.info_list.get_first_child()

        items = [
            ("OS", info["os"], "software-update-available-symbolic"),
            ("Kernel", info["kernel"], "utilities-terminal-symbolic"),
            ("Desktop", info["desktop"], "preferences-desktop-wallpaper-symbolic"),
            ("Session", info["session"], "window-new-symbolic"),
            ("CPU", info["cpu"], "computer-symbolic"),
            ("GPU", info["gpu"], "video-display-symbolic"),
            ("RAM", info["ram"], "drive-multidisk-symbolic")
        ]

        for title, value, icon in items:
            row = Adw.ActionRow(title=title, subtitle=str(value))
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            self.info_list.append(row)

    def update_essentials_list(self):
        family = self.get_application().distro_mgr.family
        essentials = self.get_application().probe.drivers_db.get("essentials", {}).get(family, [])
        self._update_package_list(self.essentials_list, essentials)

    def update_optional_list(self):
        # cool tools!
        optional_tools = [
            "ani-cli", "pokemon-colorscripts", "fastfetch",
            "cava", "btop", "htop", "ranger", "fish", "zsh", "starship",
            "vlc", "mpv", "telegram-desktop", "discord", "obs-studio",
            "steam", "lutris", "bottles", "kitty", "alacritty", "yt-dlp",
            "qbittorrent", "stremio", "prism-launcher", "heroic-games-launcher-bin"
        ]
        logger.info(f"Updating optional tools list: {len(optional_tools)} tools found")
        self._update_package_list(self.optional_list, optional_tools)

    def _update_package_list(self, listbox, packages):
        child = listbox.get_first_child()
        while child:
            listbox.remove(child)
            child = listbox.get_first_child()

        if not packages:
            row = Adw.ActionRow(title="No packages found", subtitle="Check your internet connection or data files.")
            listbox.append(row)
            return

        for pkg in packages:
            installed = self.get_application().distro_mgr.is_package_installed(pkg)
            row = Adw.ActionRow(title=pkg)
            row.set_subtitle("Installed" if installed else "Available for installation")
            
            icon_name = "object-select-symbolic" if installed else "system-software-install-symbolic"
            row.add_prefix(Gtk.Image.new_from_icon_name(icon_name))
            
            if not installed:
                btn = Gtk.Button(label="Install", valign=Gtk.Align.CENTER)
                btn.add_css_class("flat")
                btn.connect("clicked", lambda x, p=pkg: self.install_package(p))
                row.add_suffix(btn)
            
            listbox.append(row)

    def on_fw_update_clicked(self, button):
        logger.info("Firmware update requested")
        cmd = self.get_application().distro_mgr._sudo_wrap(["fwupdmgr", "update", "-y"])
        logger.info(f"Running firmware update command: {cmd}")
        self.toast_overlay.add_toast(Adw.Toast.new("Updating firmware... This might take a while."))
        self.worker.run_command(cmd)

    def on_refresh_clicked(self, button):
        # refresh package database and firmware metadata in worker
        pkg_cmd = self.get_application().distro_mgr.refresh_database()
        
        fw_cmd_str = "pkexec fwupdmgr refresh"
        if os.getuid() == 0:
            fw_cmd_str = "fwupdmgr refresh"
            
        if pkg_cmd:
            # combine commands if possible or just run them as a shell script string
            # taskWorker takes a list for subprocess.Popen, so we will use a wrapper
            cmd_list = ["bash", "-c", f"{' '.join(pkg_cmd)} && {fw_cmd_str}"]
            logger.info(f"Refreshing all databases: {cmd_list}")
            self.toast_overlay.add_toast(Adw.Toast.new("Refreshing databases..."))
            self.worker.run_command(cmd_list)
        else:
            # just firmware
            cmd_list = ["bash", "-c", fw_cmd_str]
            self.worker.run_command(cmd_list)

    def on_rescan_clicked(self, button):
        logger.info("Hardware rescan requested")
        family = self.get_application().distro_mgr.family
        logger.debug(f"Scanning for distro family: {family}")
        matches = self.get_application().probe.find_needed_packages(family)
        logger.info(f"Scan complete. Found {len(matches)} driver matches in database.")
        
        # enrich matches with installation status
        for match in matches:
            match["missing_packages"] = [p for p in match["packages"] if not self.get_application().distro_mgr.is_package_installed(p)]
            match["is_installed"] = len(match["missing_packages"]) == 0
        
        if matches:
            self.update_driver_list(matches)
            self.drivers_stack.set_visible_child_name("list")
        else:
            self.drivers_stack.set_visible_child_name("empty")
            if button:
                self.toast_overlay.add_toast(Adw.Toast.new("No matching hardware found in database."))
                
        # also check for firmware updates in background to avoid freezing the UI
        def check_fw():
            fw_updates = self.get_application().probe.get_firmware_updates()
            GLib.idle_add(self.apply_fw_status, fw_updates, matches)
            
        threading.Thread(target=check_fw, daemon=True).start()

    def apply_fw_status(self, fw_updates, matches):
        if fw_updates:
            logger.info(f"Firmware updates found: {fw_updates}")
            self.fw_update_btn.set_visible(True)
            self.status_page.set_title("Updates Available")
            self.status_page.set_description("Firmware updates were found for your hardware.")
            self.status_page.set_icon_name("software-update-available-symbolic")
            self.toast_overlay.add_toast(Adw.Toast.new("Firmware updates available!"))
        else:
            self.fw_update_btn.set_visible(False)
            any_missing = any(not m["is_installed"] for m in matches)
            if not any_missing:
                self.status_page.set_title("All Clear")
                self.status_page.set_description("System is up to date.")
                self.status_page.set_icon_name("object-select-symbolic")
        return False # stop GLib timeout

    def update_driver_list(self, matches):
        child = self.driver_list.get_first_child()
        while child:
            self.driver_list.remove(child)
            child = self.driver_list.get_first_child()
            
        for match in matches:
            # get a cleaner device name
            device_name = match["driver_name"]
            raw = match["device_raw"]
            sub = f"Category: {match['category'].upper()}"
            parts = re.findall(r'\"(.*?)\"', raw)
            if len(parts) >= 3:
                sub = f"{parts[1]} | {parts[2]}"

            row = Adw.ActionRow(title=match["driver_name"], subtitle=sub)
            
            if match["is_installed"]:
                icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                icon.add_css_class("success")
                row.add_prefix(icon)
                
                label = Gtk.Label(label="Installed")
                label.add_css_class("dim-label")
                row.add_suffix(label)
            else:
                row.add_prefix(Gtk.Image.new_from_icon_name("system-software-install-symbolic"))
                
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
                for pkg in match["missing_packages"]:
                    btn = Gtk.Button(label=f"Install {pkg}")
                    btn.add_css_class("flat")
                    btn.connect("clicked", lambda x, p=pkg: self.install_package(p))
                    vbox.append(btn)
                row.add_suffix(vbox)
                
            self.driver_list.append(row)

    def on_cleanup_scan_clicked(self, button):
        orphans = self.get_application().distro_mgr.get_orphans()
        if orphans:
            self.cleanup_status.set_visible(False)
            self.orphans_list.set_visible(True)
            self.update_orphans_list(orphans)
        else:
            self.toast_overlay.add_toast(Adw.Toast.new("No orphans found! Your system is clean."))

    def update_orphans_list(self, orphans):
        child = self.orphans_list.get_first_child()
        while child:
            self.orphans_list.remove(child)
            child = self.orphans_list.get_first_child()
        for pkg in orphans:
            row = Adw.ActionRow(title=pkg, subtitle="Orphaned package")
            btn = Gtk.Button(label="Remove", valign=Gtk.Align.CENTER)
            btn.add_css_class("destructive-action")
            btn.add_css_class("flat")
            btn.connect("clicked", lambda x, p=pkg: self.remove_package(p))
            row.add_suffix(btn)
            self.orphans_list.append(row)

    def install_package(self, pkg):
        cmd = self.get_application().distro_mgr.get_install_command([pkg])
        logger.info(f"Installing package: {pkg} with command: {cmd}")
        self.toast_overlay.add_toast(Adw.Toast.new(f"Installing {pkg}..."))
        self.worker.run_command(cmd)

    def remove_package(self, pkg):
        cmd = self.get_application().distro_mgr.get_remove_command([pkg])
        logger.info(f"Removing package: {pkg} with command: {cmd}")
        self.toast_overlay.add_toast(Adw.Toast.new(f"Removing {pkg}..."))
        self.worker.run_command(cmd)

    def on_worker_event(self, event_type, data):
        if event_type == "finished":
            logger.info("Task worker finished successfully")
            self.toast_overlay.add_toast(Adw.Toast.new("Task finished!"))
            self.on_rescan_clicked(None)
            self.update_essentials_list()
        elif event_type == "error":
            logger.error(f"Task worker error: {data}")
            self.toast_overlay.add_toast(Adw.Toast.new(f"Error: {data}"))

if __name__ == "__main__":
    app = InsertApp()
    app.run(sys.argv)
