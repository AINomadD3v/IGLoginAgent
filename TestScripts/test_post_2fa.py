# TestScripts/test_post_2fa.py

import os
import sys
import time

import uiautomator2 as u2

# --- Path Setup ---
# This ensures the script can find the 'Shared' and other project directories
# when run directly from the command line.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Refactored Imports ---
from Login.login_bot import InstagramLoginHandler
from Shared.instagram_actions import InstagramInteractions
from Shared.popup_handler import PopupHandler
from Shared.Utils.logger_config import setup_logger
from Shared.Utils.stealth_typing import StealthTyper

# --- Test Configuration ---
DEVICE_ID = "R5CR7027Y7W"  # Your specific device's serial ID
PACKAGE_NAME = "com.instagram.android"  # Change if using a cloned app

# --- Logger for the test script ---
test_logger = setup_logger("Post2FATestHarness")


def run_test():
    """
    Connects to a device and tests the post-2FA logic.

    PRE-REQUISITE: Before running, manually get the Instagram app to the state
    immediately after entering the 2FA code, where the "Save your login
    information?" popup is VISIBLE on the screen.
    """
    test_logger.info("--- Starting Post-2FA Test Harness ---")
    test_logger.info(f"Targeting device: {DEVICE_ID}")
    test_logger.info(f"Targeting package: {PACKAGE_NAME}")

    popup_handler = None
    try:
        d = u2.connect(DEVICE_ID)
        test_logger.info(f"✅ Successfully connected to device: {d.serial}")

        # 1. Initialize the PopupHandler.
        test_logger.info("Initializing PopupHandler and starting watchers...")
        popup_handler = PopupHandler(driver=d)
        popup_handler.set_context(None, None, PACKAGE_NAME, None, None)
        popup_handler.register_and_start_watchers()

        # 2. Initialize the InstagramLoginHandler
        test_logger.info("Initializing InstagramLoginHandler...")
        interactions = InstagramInteractions(device=d, app_package=PACKAGE_NAME)
        typer = StealthTyper(device_id=d.serial)

        login_handler = InstagramLoginHandler(
            device=d,
            interactions=interactions,
            stealth_typer=typer,
            popup_handler=popup_handler,  # Pass the initialized handler
        )

        # 3. RUN THE TARGETED TEST
        test_logger.warning("=" * 50)
        test_logger.warning(">>> ACTION REQUIRED <<<")
        test_logger.warning(
            "Manually ensure the 'Save your login info?' popup is VISIBLE on the device NOW."
        )
        test_logger.info("Starting the test in 10 seconds...")
        test_logger.warning("=" * 50)

        for i in range(10, 0, -1):
            print(f"\rStarting in {i} seconds... ", end="")
            time.sleep(1)
        print("\n")

        test_logger.info("Executing `verify_login_after_2fa`...")
        result = login_handler.verify_login_after_2fa(timeout=30)

        test_logger.info("--- TEST COMPLETE ---")
        if result == "login_success":
            test_logger.info(f"✅ PASSED: Final result is '{result.upper()}'")
        else:
            test_logger.error(f"❌ FAILED: Final result is '{result.upper()}'")
            test_logger.error(
                "Check the screenshot on the device/emulator for the final screen state."
            )

    except Exception as e:
        test_logger.error(
            f"💥 A critical error occurred in the test harness: {e}", exc_info=True
        )
    finally:
        if popup_handler:
            test_logger.info("Stopping popup watchers...")
            popup_handler.stop_watchers()
        test_logger.info("--- Test Harness Finished ---")


if __name__ == "__main__":
    run_test()
