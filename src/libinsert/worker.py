import subprocess
import threading
import os
import logging
from gi.repository import GLib

logger = logging.getLogger("TaskWorker")

class TaskWorker:
    def __init__(self, callback):
        self.callback = callback # to call with progress/status
        self.thread = None
        # path to our askpass helper
        self.askpass_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui", "askpass.py"))
    def run_command(self, command):
        logger.info(f"starting bg command: {' '.join(command)}")
        self.thread = threading.Thread(target=self._execute, args=(command,))
        self.thread.start()

    def _execute(self, command):
        try:
            # setup env for sudo askpass if needed (though we use pkexec mostly..)
            env = os.environ.copy()
            env["SUDO_ASKPASS"] = self.askpass_path
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )

            for line in process.stdout:
                msg = line.strip()
                if msg:
                    logger.debug(f"Worker out: {msg}")
                    GLib.idle_add(self.callback, "progress", msg)

            process.wait()
            logger.info(f"finished with return code: {process.returncode}")
            
            if process.returncode == 0:
                GLib.idle_add(self.callback, "finished", True)
            else:
                GLib.idle_add(self.callback, "error", f"Command failed with code {process.returncode}!")
        except Exception as e:
            logger.error(f"Worker exception: {e}")
            GLib.idle_add(self.callback, "error", str(e))
