# Warmup/scroller.py

import hashlib
import os
import random
import sys
import time
from typing import Optional

import uiautomator2 as u2

# --- Path Setup ---
# Ensures the script can find the 'Shared' and other project directories.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Refactored Imports ---
# Import directly from our new, centralized components.
from Shared.config import ScrollerConfig
from Shared.instagram_actions import InstagramInteractions
from Shared.popup_handler import PopupHandler
from Shared.Utils.logger_config import setup_logger
from Shared.Utils.stealth_typing import StealthTyper

# --- Logger and Configuration Setup ---
logger = setup_logger(name="Scroller")


# --- Utility Functions ---
def random_delay(label: str):
    """Sleeps for a random duration based on the label from ScrollerConfig."""
    # Access delays directly from our new config class
    lo, hi = ScrollerConfig.DELAYS.get(label, ScrollerConfig.DELAYS["default"])
    try:
        lo_f, hi_f = float(lo), float(hi)
        if hi_f < lo_f:
            hi_f, lo_f = lo_f, hi_f  # Swap if order is wrong
        t = random.uniform(lo_f, hi_f)
        logger.debug(f"Sleeping {t:.2f}s ({label})")
        time.sleep(t)
    except (TypeError, ValueError) as e:
        logger.error(
            f"Invalid delay config for '{label}': {lo}, {hi}. Using default 1s. Error: {e}"
        )
        time.sleep(1.0)


# --- Core Logic Functions ---


def extract_search_page_reels(insta_actions: InstagramInteractions) -> list[dict]:
    """
    Extracts reel information from the search page by directly finding elements
    that are explicitly identified as Reels based on their content description.
    """
    reels = []
    seen_this_screen = set()
    device = insta_actions.device

    try:
        # This is the reliable, direct XPath that correctly identifies only Reels.
        reel_elements_xpath = (
            "//android.widget.ImageView[contains(@content-desc, 'Reel by')]"
        )
        reel_elements = device.xpath(reel_elements_xpath).all()

        logger.info(f"Found {len(reel_elements)} potential Reels on screen.")

        for reel_el in reel_elements:
            try:
                iv_info = reel_el.info
                desc = iv_info.get("contentDescription", "").strip()
                bounds = iv_info.get("bounds")

                if not desc or not bounds:
                    continue

                if desc in seen_this_screen:
                    continue
                seen_this_screen.add(desc)

                key = hashlib.sha1(desc.encode("utf-8")).hexdigest()
                try:
                    username = desc.split("by", 1)[1].split("at", 1)[0].strip()
                except IndexError:
                    logger.warning(f"Could not parse username from desc: {desc}")
                    username = "unknown"

                bounds_str = f"[{bounds.get('left', 0)},{bounds.get('top', 0)}][{bounds.get('right', 0)},{bounds.get('bottom', 0)}]"
                post = {
                    "id": key,
                    "short_id": key[:7],
                    "username": username,
                    "desc": desc,
                    "bounds": bounds_str,
                }
                logger.info(f"[{post['short_id']}] ✅ Extracted Reel | @{username}")
                reels.append(post)
            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to parse a specific reel element: {e}", exc_info=False
                )
                continue
    except Exception as outer_e:
        logger.error(
            f"💥 Error extracting reels from search page: {outer_e}", exc_info=True
        )

    return reels


def process_reel(
    insta_actions: InstagramInteractions, reel_post: dict
) -> Optional[dict]:
    """Processes a single reel: watches, interacts, and extracts data."""
    # Get config values directly from the ScrollerConfig class
    full_watch_time = random.uniform(*ScrollerConfig.WATCH_TIME_RANGE)
    like_probability = ScrollerConfig.LIKE_PROBABILITY
    comment_probability = ScrollerConfig.COMMENT_PROBABILITY

    like_delay = random.uniform(1.2, max(1.3, full_watch_time - 0.5))
    interaction_times = sorted(
        random.sample(
            [random.uniform(1.0, max(1.1, full_watch_time - 0.2)) for _ in range(3)],
            k=2,
        )
    )

    logger.info(
        f"⏱️ Watching reel [{reel_post.get('short_id', 'N/A')}] for {full_watch_time:.2f}s"
    )
    start_time = time.time()

    # --- Tap the reel to open it ---
    reel_tap_xpath = insta_actions.xpath_config.search_reel_imageview_template(
        reel_post["desc"]
    )
    if not insta_actions.click_by_xpath(reel_tap_xpath, timeout=5):
        logger.error(f"❌ Failed to tap/open reel [{reel_post.get('short_id', 'N/A')}]")
        return None

    random_delay("after_post_tap")

    # --- Interaction Loop ---
    end_time = start_time + full_watch_time
    liked = False
    commented = False
    should_comment = random.random() < comment_probability
    next_interaction_time = interaction_times.pop(0) if interaction_times else None

    while time.time() < end_time:
        elapsed = time.time() - start_time

        if next_interaction_time and elapsed >= next_interaction_time:
            insta_actions.perform_light_interaction()
            next_interaction_time = (
                interaction_times.pop(0) if interaction_times else None
            )

        if not liked and elapsed >= like_delay:
            if random.random() < like_probability:
                if insta_actions.like_current_post_or_reel():
                    random_delay("after_like")
                    liked = True
            # Set delay to infinity to ensure we only try once
            like_delay = float("inf")

        if not commented and should_comment and elapsed >= full_watch_time * 0.6:
            if insta_actions.simulate_open_close_comments():
                random_delay("after_comment")
                commented = True
            should_comment = False

        time.sleep(0.2)

    # --- Exit Reel View ---
    verify_xpath = insta_actions.xpath_config.reel_like_or_unlike_button
    insta_actions.ensure_back_to_explore_grid()
    random_delay("back_delay")

    # This functionality to return data is preserved, even if not used in the main loop
    return {"liked": liked, "commented": commented}


