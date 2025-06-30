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

# --- Refactored Imports ---
from get_imap_code import get_instagram_verification_code
from nord import main_flow as rotate_nordvpn_ip

from Shared.config import XpathConfig
from Shared.Data.airtable_manager import AirtableClient
from Shared.instagram_actions import InstagramInteractions
from Shared.popup_handler import PopupHandler
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
        base_id: Optional[str] = None,
        table_id: Optional[str] = None,
    ):
        self.d = device
        self.interactions = interactions
        self.popup_handler = popup_handler
        self.xpaths = XpathConfig(interactions.app_package)
        self.typer = stealth_typer
        self.logger = setup_logger(self.__class__.__name__)
        self.airtable_client = airtable_client
        self.record_id = record_id
        if airtable_client and base_id and table_id:
            airtable_client.base_id = base_id
            airtable_client.table_id = table_id
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

    def handle_2fa(self, email_address: str, email_password: str) -> str:
        """Handles the 2FA process by fetching a code via IMAP and submitting it."""
        self.logger.info("--- Starting 2FA Handling Process ---")

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
            self.logger.error(
                "❌ Failed to retrieve 2FA code via IMAP after all attempts."
            )
            return "2fa_failed"

        # If code was retrieved successfully
        self.logger.info(f"✅ Successfully retrieved 2FA code: {verification_code}")

        if not self.interactions.wait_for_element_appear(
            self.xpaths.two_fa_code_input, timeout=10
        ):
            self.logger.error("Could not find the 2FA code input field on screen.")
            return "2fa_failed"

        self.logger.info("Entering the 6-digit code...")
        self.interactions.click_by_xpath(self.xpaths.two_fa_code_input)
        time.sleep(0.5)
        self.d.clear_text()
        time.sleep(0.3)
        self.typer.type_text(verification_code)
        time.sleep(1)

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
            self.airtable_client.update_record_fields(self.record_id, status_map)
            self.logger.info(
                f"✅ Airtable record {self.record_id} updated: {status_map}"
            )
        except Exception as e:
            self.logger.error(f"❌ Airtable update failed: {e}")


# --- Main Execution Block ---
if __name__ == "__main__":
    module_logger.info("--- Main LoginBot Script Started ---")

    BASE_ID = os.getenv("IG_ARMY_BASE_ID")
    TABLE_ID = os.getenv("IG_ARMY_ACCS_TABLE_ID")

    d, popup_handler, login_handler = None, None, None
    login_result = "not_run"
    account_data = None

    try:
        airtable_client = AirtableClient()
        accounts_to_process = airtable_client.fetch_unused_accounts(max_records=1)
        if not accounts_to_process:
            module_logger.error("❌ No unused accounts found. Exiting.")
            sys.exit(1)
        account_data = accounts_to_process[0]

        DEVICE_ID = (account_data.get("device_id") or [""])[0].strip()
        PACKAGE_NAME = (account_data.get("package_name") or [""])[0].strip()
        if not DEVICE_ID or not PACKAGE_NAME:
            module_logger.error(
                "❌ Account missing device_id or package_name. Exiting."
            )
            sys.exit(1)

        module_logger.info(
            f"✅ Processing: {account_data['instagram_username']} on {DEVICE_ID}"
        )

        d = u2.connect(DEVICE_ID)
        rotate_nordvpn_ip(d)

        popup_handler = PopupHandler(driver=d)
        popup_handler.set_context(
            airtable_client, account_data["record_id"], PACKAGE_NAME, BASE_ID, TABLE_ID
        )
        popup_handler.register_and_start_watchers()

        d.app_start(PACKAGE_NAME, stop=True)
        time.sleep(5)

        interactions = InstagramInteractions(device=d, app_package=PACKAGE_NAME)
        typer = StealthTyper(device_id=d.serial)
        login_handler = InstagramLoginHandler(
            device=d,
            interactions=interactions,
            stealth_typer=typer,
            popup_handler=popup_handler,
            airtable_client=airtable_client,
            record_id=account_data["record_id"],
            base_id=BASE_ID,
            table_id=TABLE_ID,
        )

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

    except Exception as e:
        module_logger.critical(
            f"💥 A critical error occurred in the main block: {e}", exc_info=True
        )
        login_result = "critical_error"
    finally:
        module_logger.info("--- Execution Finished ---")
        module_logger.info(f"Final Login Status: {login_result.upper()}")

        if popup_handler and login_result != "login_success":
            popup_handler.stop_watchers()
            if d:
                d.app_stop(PACKAGE_NAME)

        module_logger.info("--- Script Complete ---")
