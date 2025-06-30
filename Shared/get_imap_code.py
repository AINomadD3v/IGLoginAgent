# Shared.get_imap_code.py

import email
import imaplib
import re
from typing import Optional

from bs4 import BeautifulSoup


def extract_body(msg) -> str:
    """Extracts email body as text (HTML or plain)."""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))

            if "attachment" in cdispo:
                continue

            payload = part.get_payload(decode=True)
            if ctype == "text/plain" and payload:
                return payload.decode(errors="replace")
            elif ctype == "text/html" and payload:
                html = payload.decode(errors="replace")
                return BeautifulSoup(html, "html.parser").get_text(separator=" ")
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            try:
                html = payload.decode()
                return BeautifulSoup(html, "html.parser").get_text(separator=" ")
            except UnicodeDecodeError:
                return payload.decode(errors="replace")
        return ""


def get_instagram_verification_code(
    email_address: str,
    password: str,
    imap_host: str = "imap.poczta.onet.pl",
    imap_port: int = 993,
    timeout: int = 30,
    debug: bool = False,
) -> Optional[str]:
    """
    Fetches the latest Instagram verification code by reliably searching all mail
    in both INBOX and Spam folders, and filtering within Python.
    """
    CODE_REGEX = r"code to confirm your identity[:\s]*([0-9]{6})"
    imap = None

    folders_to_check = ["INBOX", "Spam"]

    try:
        if debug:
            print(f"Connecting to {imap_host}...")
        imap = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=timeout)

        if debug:
            print(f"Logging in as {email_address}...")
        imap.login(email_address, password)

        for folder in folders_to_check:
            if debug:
                print(f"\n--- Selecting folder: {folder} ---")

            try:
                status, _ = imap.select(
                    f'"{folder}"', readonly=True
                )  # Readonly is safer
                if status != "OK":
                    if debug:
                        print(f"Could not select folder '{folder}'. It may not exist.")
                    continue
            except Exception as e:
                if debug:
                    print(f"Error selecting folder '{folder}': {e}")
                continue

            if debug:
                print("Searching for ALL messages in this folder...")
            status, data = imap.search(None, "ALL")
            if status != "OK" or not data[0]:
                if debug:
                    print("No messages found in this folder.")
                continue

            msg_nums = data[0].split()[::-1]

            # Check the most recent 20 emails
            for num in msg_nums[:20]:
                status, msg_data = imap.fetch(num, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(msg_data[0][1])

                # --- MODIFIED: Filtering is now done in Python for reliability ---
                subject = str(
                    email.header.make_header(email.header.decode_header(msg["Subject"]))
                )
                sender = str(
                    email.header.make_header(email.header.decode_header(msg["From"]))
                )

                if debug:
                    print(f"Checking email from '{sender}' with subject '{subject}'")

                # The actual check
                is_target_email = (
                    "verify your account" in subject.lower()
                    and "security@mail.instagram.com" in sender.lower()
                )

                if not is_target_email:
                    continue  # Skip to the next email if it doesn't match

                # If we get here, it's the right email. Now extract the code.
                if debug:
                    print("Found a matching email. Extracting body...")
                body = extract_body(msg)

                if not body:
                    if debug:
                        print("[Body is empty, skipping]")
                    continue

                match = re.search(CODE_REGEX, body, re.IGNORECASE)
                if match:
                    found_code = match.group(1)
                    if debug:
                        print(f"✅✅✅ FOUND CODE: {found_code} in folder '{folder}'")
                    return found_code

    except imaplib.IMAP4.error as e:
        if debug:
            print(f"IMAP Error (check credentials or connection): {e}")
    except Exception as e:
        if debug:
            print(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        if imap:
            if imap.state == "SELECTED":
                imap.close()
            imap.logout()
            if debug:
                print("\nIMAP connection closed.")

    if debug:
        print("\n❌ No Instagram verification code found after all attempts.")
    return None


if __name__ == "__main__":
    print("--- Running Standalone IMAP Test ---")
    test_email = "elianestrada@onet.pl"
    test_password = "khan567996"
    print(
        "NOTE: This test will search for any matching Instagram email, read or unread."
    )

    code = get_instagram_verification_code(test_email, test_password, debug=True)

    print("\n--- TEST RESULT ---")
    if code:
        print(f"✅ Verification code is: {code}")
    else:
        print("❌ No verification code found.")