def perform_keyword_search(insta_actions: InstagramInteractions, keyword: str) -> bool:
    """Performs a keyword search on the Explore page."""
    logger.info(f"🔍 Performing keyword search: {keyword}")
    xpath_config = insta_actions.xpath_config
    typer = StealthTyper(device=insta_actions.device)

    try:
        search_xpath = xpath_config.explore_search_bar
        if not insta_actions.click_by_xpath(search_xpath, timeout=10):
            logger.error("❌ Failed to click search bar.")
            return False

        logger.info("✅ Search bar tapped.")
        time.sleep(random.uniform(0.8, 1.2))

        typer.type_text(keyword)
        time.sleep(random.uniform(0.3, 0.6))
        typer.press_enter()
        logger.info("⏎ Enter pressed to start search.")
        time.sleep(random.uniform(2.5, 4.0))

        logger.info("↕️ Scrolling down slightly to reveal posts...")
        insta_actions.scroll_explore_feed_proactive()
        time.sleep(random.uniform(1.0, 1.5))

        if not insta_actions.wait_for_element_appear(
            xpath_config.search_results_container, timeout=10
        ):
            logger.error("❌ Search results container not found after search.")
            return False

        logger.info("✅ Search results loaded.")
        return True

    except Exception as e:
        logger.error(f"❌ Failed during keyword search flow: {e}", exc_info=True)
        return False


