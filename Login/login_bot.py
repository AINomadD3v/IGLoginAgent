# Login/login_bot.py

import os
import sys
import time
from typing import Optional

import uiautomator2 as u2
from dotenv import load_dotenv
from uiautomator2 import UiObjectNotFoundError

load_dotenv()

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Shared.config import XpathConfig

# --- Refactored Imports ---
from Shared.get_imap_code import get_instagram_verification_code
from Shared.instagram_actions import InstagramInteractions
from Shared.nord import main_flow as rotate_nordvpn_ip
from Shared.popup_handler import PopupHandler
from Shared.Utils.airtable_manager import AirtableClient
from Shared.Utils.logger_config import setup_logger
from Shared.Utils.stealth_typing import StealthTyper
from Warmup.scroller import run_warmup_for_account

# --- Logger Setup ---
module_logger = setup_logger(__name__)


class InstagramLoginHandler:
    """Handles the Instagram login process, including 2FA, and detects post-login states."""

    def __init__(
        self,
        device: u2.Device,
        interactions: InstagramInteractions,
        stealth_typer: StealthTyper,
        popup_handler: PopupHandler,
        airtable_client: Optional[AirtableClient] = None,
        record_id: Optional[str] = None,
        # base_id and table_id are no longer needed here
    ):
        self.d = device
        self.interactions = interactions
        self.popup_handler = popup_handler
        self.xpaths = XpathConfig(interactions.app_package)
        self.typer = stealth_typer
        self.logger = setup_logger(self.__class__.__name__)
        self.airtable_client = airtable_client
        self.record_id = record_id
        # This block is no longer needed
        # if airtable_client and base_id and table_id:
        #     airtable_client.base_id = base_id
        #     airtable_client.table_id = table_id
        self.package_name = self.interactions.app_package
        self.current_username: Optional[str] = None
        self.logger.debug(f"Initialized Login Handler for package: {self.package_name}")

    def execute_login(
        self, username: str, password: str, email_address: str, email_password: str
    ) -> str:
        """The core login logic, preserved from the original script."""
        try:
            self.logger.info(f"--- Starting Instagram Login for: {username} ---")
            self.current_username = username

            if not self.interactions.wait_for_element_appear(
                self.xpaths.login_page_identifier, timeout=20
            ):
                self.logger.error("❌ Timed out waiting for the login page.")
                return "error"
            self.logger.info("✅ Login page identified.")

            # Enter username
            username_field = self.d.xpath(self.xpaths.login_username_field)
            if not username_field.wait(timeout=5):
                return "error"
            username_field.click()
            time.sleep(0.5)
            self.d.clear_text()
            time.sleep(0.3)
            self.typer.type_text(username)

            # Enter password
            password_field = self.d.xpath(self.xpaths.login_password_field)
            if not password_field.wait(timeout=5):
                return "error"
            password_field.click()
            time.sleep(0.5)
            self.d.clear_text()
            time.sleep(0.3)
            self.typer.type_text(password)

            if not self.interactions.click_by_xpath(
                self.xpaths.login_button, timeout=5
            ):
                return "error"

            self.logger.info("Login clicked. Waiting for loading to complete.")
            if self.interactions.wait_for_element_appear(
                self.xpaths.login_loading_indicator, timeout=5
            ):
                if not self.interactions.wait_for_element_vanish(
                    self.xpaths.login_loading_indicator, timeout=45
                ):
                    self.logger.error("❌ Loading indicator did not disappear.")
                    return "error"
                self.logger.info("✅ Loading process finished.")

            # Post-login checks
            if self.interactions.wait_for_element_appear(
                self.xpaths.incorrect_password_text, timeout=2
            ):
                self.logger.warning("❌ Incorrect Password error detected!")
                self._update_airtable_status({"Status": "Login Failed - Incorrect PW"})
                return "login_failed"

            if self.interactions.wait_for_element_appear(
                self.xpaths.two_fa_page_identifier, timeout=5
            ):
                self.logger.info("✅ 2FA screen detected. Starting 2FA handler...")
                return self.handle_2fa(email_address, email_password)

            final_state = self.detect_post_login_state(username, timeout=20)
            if final_state == "login_success":
                self._update_airtable_status(
                    {"Logged In?": True, "Status": "Logged In - Active"}
                )
                return "login_success"
            elif final_state == "2fa_required":
                return self.handle_2fa(email_address, email_password)
            elif final_state == "account_suspended":
                self._update_airtable_status({"Status": "Banned"})
                return "account_banned"
            else:
                self._update_airtable_status({"Status": "Login Failed - Unknown State"})
                return "timeout_or_unknown"

        except Exception as e:
            self.logger.error(f"💥 Unexpected Error during login: {e}", exc_info=True)
            self._update_airtable_status({"Status": f"Login Error: {type(e).__name__}"})
            return "error"

    def detect_post_login_state(self, username: str, timeout: int = 30) -> str:
        """Detects the state after submitting login credentials."""
        self.logger.info("🔍 Detecting post-login state...")
        checks = {
            "login_success": [
                self.xpaths.save_login_info_prompt,
                self.xpaths.turn_on_notifications_prompt,
                self.xpaths.home_feed_identifier,
            ],
            "2fa_required": [
                self.xpaths.two_fa_page_identifier,
                self.xpaths.two_fa_code_input,
            ],
            "account_suspended": [self.xpaths.account_suspended_text],
        }
        start_time = time.time()
        while time.time() - start_time < timeout:
            for state, xpaths in checks.items():
                for xpath in xpaths:
                    if self.interactions.element_exists(xpath):
                        self.logger.info(f"✅ Detected UI indicating state: {state}")
                        return state
            time.sleep(1.0)
        self.logger.error(
            f"⏰ Timeout ({timeout}s): No known post-login state detected."
        )
        return "unknown"

    # In Login/login_bot.py

    def handle_2fa(self, email_address: str, email_password: str) -> str:
        """Handles the 2FA process by fetching a code, focusing the input, and typing with StealthTyper."""
        self.logger.info("--- Starting 2FA Handling Process ---")

        # --- (Code fetching logic remains the same) ---
        verification_code = None
        max_retries = 5
        retry_delay = 15

        for attempt in range(max_retries):
            self.logger.info(
                f"Attempting to fetch 2FA code for '{email_address}'... (Attempt {attempt + 1}/{max_retries})"
            )
            code = get_instagram_verification_code(
                email_address, email_password, debug=True
            )
            if code:
                self.logger.info("✅ Code found!")
                verification_code = code
                break
            self.logger.warning(
                f"Code not found. Waiting {retry_delay} seconds before retrying..."
            )
            time.sleep(retry_delay)

        if not verification_code:
            self.logger.error("❌ Failed to retrieve 2FA code after all attempts.")
            return "2fa_failed"

        self.logger.info(f"✅ Successfully retrieved 2FA code: {verification_code}")

        # --- START: REVISED LOGIC USING STEALTH TYPER ---
        self.logger.info("Entering the 6-digit code using StealthTyper...")

        # 1. Find and click the input field to give it focus. THIS IS THE KEY STEP.
        if not self.interactions.click_by_xpath(
            self.xpaths.two_fa_code_input, timeout=10
        ):
            self.logger.error(
                "❌ Could not find or click the 2FA input field to focus it."
            )
            return "2fa_failed"

        self.logger.info("✅ 2FA input field clicked and focused.")
        time.sleep(0.5)  # Small delay to ensure focus is set

        # 2. Use your existing StealthTyper to type the code into the now-focused field.
        self.typer.type_text(verification_code)
        time.sleep(1)  # Wait for the UI to process the input and enable the button.

        # --- END: REVISED LOGIC ---

        # 3. Click the confirmation button, which should now be enabled.
        if self.interactions.click_by_xpath(
            self.xpaths.two_fa_confirm_button, timeout=5
        ):
            self.logger.info("Clicked the 2FA confirmation button.")
        else:
            self.logger.error("Could not find or click the 2FA confirmation button.")
            return "2fa_failed"

        final_state = self.verify_login_after_2fa(timeout=45)
        if final_state == "login_success":
            return "login_success"
        else:
            self.logger.error(
                f"Login failed after submitting 2FA. Final state: {final_state}"
            )
            return "2fa_failed"

    def verify_login_after_2fa(self, timeout: int = 45) -> str:
        """Waits for popups to be handled and verifies login success."""
        self.logger.info("Verifying login after 2FA submission...")
        event_handled = self.popup_handler.save_info_prompt_handled.wait(
            timeout=timeout
        )
        if not event_handled:
            self.logger.error(
                "❌ Timed out waiting for the 'Save Info' popup to be handled."
            )
            return "login_failed"

        self.logger.info(
            "✅ 'Save Info' popup handled. Performing final check for home screen."
        )
        time.sleep(3.0)

        if self.interactions.wait_for_element_appear(
            self.xpaths.home_feed_identifier, timeout=15
        ):
            return "login_success"
        else:
            self.logger.error("❌ Failed final verification. Home screen not found.")
            return "login_failed"

    def _update_airtable_status(self, status_map: dict):
        """Helper to update Airtable with the current status."""
        if not (self.airtable_client and self.record_id):
            return

        try:
            # The new update_record method requires the table object
            accounts_table = self.airtable_client.accounts_table
            self.airtable_client.update_record(
                accounts_table, self.record_id, status_map
            )
            self.logger.info(
                f"✅ Airtable record {self.record_id} updated: {status_map}"
            )
        except Exception as e:
            self.logger.error(f"❌ Airtable update failed: {e}")


