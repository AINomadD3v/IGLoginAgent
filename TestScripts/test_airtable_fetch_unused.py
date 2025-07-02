import os
import pprint
import sys

# --- Path Setup ---
# This ensures the script can find the 'Shared' directory to import the AirtableClient.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Refactored Imports ---
from Shared.Utils.airtable_manager import AirtableClient
from Shared.Utils.logger_config import setup_logger

# --- Logger for the test script ---
logger = setup_logger("AirtableUnusedAccountTest")


def run_fetch_test():
    """
    Initializes the AirtableClient and calls the fetch_and_claim_account_for_login method.
    This tests the core functionality for grabbing a new account to process.
    """
    logger.info("--- Starting Airtable 'Fetch Unused Account' Test ---")

    try:
        # Step 1: Initialize the AirtableClient
        logger.info("🛠️  Initializing AirtableClient...")
        airtable_client = AirtableClient()
        logger.info("✅ AirtableClient initialized.")

        # Step 2: Call the fetch and claim method
        logger.info("🚀 Calling fetch_and_claim_account_for_login...")
        account_data = airtable_client.fetch_and_claim_account_for_login()
        logger.info("=" * 50)

        # Step 3: Print the result
        if account_data:
            logger.info("✅ Successfully fetched and claimed an account:")
            # Use pprint for a nicely formatted dictionary output
            pprint.pprint(account_data)
        else:
            logger.warning(
                "⚠️ No unused account was fetched or claimed. This might be expected if none are available."
            )

        logger.info("=" * 50)

    except Exception as e:
        logger.critical(
            f"💥 A critical error occurred during the test: {e}",
            exc_info=True,
        )
    finally:
        logger.info("--- Test 'Fetch Unused Account' Finished ---")


if __name__ == "__main__":
    run_fetch_test()
