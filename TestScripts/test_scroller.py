# TestScripts/test_scroller.py

import os
import sys
import time

import uiautomator2 as u2

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Shared.instagram_actions import InstagramInteractions
from Shared.popup_handler import PopupHandler
from Shared.Utils.logger_config import setup_logger

# --- Refactored Imports ---
# We import the main function from the scroller module to test it directly
from Warmup.scroller import run_warmup_session

# --- Test Configuration ---
DEVICE_ID = None  # Use None to connect to the default device, or specify a serial ID

# --- Logger for the test script ---
logger = setup_logger("ScrollerTest")


def run_scroller_test():
    """
    Connects to a device, detects the foreground app, and tests the scroller functionality.

    PRE-REQUISITE: Before running, ensure the target Instagram app (any clone)
    is already open and logged in on the device's home screen.
    """
    logger.info("--- Starting Scroller Test Harness ---")

    device = None
    popup_handler = None
    insta_actions = None

    try:
        # Step 1: Connect to the device
        logger.info("🔌 Connecting to device...")
        # FIX: Call connect() without arguments if DEVICE_ID is None
        if DEVICE_ID:
            device = u2.connect(DEVICE_ID)
        else:
            device = u2.connect()
        logger.info(f"✅ Connected to device: {device.serial}")

        # Step 2: Automatically detect the foreground application package
        logger.info("🔍 Detecting foreground application...")
        current_app = device.app_current()
        package_name = current_app.get("package")

        if not package_name or "instagram" not in package_name.lower():
            logger.error("❌ The currently open app is not an Instagram app.")
            logger.error(f"    Detected package: {package_name}")
            logger.error(
                "    Please open the target Instagram clone and run the test again."
            )
            return

        logger.info(f"✅ Detected Instagram package: {package_name}")

        # Step 3: Initialize all necessary components
        logger.info("🛠️ Initializing interactions and popup handler...")
        insta_actions = InstagramInteractions(device, package_name)
        popup_handler = PopupHandler(device)

        # Context is minimal as this is just for the scroller
        popup_handler.set_context(None, None, package_name, None, None)
        popup_handler.register_and_start_watchers()

        # Step 4: Run the main warmup session from the scroller script
        logger.info("🚀 Handing off to run_warmup_session...")
        logger.info("=" * 50)

        # This calls the exact same logic that the main login_bot would call
        run_warmup_session(insta_actions=insta_actions)

        logger.info("=" * 50)
        logger.info("✅ Scroller session finished.")

    except Exception as e:
        logger.critical(
            f"💥 A critical error occurred during the test: {e}", exc_info=True
        )
    finally:
        logger.info("--- Cleaning up test session ---")
        if popup_handler:
            logger.info("🧹 Stopping popup watchers...")
            popup_handler.stop_watchers()
        logger.info("--- Test Harness Finished ---")


if __name__ == "__main__":
    run_scroller_test()
