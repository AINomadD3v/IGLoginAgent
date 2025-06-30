# Shared/Utils/stealth_typing.py

import os
import random
import subprocess
import sys
import time

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Shared.Utils.logger_config import setup_logger

logger = setup_logger(__name__)


class StealthTyper:
    """Handles typing text via ADB for reliability and speed."""

    def __init__(self, device):
        """
        Initializes the typer with an existing uiautomator2 device object.

        Args:
            device: An already connected uiautomator2.Device object.
        """
        if not device:
            raise ValueError("A connected device object must be provided.")
        self.d = device
        self.device_id = self.d.serial

    def _adb_shell(self, command: str):
        """Executes a shell command on the connected device via ADB."""
        cmd = ["adb", "-s", self.device_id, "shell", command]
        # We don't need to capture output for typing, just execute
        subprocess.run(cmd, check=True, capture_output=True)

    def type_text(self, text: str):
        """
        Types the given text into the currently focused input field using ADB.
        This method is fast and reliable for standard text.
        """
        text = text.strip()
        logger.info(f"Typing text: '{text}'")

        # ADB shell input requires escaping spaces with %s
        safe_text = text.replace(" ", "%s")
        command = f'input text "{safe_text}"'

        try:
            self._adb_shell(command)
            time.sleep(0.5)  # A brief pause to ensure text is registered
        except Exception as e:
            logger.error(f"❌ Failed to type via adb shell input: {e}")

    def press_enter(self):
        """Simulates pressing the Enter key."""
        logger.debug("Pressing Enter key.")
        self._adb_shell("input keyevent 66")  # 66 is the keycode for ENTER

    def press_tab(self):
        """Simulates pressing the Tab key."""
        logger.debug("Pressing Tab key.")
        self._adb_shell("input keyevent 61")  # 61 is the keycode for TAB
