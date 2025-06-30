# Shared/instagram_actions.py

import math  # Added for swipe calculations
import os
import random
import subprocess
import sys
import time
from typing import Optional

import uiautomator2 as u2

# --- Path setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Refactored Imports ---
from Shared.config import XpathConfig  # Use new unified config
from Shared.Utils.logger_config import setup_logger


class InstagramInteractions:
    """
    A streamlined class for handling UI interactions, now with integrated gesture controls.
    """

    def __init__(self, device: u2.Device, app_package: str, airtable_manager=None):
        self.device = device
        self.app_package = app_package.strip()
        # Use the new unified XpathConfig
        self.xpath_config = XpathConfig(self.app_package)
        self.airtable_manager = airtable_manager
        self.logger = setup_logger(self.__class__.__name__)
        # The SwipeHelper is no longer needed as its methods are now part of this class.

    # --- App Management ---

    def close_app(self) -> bool:
        """Stops the app cleanly, with a fallback to ADB force-stop."""
        pkg = self.app_package
        self.logger.debug(f"🛑 Attempting to stop app: {pkg}")
        try:
            self.device.app_stop(pkg)
            time.sleep(1)
            # Verify app is stopped
            if self.device.app_current().get("package") == pkg:
                self.logger.warning(
                    f"uiautomator2 app_stop failed for {pkg}, falling back to ADB."
                )
                try:
                    subprocess.run(
                        [
                            "adb",
                            "-s",
                            self.device.serial,
                            "shell",
                            "am",
                            "force-stop",
                            pkg,
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.logger.debug(f"✅ App {pkg} stopped via ADB force-stop.")
                except Exception as adb_e:
                    self.logger.error(
                        f"❌ ADB force-stop command failed for {pkg}: {adb_e}"
                    )
                    return False
            else:
                self.logger.debug(
                    f"✅ App {pkg} stopped successfully via uiautomator2."
                )
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to stop app {pkg}: {e}", exc_info=True)
            return False

    # --- Element Interaction Primitives ---

    def wait_for_element_appear(self, xpath: str, timeout: int = 10) -> bool:
        """Waits for an element to appear on the screen."""
        self.logger.debug(f"Waiting up to {timeout}s for element to appear: {xpath}")
        return self.device.xpath(xpath).wait(timeout=timeout)

    def wait_for_element_vanish(self, xpath: str, timeout: int = 10) -> bool:
        """Waits for an element to disappear from the screen."""
        self.logger.debug(f"Waiting up to {timeout}s for element to vanish: {xpath}")
        return self.device.xpath(xpath).wait_gone(timeout=timeout)

    def element_exists(self, xpath: str) -> bool:
        """Checks if an element exists without a long wait."""
        return self.device.xpath(xpath).exists

    def click_by_xpath(self, xpath: str, timeout: int = 10) -> bool:
        """Waits for an element and clicks it."""
        self.logger.debug(f"Attempting to click element: {xpath}")
        try:
            return self.device.xpath(xpath).click_exists(timeout=timeout)
        except Exception as e:
            self.logger.error(f"Error clicking element '{xpath}': {e}", exc_info=True)
            return False

    def get_element_attribute(
        self, xpath: str, attribute: str, timeout: int = 5
    ) -> Optional[str]:
        """Gets a specific attribute value of an element."""
        self.logger.debug(f"Getting attribute '{attribute}' from: {xpath}")
        el = self.device.xpath(xpath).get(timeout=timeout)
        if el:
            return el.info.get(attribute)
        return None

    # --- Start: Merged SwipeHelper Methods ---

    def _curved_path(self, start, end, steps, max_arc_x, jitter_y):
        """Generates a list of points for a curved, human-like swipe."""
        x1, y1 = start
        x2, y2 = end
        path = []

        for i in range(steps + 1):
            t = i / steps
            arc_offset = math.sin(t * math.pi) * random.uniform(-max_arc_x, max_arc_x)
            jitter = random.uniform(-jitter_y, jitter_y)
            x = x1 + (x2 - x1) * t + arc_offset
            y = y1 + (y2 - y1) * t + jitter
            path.append((int(x), int(y)))
        return path

    def _curved_swipe(self, start, end, duration_ms, intensity="medium"):
        """Performs a swipe along a curved path."""
        self.logger.debug(
            f"🌀 Executing curved swipe: {start} → {end} over {duration_ms}ms (style: {intensity})"
        )

        intensity_map = {
            "gentle": {"arc": 15, "jitter": 2, "steps": 15},
            "medium": {"arc": 30, "jitter": 4, "steps": 20},
            "chaotic": {"arc": 60, "jitter": 8, "steps": 25},
        }
        params = intensity_map.get(intensity, intensity_map["medium"])

        path = self._curved_path(
            start, end, params["steps"], params["arc"], params["jitter"]
        )
        self.device.swipe_points(path, duration_ms / 1000.0)

    def scroll_up_humanlike(self, intensity="medium"):
        """Performs a human-like scroll up the screen (i.e., a downward swipe)."""
        self.logger.debug("Performing human-like scroll up...")
        width, height = self.device.window_size()
        x = random.randint(int(width * 0.45), int(width * 0.55))
        y_start = random.randint(int(height * 0.65), int(height * 0.75))
        y_end = random.randint(int(height * 0.25), int(height * 0.35))
        duration = random.randint(300, 600)

        self._curved_swipe((x, y_start), (x, y_end), duration, intensity)

    def _tap_random_in_bounds(
        self, bounds: dict, label: str = "element", offset: int = 8
    ) -> bool:
        """Internal helper to tap randomly within a given bounds dictionary."""
        try:
            left, top, right, bottom = (
                bounds["left"],
                bounds["top"],
                bounds["right"],
                bounds["bottom"],
            )
            # If the element is too small, just click the center
            if right <= left + (2 * offset) or bottom <= top + (2 * offset):
                x, y = (left + right) // 2, (top + bottom) // 2
            else:
                x = random.randint(left + offset, right - offset)
                y = random.randint(top + offset, bottom - offset)

            self.logger.info(f"👆 Tapping {label} randomly at ({x}, {y})")
            self.device.click(x, y)
            return True
        except Exception as e:
            self.logger.error(f"Error during random tap on {label}: {e}", exc_info=True)
            return False

    def tap_random_within_element(
        self, xpath: str, label: str = "element", timeout: int = 5
    ) -> bool:
        """Finds an element by XPath and taps at a random point within its bounds."""
        self.logger.debug(f"Attempting random tap within {label}: {xpath}")
        el = self.device.xpath(xpath).get(timeout=timeout)
        if not el:
            self.logger.warning(f"{label} not found for random tap: {xpath}")
            return False

        bounds = el.info.get("bounds")
        if not bounds:
            self.logger.warning(
                f"Could not get bounds for {label}, using default click."
            )
            return self.click_by_xpath(xpath, timeout=1)

        return self._tap_random_in_bounds(bounds, label)

    # --- End: Merged SwipeHelper Methods ---

    # --- Scroller-Specific Actions ---

    def perform_light_interaction(self):
        """Performs a minor, human-like interaction on a Reel to seem more active."""
        action = random.choice(["tap_center", "mini_scrub"])
        self.logger.info(f"Performing light interaction: {action}")
        try:
            width, height = self.device.window_size()
            if action == "tap_center":
                x = random.randint(int(width * 0.4), int(width * 0.6))
                y = random.randint(int(height * 0.4), int(height * 0.6))
                self.device.click(x, y)
            elif action == "mini_scrub":
                x_start = random.randint(int(width * 0.3), int(width * 0.5))
                y = random.randint(int(height * 0.6), int(height * 0.8))
                offset = random.randint(40, 90) * random.choice([-1, 1])
                self.device.swipe(x_start, y, x_start + offset, y, duration=0.1)
        except Exception as e:
            self.logger.error(
                f"Error during light interaction '{action}': {e}", exc_info=True
            )

    def like_current_post_or_reel(self) -> bool:
        """Likes the currently viewed post or reel by tapping the like button."""
        self.logger.info("Attempting to like current post/reel...")
        like_xpath = self.xpath_config.reel_likes_button

        # Tap the like button area
        if not self.tap_random_within_element(
            like_xpath, label="Like Button", timeout=3
        ):
            self.logger.warning(f"Like button not found via XPath: {like_xpath}")
            return False

        time.sleep(random.uniform(0.8, 1.3))

        # Verify the button state changed to 'Unlike'
        if self.element_exists(
            self.xpath_config.reel_like_or_unlike_button.replace('"Like"', '"Unlike"')
        ):
            self.logger.info("❤️ Like successful and verified.")
            return True
        else:
            self.logger.warning(
                "⚠️ Like button clicked, but state did not change to 'Unlike'."
            )
            return False

    def simulate_open_close_comments(self) -> bool:
        """Simulates opening the comment section, scrolling slightly, and closing it."""
        self.logger.info("💬 Simulating opening/closing comments...")
        comment_xpath = self.xpath_config.reel_comment_button

        if not self.tap_random_within_element(
            comment_xpath, label="Comment Button", timeout=5
        ):
            self.logger.warning("Failed to tap comment button.")
            return False

        time.sleep(random.uniform(1.5, 2.5))

        # Scroll up slightly in the comments
        self.scroll_up_humanlike(intensity="gentle")
        time.sleep(random.uniform(1.0, 2.0))

        self.logger.debug("Pressing back to close comments.")
        self.device.press("back")
        time.sleep(random.uniform(0.8, 1.2))

        if self.element_exists(comment_xpath):
            self.logger.info("✅ Comment simulation complete.")
            return True
        else:
            self.logger.warning("⚠️ Comment button not visible after closing.")
            # Attempt one more back press as a recovery measure
            self.device.press("back")
            return False

    def navigate_back_from_reel(self, verify_xpath: Optional[str] = None) -> bool:
        """Navigates back from a full-screen reel view."""
        self.logger.info("Attempting to navigate back from reel view...")

        # Prefer the explicit back button if it exists, otherwise use system back
        if self.click_by_xpath(self.xpath_config.nav_back_button, timeout=1):
            self.logger.info("Clicked explicit 'Back' button.")
        else:
            self.logger.info(
                "No explicit 'Back' button found, using system back press."
            )
            self.device.press("back")

        time.sleep(random.uniform(1.0, 1.5))

        if verify_xpath:
            if self.wait_for_element_vanish(verify_xpath, timeout=5):
                self.logger.info("✅ Exited reel view (verified).")
                return True
            else:
                self.logger.error("❌ Failed to verify exit from reel view.")
                return False

        return True  # Assume success if no verification XPath is provided
