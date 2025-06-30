# Shared/nord.py

import re
import time

from uiautomator2 import UiObjectNotFoundError


def extract_ip_number(content_desc: str) -> str:
    match = re.search(r"#(\d+)", content_desc)
    if match:
        return match.group(1)
    return ""


def main_flow(d):
    PACKAGE_NAME = "com.nordvpn.android"
    TOTAL_TIMEOUT = 300  # 5 minutes, as you requested

    print(f"🚀 Launching {PACKAGE_NAME}")
    d.app_start(PACKAGE_NAME, stop=True)
    time.sleep(3)

    xpath_connected = '//android.view.View[starts-with(@content-desc, "Connected to:")]'
    print("⏳ Waiting for initial VPN connection status view...")
    if not d.xpath(xpath_connected).wait(timeout=20):
        raise RuntimeError("❌ Could not find initial VPN connection status view.")

    status_view = d.xpath(xpath_connected)
    content_desc_before = status_view.info.get("contentDescription", "")
    if not content_desc_before.startswith("Connected to:"):
        raise RuntimeError(f"❌ Unexpected initial VPN status: '{content_desc_before}'")

    ip_before = extract_ip_number(content_desc_before)
    print(f"Current IP identifier before rotate: #{ip_before}")

    reconnect_btn = d(resourceId="connection_card_reconnect_button")
    if not reconnect_btn.wait(timeout=5):
        raise RuntimeError("❌ Reconnect button not found. UI may have changed.")

    reconnect_btn.click()
    print("🔄 Reconnect button clicked. Starting intelligent wait for IP rotation...")

    deadline = time.time() + TOTAL_TIMEOUT
    connection_successful = False

    while time.time() < deadline:
        if d.xpath(xpath_connected).exists:
            current_desc = d.xpath(xpath_connected).get().attrib.get("content-desc", "")
            current_ip = extract_ip_number(current_desc)
            if current_ip and current_ip != ip_before:
                print("\n✅ Connection successful and IP has rotated.")
                connection_successful = True
                break

        remaining_time = int(deadline - time.time())
        print(
            f"\r   Waiting for new connection... Time remaining: {remaining_time:03d}s",
            end="",
        )
        time.sleep(2)  # Poll every 2 seconds

    print()  # Move to the next line after the loop finishes

    if not connection_successful:
        raise RuntimeError(
            f"❌ VPN did not reconnect successfully within the {TOTAL_TIMEOUT}-second timeout."
        )

    content_desc_after = d.xpath(xpath_connected).get().attrib.get("content-desc", "")
    ip_after = extract_ip_number(content_desc_after)
    print(f"Final IP identifier after rotate: #{ip_after}")

    if ip_before == ip_after:
        raise RuntimeError(
            "❌ IP did NOT rotate: same number before and after reconnect."
        )
    else:
        print(f"✅ IP rotated successfully from #{ip_before} to #{ip_after}.")

    print(f"📴 Closing {PACKAGE_NAME} app...")
    d.app_stop(PACKAGE_NAME)
    print(f"✅ {PACKAGE_NAME} app closed.")
