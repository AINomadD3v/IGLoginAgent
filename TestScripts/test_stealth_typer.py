# TestScripts/test_stealth_typer.py

import os
import sys
import time

import uiautomator2 as u2

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Shared.Utils.logger_config import setup_logger

# --- Refactored Imports ---
from Shared.Utils.stealth_typing import StealthTyper

# --- Test Configuration ---
DEVICE_ID = None  # Use None to connect to the default device, or specify a serial ID
TEST_TEXT = "This is a stealth typer test! 123_@#$"
TEST_TIMEOUT = 10  # Seconds to wait for an input field to appear

# A generic XPath to find any editable text field on the screen.
# This is robust because it doesn't depend on a specific app's resource-id.
INPUT_FIELD_XPATH = "//android.widget.EditText"

# --- Logger for the test script ---
logger = setup_logger("StealthTyperTest")


def run_stealth_typer_test():
    """
    Connects to a device and robustly tests the StealthTyper functionality.
    """
    logger.info("--- Starting Stealth Typer Test Harness ---")

    try:
        logger.info("🔌 Connecting to device...")
        d = u2.connect(DEVICE_ID)
        logger.info(f"✅ Connected to device: {d.serial}")

        # Initialize the StealthTyper with the connected device
        typer = StealthTyper(device=d)

        # Robustly check for an input field
        logger.info(
            f"🔍 Searching for an input field with XPath: '{INPUT_FIELD_XPATH}' for {TEST_TIMEOUT} seconds..."
        )

        input_field = d.xpath(INPUT_FIELD_XPATH)
        if not input_field.wait(timeout=TEST_TIMEOUT):
            logger.error("❌ No editable text field found on the current screen.")
            logger.error(
                "    Please navigate to a screen with an input box and run the test again."
            )
            return

        logger.info("✅ Input field found. Clicking to ensure focus...")
        input_field.click()
        time.sleep(0.5)

        # Clear any existing text before typing
        try:
            d.clear_text()
            logger.info("🧼 Field cleared.")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"⚠️ Could not clear text field (this is often okay): {e}")

        # Test the typing functionality
        logger.info(f"⌨️ Typing test string: '{TEST_TEXT}'")
        typer.type_text(TEST_TEXT)
        time.sleep(1)

        # Verify the text was entered correctly
        entered_text = input_field.get_text()
        if entered_text == TEST_TEXT:
            logger.info("✅ PASSED: Text verification successful.")
        else:
            logger.error(f"❌ FAILED: Text verification failed.")
            logger.error(f"    Expected: '{TEST_TEXT}'")
            logger.error(f"    Got:      '{entered_text}'")

        # Test the Enter key press
        logger.info("⏎ Testing 'press_enter'...")
        typer.press_enter()
        logger.info("✅ 'press_enter' command sent.")

    except Exception as e:
        logger.critical(
            f"💥 A critical error occurred during the test: {e}", exc_info=True
        )
    finally:
        logger.info("--- Test Harness Finished ---")


if __name__ == "__main__":
    run_stealth_typer_test()
