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
    def _scroll_feed_flick(self):
        """
        Performs a reliable, human-like "flick" gesture to scroll up the feed.
        This uses the simple device.swipe() command with randomized, fast parameters
        to be unambiguous and prevent misinterpretation as a tap.
        """
        self.logger.info("🌀 Performing scroll flick...")
        width, height = self.device.window_size()

        # Define a central, vertical corridor for the swipe to avoid edges.
        # Start in the bottom 70-85% of the screen.
        start_x = random.uniform(width * 0.4, width * 0.6)
        start_y = random.uniform(height * 0.70, height * 0.85)

        # End in the top 15-30% of the screen.
        # Add slight horizontal drift to the x-coordinate to make it less robotic.
        end_x = start_x + random.uniform(-width * 0.05, width * 0.05)
        end_y = random.uniform(height * 0.15, height * 0.30)

        # **CRITICAL FIX:** Use a short duration for a "flick", not a "drag".
        # A duration between 100ms and 250ms is fast enough to be registered
        # as a single, continuous swipe gesture by the Android UI.
        duration_s = random.uniform(0.1, 0.25)

        self.device.swipe(start_x, start_y, end_x, end_y, duration=duration_s)

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

    def get_current_view_state(self) -> str:
        """
        Determines the current view state of the app by checking for unique
        "landmark" elements in a specific order of priority.
        """
        self.logger.debug("Checking current view state...")

        # Priority 1: Check for the most specific overlays first (Comments, Peek View).
        if self.element_exists(self.xpath_config.reel_comment_input_field):
            self.logger.debug("State detected: IN_COMMENTS_VIEW")
            return "IN_COMMENTS_VIEW"

        if self.element_exists(self.xpath_config.peek_view_container):
            self.logger.debug("State detected: IN_PEEK_VIEW")
            return "IN_PEEK_VIEW"

        # Priority 2: Check for the full Reel viewer.
        if self.element_exists(self.xpath_config.reel_like_or_unlike_button):
            self.logger.debug("State detected: IN_REEL")
            return "IN_REEL"

        # Priority 3: Check if we're on the search results grid.
        if self.element_exists(self.xpath_config.explore_search_bar):
            self.logger.debug("State detected: ON_EXPLORE_GRID")
            return "ON_EXPLORE_GRID"

        # Priority 4: Check if we've returned to the main home feed.
        if self.element_exists(self.xpath_config.home_feed_identifier):
            self.logger.debug("State detected: ON_HOME_FEED")
            return "ON_HOME_FEED"

        # Fallback
        self.logger.warning("State detected: UNKNOWN")
        return "UNKNOWN"

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

    def scroll_explore_feed_proactive(self) -> bool:
        """
        The definitive, high-precision scrolling method.
        1.  **Proactively checks** if the UI is in the correct state.
        2.  **Blocks the scroll** if the state is wrong, preventing errors.
        3.  **Delegates** to the internal flick gesture if safe.
        Returns:
            bool: True if the scroll was performed, False if it was blocked.
        """
        current_state = self.get_current_view_state()
        if current_state != "ON_EXPLORE_GRID":
            self.logger.warning(
                f"⚠️ Scroll blocked: Attempted to scroll while in an invalid state ('{current_state}')."
            )
            return False
        try:
            # Call the new, reliable internal flick method.
            self._scroll_feed_flick()
            return True
        except Exception as e:
            self.logger.error(
                f"❌ An unexpected error occurred during the scroll gesture: {e}",
                exc_info=True,
            )
            return False

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
        self.scroll_explore_feed_proactive()
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

    def ensure_back_to_explore_grid(self) -> bool:
        """
        A robust navigation function that attempts to return to the explore grid
        from any known state (Reel, Comments, etc.). It will press 'back'
        until it verifies it has landed on the explore grid.
        This function is designed to be the definitive way to exit nested views.
        """
        self.logger.info("Ensuring navigation back to the explore grid...")

        # We will try up to 4 times to get back. This prevents an infinite loop.
        for attempt in range(4):
            # First, check what screen we're on
            current_state = self.get_current_view_state()

            # If we are on the correct screen, our job is done.
            if current_state == "ON_EXPLORE_GRID":
                self.logger.info("✅ Successfully navigated back to the explore grid.")
                return True

            # If we are not on the correct screen, log where we are and press back.
            self.logger.warning(
                f"Not on explore grid (currently: {current_state}). Pressing back... (Attempt {attempt + 1}/4)"
            )

            # Use the explicit back button if available, otherwise use the system back.
            # This is more robust than only using the system back press.
            if not self.click_by_xpath(self.xpath_config.nav_back_button, timeout=1):
                self.device.press("back")

            # Wait for the UI to settle after the action
            time.sleep(random.uniform(1.5, 2.2))

        # If the loop finishes without returning, it means we failed to get back.
        self.logger.error(
            "❌ Failed to navigate back to explore grid after multiple attempts."
        )
        return False
