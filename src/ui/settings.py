import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

class SettingsWindow(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Settings")

        page = Adw.PreferencesPage()
        page.set_title("General")
        page.set_icon_name("preferences-system-symbolic")

        group = Adw.PreferencesGroup()
        group.set_title("Behavior")
        page.add(group)

        # Theme selection
        theme_row = Adw.ComboRow()
        theme_row.set_title("Appearance")
        theme_row.set_subtitle("Choose your preferred theme.")
        model = Gtk.StringList.new(["Follow System", "Force Light", "Force Dark"])
        theme_row.set_model(model)
        
        # Initialize selection from current style manager state
        style_manager = Adw.StyleManager.get_default()
        if style_manager.get_color_scheme() == Adw.ColorScheme.FORCE_LIGHT:
            theme_row.set_selected(1)
        elif style_manager.get_color_scheme() == Adw.ColorScheme.FORCE_DARK:
            theme_row.set_selected(2)
        else:
            theme_row.set_selected(0)
            
        theme_row.connect("notify::selected", self.on_theme_changed)
        group.add(theme_row)

        # Notification Tester
        notif_test_row = Adw.ActionRow()
        notif_test_row.set_title("Test Notifications")
        notif_test_row.set_subtitle("Send a test toast to verify UI feedback.")
        notif_btn = Gtk.Button(label="Test Toast")
        notif_btn.set_valign(Gtk.Align.CENTER)
        notif_btn.connect("clicked", self.on_test_notif_clicked)
        notif_test_row.add_suffix(notif_btn)
        group.add(notif_test_row)

        # Danger Zone
        danger_group = Adw.PreferencesGroup()
        danger_group.set_title("Danger Zone")
        page.add(danger_group)

        reset_row = Adw.ActionRow()
        reset_row.set_title("Reset Application")
        reset_row.set_subtitle("This will clear your preferences and show the setup wizard again.")
        reset_btn = Gtk.Button(label="Reset")
        reset_btn.add_css_class("destructive-action")
        reset_btn.set_valign(Gtk.Align.CENTER)
        reset_btn.connect("clicked", self.on_reset_clicked)
        reset_row.add_suffix(reset_btn)
        danger_group.add(reset_row)

        self.add(page)

    def on_theme_changed(self, combo, pspec):
        style_manager = Adw.StyleManager.get_default()
        selected = combo.get_selected()
        if selected == 1:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif selected == 2:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT) # Default/Follow system

    def on_test_notif_clicked(self, button):
        win = self.get_transient_for()
        if hasattr(win, "toast_overlay"):
            toast = Adw.Toast.new("Notification system is working! :3")
            win.toast_overlay.add_toast(toast)

    def on_reset_clicked(self, button):
        app = self.get_transient_for().get_application()
        import os
        config_file = os.path.join(GLib.get_user_config_dir(), "insert-source", "config.json")
        if os.path.exists(config_file):
            os.remove(config_file)
        app.quit()
