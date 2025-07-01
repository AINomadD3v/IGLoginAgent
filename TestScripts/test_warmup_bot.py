import os
import subprocess
import sys
import time
from multiprocessing import Pool

import uiautomator2 as u2

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Shared.instagram_actions import InstagramInteractions
from Shared.popup_handler import PopupHandler
from Shared.Utils.logger_config import setup_logger
from Warmup.scroller import run_warmup_session

# --- Logger for the test script ---
logger = setup_logger("ScrollerTest")


def get_connected_devices() -> list[str]:
    """
    Gets a list of connected device serial numbers using adb.
    """
    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, check=True
        )
        devices = []
        for line in result.stdout.strip().split("\n")[1:]:
            if "device" in line:
                devices.append(line.split("\t")[0])
        return devices
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logger.error(f"Error getting ADB devices: {e}")
        logger.error("Please ensure ADB is installed and in your system's PATH.")
        return []


def run_scroller_test(device_id: str):
    """
    Connects to a specific device, detects the foreground app, and runs the scroller.
    """
    logger.info(f"--- Starting Scroller Test on Device: {device_id} ---")

    device = None
    popup_handler = None
    insta_actions = None

    try:
        # Step 1: Connect to the specified device
        logger.info(f"🔌 Connecting to device: {device_id}")
        device = u2.connect(device_id)
        logger.info(f"✅ Connected to device: {device.serial}")

        # Step 2: Automatically detect the foreground application package
        logger.info("🔍 Detecting foreground application...")
        current_app = device.app_current()
        package_name = current_app.get("package")

        if not package_name or "instagram" not in package_name.lower():
            logger.error(
                f"[{device_id}] ❌ The currently open app is not an Instagram app."
            )
            logger.error(f"[{device_id}]    Detected package: {package_name}")
            return

        logger.info(f"[{device_id}] ✅ Detected Instagram package: {package_name}")

        # Step 3: Initialize all necessary components
        logger.info(f"[{device_id}] 🛠️ Initializing interactions and popup handler...")
        insta_actions = InstagramInteractions(device, package_name)
        popup_handler = PopupHandler(device)
        popup_handler.set_context(None, None, package_name, None, None)
        popup_handler.register_and_start_watchers()

        # Step 4: Run the main warmup session
        logger.info(f"[{device_id}] 🚀 Handing off to run_warmup_session...")
        logger.info("=" * 50)
        run_warmup_session(insta_actions=insta_actions)
        logger.info("=" * 50)
        logger.info(f"[{device_id}] ✅ Scroller session finished.")

    except Exception as e:
        logger.critical(
            f"[{device_id}] 💥 A critical error occurred during the test: {e}",
            exc_info=True,
        )
    finally:
        logger.info(f"--- Cleaning up test session on {device_id} ---")
        if popup_handler:
            logger.info(f"[{device_id}] 🧹 Stopping popup watchers...")
            popup_handler.stop_watchers()
        logger.info(f"--- Test Harness Finished for {device_id} ---")


if __name__ == "__main__":
    logger.info("--- Main Test Orchestrator ---")

    # Get all connected devices
    connected_devices = get_connected_devices()

    if not connected_devices:
        logger.error(
            "🚫 No devices found. Please connect your devices and ensure ADB is working."
        )
    else:
        logger.info(f"Found {len(connected_devices)} devices: {connected_devices}")
        logger.info("Starting tests in parallel...")

        # Use a process pool to run the test on all devices simultaneously
        with Pool(len(connected_devices)) as pool:
            pool.map(run_scroller_test, connected_devices)

        logger.info("🎉 All tests have completed.")
