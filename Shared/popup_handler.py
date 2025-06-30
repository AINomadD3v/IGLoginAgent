# Shared/popup_handler.py
# A central, reusable class for managing background UI watchers.

import threading

import uiautomator2 as u2

# --- Refactored Imports ---
# Import the specific config class from our new unified config file
from Shared.config import PopupConfig
from Shared.Utils.logger_config import setup_logger


class PopupHandler:
    """Manages background UI watchers to handle dynamic popups."""

    def __init__(self, driver: u2.Device):
        self.d = driver
        self.logger = setup_logger(self.__class__.__name__)
        self._watcher_thread = None
        self._watcher_stop_event = threading.Event()
        self.airtable_client = None
        self.record_id = None
        self.package_name = None
        self.base_id = None
        self.table_id = None
        self._suspension_handled = False

        # --- Use the new config class directly ---
        self.config = PopupConfig.WATCHERS

        # Initialize event flags that other classes can wait on.
        self.save_info_prompt_handled = threading.Event()
        self.notifications_prompt_handled = threading.Event()

        if self.config:
            self.logger.info("Successfully loaded popup watcher configurations.")
        else:
            self.logger.error(
                "Failed to load popup watcher configurations from config.py."
            )

    def set_context(self, airtable_client, record_id, package_name, base_id, table_id):
        """Sets the context for the handler, useful for callbacks that need external info."""
        self.logger.debug(
            f"Setting context: record_id={record_id}, package={package_name}"
        )
        self.airtable_client = airtable_client
        self.record_id = record_id
        self.package_name = package_name
        self.base_id = base_id
        self.table_id = table_id
        self._suspension_handled = False

        # Reset events to their non-signaled state for each new run.
        self.save_info_prompt_handled.clear()
        self.notifications_prompt_handled.clear()

    def register_and_start_watchers(self):
        """Registers all watchers from the config and starts the monitoring thread."""
        self.logger.info("Registering and starting popup watchers...")
        w = self.d.watcher
        w.reset()

        if not isinstance(self.config, list) or not self.config:
            self.logger.warning(
                "Popup config is invalid or empty. No watchers will start."
            )
            return

        for entry in self.config:
            name = entry.get("name")
            text_xpath = entry.get("text_xpath")
            button_xpath = entry.get("button_xpath")
            callback_name = entry.get("callback")

            if not name or not text_xpath:
                self.logger.warning(
                    f"Skipping invalid watcher entry in config: {entry}"
                )
                continue

            watcher = w(name).when(text_xpath)

            if callback_name:
                callback_method = getattr(self, callback_name, None)
                if callable(callback_method):
                    self.logger.info(
                        f"Registering watcher '{name}': WHEN '{text_xpath}' THEN CALL '{callback_name}'"
                    )
                    watcher.call(callback_method)
                else:
                    self.logger.error(
                        f"Callback method '{callback_name}' not found in PopupHandler for watcher '{name}'."
                    )
            elif button_xpath:
                self.logger.info(
                    f"Registering watcher '{name}': WHEN '{text_xpath}' THEN CLICK '{button_xpath}'"
                )
                # Use a lambda to capture the button_xpath for the click action
                watcher.call(
                    lambda selector, xpath=button_xpath: self.d.xpath(xpath).click()
                )
            else:
                self.logger.warning(
                    f"Watcher '{name}' has no valid action (no button_xpath or callback)."
                )

        if not w._watchers:
            self.logger.info(
                "No valid watchers were registered. Watcher thread will not start."
            )
            return

        self._watcher_stop_event.clear()
        self._watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._watcher_thread.start()
        self.logger.info(f"✅ {len(w._watchers)} watchers started in background.")

    def _watcher_loop(self, interval: float = 1.0):
        self.logger.debug("📡 Watcher thread running.")
        while not self._watcher_stop_event.is_set():
            try:
                self.d.watcher.run()
            except Exception as e:
                self.logger.error(f"💥 Watcher run error: {e}", exc_info=False)
            self._watcher_stop_event.wait(timeout=interval)
        self.logger.info("📡 Watcher thread stopped.")

    def stop_watchers(self):
        """Stops the watcher thread and resets the uiautomator2 watcher."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            self.logger.info("🛑 Signaling watcher loop to stop...")
            self._watcher_stop_event.set()
            self._watcher_thread.join(timeout=2.0)
            self._watcher_thread = None

        try:
            self.d.watcher.stop()
            self.d.watcher.remove()
            self.logger.info("Underlying uiautomator2 watchers stopped and removed.")
        except Exception as e:
            # It's common for this to raise an error if already stopped, so we check the message.
            if "watch already stopped" not in str(e).lower():
                self.logger.error(f"Error stopping uiautomator2 watcher: {e}")

    # --- Watcher Callback Methods ---

    def handle_save_login_info(self, selector):
        """Handles the 'Save login info?' popup and sets an event flag."""
        self.logger.info("WATCHER: Handling 'Save Login Info' popup.")
        try:
            # Find the button_xpath from the config entry that triggered this callback
            for entry in self.config:
                if entry.get("callback") == "handle_save_login_info":
                    button_xpath = entry.get("button_xpath")
                    if button_xpath:
                        self.logger.info(f"Watcher clicking button: '{button_xpath}'")
                        self.d.xpath(button_xpath).click(timeout=5)
                        self.logger.info(f"WATCHER: Clicked '{button_xpath}'.")
                        # Signal that the event was handled successfully
                        self.save_info_prompt_handled.set()
                        return
            self.logger.warning(
                "Watcher 'handle_save_login_info' triggered but no button_xpath found in config."
            )
        except Exception as e:
            self.logger.error(f"Error in handle_save_login_info watcher: {e}")
        finally:
            # CRITICAL: Always set the event, even on failure, to prevent the main thread from hanging.
            if not self.save_info_prompt_handled.is_set():
                self.save_info_prompt_handled.set()

    def handle_suspension(self, selector):
        """Handles the account suspension popup and updates Airtable."""
        self.logger.warning("🚫 WATCHER: Account suspended popup detected!")
        if self._suspension_handled:
            return
        if not self.record_id or not self.airtable_client:
            self.logger.error(
                "❌ Cannot handle suspension: Airtable context is missing."
            )
            return
        try:
            self.logger.info(f"Updating Airtable record {self.record_id} to 'Banned'.")
            self.airtable_client.update_record_fields(
                self.record_id, {"Status": "Banned"}
            )
            self._suspension_handled = True
            if self.package_name:
                self.logger.info(f"🛑 Stopping suspended app: {self.package_name}")
                self.d.app_stop(self.package_name)
        except Exception as e:
            self.logger.error(
                f"💥 Error in handle_suspension callback: {e}", exc_info=True
            )

    def photo_removed_callback(self, selector):
        """Placeholder callback for when a photo removed popup is detected."""
        self.logger.warning(
            "WATCHER: 'Photo Removed' popup detected. Taking no action."
        )

    def handle_generic_error_toast(self, selector):
        """Placeholder callback for a generic error toast message."""
        self.logger.warning(
            "WATCHER: 'Something went wrong' toast detected. Taking no action."
        )

    def handle_vpn_slow_connection(self, selector):
        """Placeholder callback for the NordVPN slow connection notification."""
        self.logger.warning(
            "WATCHER: NordVPN slow connection detected. Taking no action."
        )
