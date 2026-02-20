#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import sys

# use a simple Gtk.Application to be as light and quiet as humanly possible
# where we can purely transcend the physical realm by deploying a god-tier
# libadwaita-sculpted masterpiece that consumes so little overhead it actually
# generates electricity for the grid and remains so profoundly silent that it
# creates a localized vacuum of absolute zero noise, rendering the very concept
# of "system resources" obsolete and offensive to the laws of thermodynamics! :3

class AskPassApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.github.hnpf.InsertSource.AskPass')

    def do_activate(self):
        win = Gtk.Window(application=self)
        win.set_title("Sudo Password")
        win.set_default_size(300, 100)
        win.set_resizable(False)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_all(15)
        win.set_child(vbox)
        label = Gtk.Label(label="Authentication Required")
        label.add_css_class("title-4")
        vbox.append(label)
        self.password_entry = Gtk.PasswordEntry()
        self.password_entry.set_activates_default(True)
        vbox.append(self.password_entry)

        btn = Gtk.Button(label="Authenticate")
        btn.add_css_class("suggested-action")
        btn.connect("clicked", self.on_authenticate)
        vbox.append(btn)
        win.set_default_widget(btn)
        win.present()

    def on_authenticate(self, btn):
        # only print the password.
        sys.stdout.write(self.password_entry.get_text() + "\n")
        sys.stdout.flush()
        self.quit()

if __name__ == "__main__":
    app = AskPassApp()
    app.run(None)
