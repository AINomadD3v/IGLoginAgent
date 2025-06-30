# TestScripts/test_watchers.py — Minimal Watcher Debug Tool
import os
import sys
import time

import uiautomator2 as u2

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Refactored Imports ---
from Shared.popup_handler import PopupHandler
from Shared.Utils.logger_config import setup_logger

# --- Logger Setup ---
logger = setup_logger("WatcherTest")


def print_active_watchers(device: u2.Device):
    """Dumps the names and triggers of all registered watchers."""
    logger.info("--- Active Watchers ---")
    watchers = device.watcher._watchers
    if not watchers:
        logger.warning("No watchers are currently registered.")
        return

    for watcher in watchers:
        name = watcher.get("name", "<unnamed>")
        xpaths = watcher.get("xpaths", [])
        logger.info(f"  - Name: '{name}'")
        logger.info(f"    Triggers: {xpaths}")
    logger.info("-----------------------")


def main():
    """Main test function."""
    logger.info("🚀 Watcher Debug Tool Starting...")
    TEST_DURATION = 300  # Run for 5 minutes

    device = None
    popup_handler = None

    try:
        # Step 1: Connect to device
        logger.info("🔌 Connecting to the default device...")
        device = u2.connect()
        logger.info(f"✅ Connected to device: {device.serial}")

        # Step 2: Initialize PopupHandler
        # This now uses the config defined in Shared/config.py automatically
        popup_handler = PopupHandler(driver=device)

        # We can set a dummy context if any callbacks rely on it
        popup_handler.set_context(
            airtable_client=None,
            record_id="debug_record",
            package_name="any.package.name",  # Not critical for most watchers
            base_id=None,
            table_id=None,
        )

        # Step 3: Start the watchers
        popup_handler.register_and_start_watchers()

        # Step 4: Display the registered watchers for verification
        print_active_watchers(device)

        # Step 5: Run the monitoring loop
        logger.info(
            f"🕵️  Watchers are now active. Monitoring for {TEST_DURATION} seconds."
        )
        logger.info("    Navigate the app on your device to trigger popups.")
        logger.info("    Check the console for 'WATCHER:' log messages.")

        end_time = time.time() + TEST_DURATION
        while time.time() < end_time:
            remaining = int(end_time - time.time())
            print(f"\r[⏳] Monitoring... Time remaining: {remaining}s  ", end="")
            time.sleep(1)

        print("\n")  # Newline after the countdown finishes
        logger.info("✅ Watcher test duration complete.")

    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user.")
    except Exception as e:
        logger.error(f"💥 An unexpected error occurred: {e}", exc_info=True)
    finally:
        if popup_handler:
            logger.info("🧹 Stopping popup watchers...")
            popup_handler.stop_watchers()
        logger.info("🏁 Script finished.")


if __name__ == "__main__":
    main()