if __name__ == "__main__":
    module_logger.info("--- Main LoginBot Script Started ---")

    d, popup_handler, login_handler = None, None, None
    login_result = "not_run"
    account_data = None
    airtable_client = None  # Define here for access in finally block

    try:
        airtable_client = AirtableClient()
        # Call the new fetch_and_claim function
        account_data = airtable_client.fetch_and_claim_account_for_login()

        if not account_data:
            module_logger.error("❌ No unused accounts available to claim. Exiting.")
            sys.exit(1)

        # Data unpacking is now much simpler
        DEVICE_ID = account_data.get("device_id")
        PACKAGE_NAME = account_data.get("package_name")

        if not DEVICE_ID or not PACKAGE_NAME:
            module_logger.error(
                "❌ Account missing device_id or package_name. Exiting."
            )
            # Commented out for testing, but should be used to release the claimed account
            # if airtable_client:
            #     airtable_client.update_record(
            #         airtable_client.accounts_table,
            #         account_data["record_id"],
            #         {"Status": "Missing Device/Package Info"},
            #     )
            sys.exit(1)

        module_logger.info(
            f"✅ Processing: {account_data['instagram_username']} on {DEVICE_ID}"
        )

        d = u2.connect(DEVICE_ID)
        rotate_nordvpn_ip(d)

        popup_handler = PopupHandler(driver=d)
        # Context no longer needs base_id or table_id
        popup_handler.set_context(
            airtable_client, account_data["record_id"], PACKAGE_NAME, None, None
        )
        popup_handler.register_and_start_watchers()

        d.app_start(PACKAGE_NAME, stop=True)
        time.sleep(5)

        interactions = InstagramInteractions(device=d, app_package=PACKAGE_NAME)
        typer = StealthTyper(device=d)

        # Initializing the handler is now simpler
        login_handler = InstagramLoginHandler(
            device=d,
            interactions=interactions,
            stealth_typer=typer,
            popup_handler=popup_handler,
            airtable_client=airtable_client,
            record_id=account_data["record_id"],
        )

        # Call execute_login with only the required credentials
        # Email credentials are still fetched in case they are needed for 2FA
        login_result = login_handler.execute_login(
            username=account_data["instagram_username"],
            password=account_data["instagram_password"],
            email_address=account_data["email_address"],
            email_password=account_data["email_password"],
        )

        if login_result == "login_success":
            module_logger.info(
                "✅ Login successful. Handing over to Warmup Scroller..."
            )
            try:
                run_warmup_for_account(
                    username=account_data["instagram_username"],
                    device_id=DEVICE_ID,
                    package_name=PACKAGE_NAME,
                )
            except Exception as e:
                module_logger.error(f"💥 The warmup session failed: {e}", exc_info=True)
        else:
            module_logger.error(
                f"Login failed with status: {login_result.upper()}. Skipping warmup."
            )
            # This is the commented-out error handling you requested
            # if airtable_client and account_data:
            #     error_status = f"Login Failed - {login_result.upper()}"
            #     login_handler._update_airtable_status({"Status": error_status})

    except Exception as e:
        module_logger.critical(
            f"💥 A critical error occurred in the main block: {e}", exc_info=True
        )
        login_result = "critical_error"
        # And here for critical errors
        # if airtable_client and account_data:
        #     airtable_client.update_record(
        #         airtable_client.accounts_table,
        #         account_data["record_id"],
        #         {"Status": "Critical Error"},
        #     )

    finally:
        module_logger.info("--- Execution Finished ---")
        module_logger.info(f"Final Login Status: {login_result.upper()}")

        if popup_handler and login_result != "login_success":
            popup_handler.stop_watchers()

        module_logger.info("--- Script Complete ---")
