import os
import sys
import time

import uiautomator2 as u2

# --- Path Setup ---
# Ensures the script can find the 'Shared' and other project directories.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Project Imports ---
from Shared.instagram_actions import InstagramInteractions
from Shared.Utils.logger_config import setup_logger

# --- Test Configuration ---
DEVICE_ID = None  # Use None to connect to the first available device.
SCROLL_TEST_COUNT = 15  # Number of test scrolls to perform.
DELAY_BETWEEN_SCROLLS = 2.0  # Seconds to wait between each scroll attempt.

# --- Logger for the test script ---
logger = setup_logger("HumanoidScrollerTest")


def run_humanoid_scroller_test():
    """
    Connects to a device, detects the foreground Instagram app, and specifically
    tests the `scroll_explore_feed_proactive` function.

    PRE-REQUISITE: Before running, ensure the target Instagram app (any clone)
    is already open and on the Explore/Search grid page.
    """
    logger.info("--- Starting Humanoid Scroller Test Harness ---")

    device = None
    try:
        # Step 1: Connect to the default device
        logger.info("🔌 Connecting to device...")
        device = u2.connect(DEVICE_ID)
        logger.info(f"✅ Connected to device: {device.serial}")

        # Step 2: Automatically detect the foreground application package
        logger.info("🔍 Detecting foreground application...")
        current_app = device.app_current()
        package_name = current_app.get("package")

        if not package_name or "instagram" not in package_name.lower():
            logger.error("❌ The currently open app is not an Instagram app.")
            logger.error(f"   Detected package: {package_name}")
            logger.error(
                "   Please open the target Instagram clone to the Explore page and run the test again."
            )
            return

        logger.info(f"✅ Detected Instagram package: {package_name}")

        # Step 3: Initialize the interactions module
        insta_actions = InstagramInteractions(device, package_name)
        logger.info("🛠️ InstagramInteractions module initialized.")
        logger.info(
            f"🚀 Starting test: Will perform {SCROLL_TEST_COUNT} scroll attempts."
        )
        logger.info("=" * 50)

        # Step 4: Run the scroll test loop
        for i in range(SCROLL_TEST_COUNT):
            logger.info(f"--- Scroll attempt {i + 1}/{SCROLL_TEST_COUNT} ---")

            # Call the new, proactive function and check its return value
            scroll_performed = insta_actions.scroll_explore_feed_proactive()

            if scroll_performed:
                logger.info("✅ PASSED: Scroll was performed successfully.")
            else:
                # This is not a failure, but an expected outcome if the state is wrong.
                logger.warning(
                    "⚠️ BLOCKED: Scroll was blocked by the proactive state guard."
                )
                logger.warning(
                    "   This is the correct behavior if the app is not on the Explore Grid."
                )

            # Wait a moment to observe the result on screen
            time.sleep(DELAY_BETWEEN_SCROLLS)

        logger.info("=" * 50)
        logger.info("🎉 Test finished. All scroll attempts completed.")

    except Exception as e:
        logger.critical(
            f"💥 A critical error occurred during the test: {e}", exc_info=True
        )
    finally:
        logger.info("--- Test Harness Finished ---")


if __name__ == "__main__":
    run_humanoid_scroller_test()