def run_warmup_session(insta_actions: InstagramInteractions):
    """Runs the main warmup/scrolling session logic with robust state management."""
    seen_hashes = set()
    all_reels_processed_info = []

    # --- Navigate to Explore ---
    logger.info("📍 Navigating to Explore page...")
    if not insta_actions.click_by_xpath(
        insta_actions.xpath_config.nav_explore_tab, timeout=10
    ):
        logger.error("🚫 Failed to find or click Explore tab. Exiting warmup.")
        return

    if not insta_actions.wait_for_element_appear(
        insta_actions.xpath_config.explore_search_bar, timeout=10
    ):
        logger.error(
            "🚫 Explore page failed to load (search bar not found). Exiting warmup."
        )
        return
    logger.info("✅ Explore page loaded successfully.")

    # --- Perform Keyword Search ---
    keyword = random.choice(ScrollerConfig.KEYWORDS)
    logger.info(f"🎯 Chosen keyword for search: '{keyword}'")
    if not perform_keyword_search(insta_actions, keyword):
        logger.error("🚫 Keyword search failed. Exiting warmup.")
        return

    # --- Main Scrolling Loop ---
    start_time = time.time()
    actions_since_idle = 0
    idle_min, idle_max = ScrollerConfig.IDLE_AFTER_ACTIONS_RANGE
    next_idle_at = random.randint(idle_min, idle_max)

    for i in range(ScrollerConfig.MAX_SCROLLS):
        if time.time() - start_time > ScrollerConfig.MAX_RUNTIME_SECONDS:
            logger.info(
                f"⏰ Runtime limit ({ScrollerConfig.MAX_RUNTIME_SECONDS}s) exceeded."
            )
            break

        logger.info(f"--- Scroll iteration {i + 1}/{ScrollerConfig.MAX_SCROLLS} ---")

        # --- STATE CHECK & RECOVERY BLOCK ---
        current_state = insta_actions.get_current_view_state()

        if current_state == "IN_PEEK_VIEW":
            logger.warning(
                "🫣 State check: Caught in a 'Peek View'. Pressing back to escape."
            )
            insta_actions.device.press("back")
            random_delay("back_delay")
            continue

        elif current_state == "IN_REEL":
            logger.warning(
                "🚨 State check: Detected we are inside a reel unexpectedly. Navigating back."
            )
            insta_actions.ensure_back_to_explore_grid()
            random_delay("back_delay")
            continue

        elif current_state == "ON_HOME_FEED":
            logger.warning(
                "↩️ State check: On Home Feed. Navigating back to Explore page."
            )
            insta_actions.click_by_xpath(insta_actions.xpath_config.nav_explore_tab)
            random_delay("after_post_tap")
            continue

        elif current_state == "UNKNOWN":
            logger.error(
                "🚫 State check: Screen is in an unknown state. Attempting generic back press to recover."
            )
            insta_actions.device.press("back")
            random_delay("back_delay")
            continue
        # --- END OF STATE CHECK ---

        # If we passed the checks, we are ON_EXPLORE_GRID, so it's safe to proceed.
        new_reels = [
            r
            for r in extract_search_page_reels(insta_actions)
            if r["id"] not in seen_hashes
        ]

        if not new_reels:
            logger.info("🔁 No new reels found, scrolling up...")
            insta_actions.scroll_explore_feed_proactive()
            random_delay("between_scrolls")
            continue

        logger.info(f"Found {len(new_reels)} new reels on screen.")
        num_to_process = max(
            1, int(len(new_reels) * ScrollerConfig.PERCENT_REELS_TO_WATCH)
        )
        reels_to_process = random.sample(new_reels, num_to_process)
        logger.info(f"Processing {len(reels_to_process)} of them.")

        for reel_data in reels_to_process:
            if time.time() - start_time > ScrollerConfig.MAX_RUNTIME_SECONDS:
                break

            logger.info(
                f"🎬 Processing reel [{reel_data['short_id']}] by @{reel_data['username']}"
            )
            result = process_reel(insta_actions=insta_actions, reel_post=reel_data)
            seen_hashes.add(reel_data["id"])
            if result:
                all_reels_processed_info.append(result)

            actions_since_idle += 1
            if actions_since_idle >= next_idle_at:
                idle_time = random.uniform(*ScrollerConfig.IDLE_DURATION_RANGE)
                logger.info(f"😴 Idle break for {idle_time:.2f}s")
                time.sleep(idle_time)
                actions_since_idle = 0
                next_idle_at = random.randint(idle_min, idle_max)

        random_delay("before_scroll")
        insta_actions.scroll_explore_feed_proactive()
        random_delay("between_scrolls")

    # --- Session End Summary ---
    duration = time.time() - start_time
    logger.info(f"🕒 Warmup session finished. Runtime: {duration:.2f}s")
    total_liked = sum(1 for r in all_reels_processed_info if r.get("liked"))
    total_comments = sum(1 for r in all_reels_processed_info if r.get("commented"))
    logger.info("📊 Session Summary:")
    logger.info(f"  - Total Reels Processed: {len(all_reels_processed_info)}")
    logger.info(f"  - Total Reels Liked:     {total_liked}")
    logger.info(f"  - Comment Interactions:  {total_comments}")


def run_warmup_for_account(username: str, device_id: str, package_name: str):
    """Main entry point for a single account's warmup session."""
    logger.info(
        f"--- Preparing warmup for @{username} on {device_id} ({package_name}) ---"
    )
    device, popup_handler, insta_actions = None, None, None
    try:
        logger.info(f"🔌 Connecting to device: {device_id}")
        device = u2.connect(device_id)
        logger.info(f"✅ Connected to {device.serial}")

        insta_actions = InstagramInteractions(device, package_name)
        logger.info(
            "Assuming login is complete. Starting popup handler for scroller session."
        )

        popup_handler = PopupHandler(device)
        popup_handler.set_context(None, None, package_name, None, None)
        popup_handler.register_and_start_watchers()

        run_warmup_session(insta_actions=insta_actions)

    except ConnectionError as conn_err:
        logger.error(f"❌ Connection Error for @{username} on {device_id}: {conn_err}")
    except Exception as e:
        logger.error(
            f"❌ Unhandled exception during warmup for @{username}: {e}", exc_info=True
        )
    finally:
        logger.info(f"--- Cleaning up session for @{username} ---")
        if popup_handler:
            popup_handler.stop_watchers()
        if insta_actions:
            insta_actions.close_app()
        logger.info(f"--- Finished processing for @{username} ---")
