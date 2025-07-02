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
logger = setup_logger("AirtableWarmupAccountTest")


def run_warmup_fetch_test():
    """
    Initializes the AirtableClient and calls the fetch_account_for_warmup method.
    This tests the functionality for grabbing an account that needs to be warmed up.
    """
    logger.info("--- Starting Airtable 'Fetch Warmup Account' Test ---")

    try:
        # Step 1: Initialize the AirtableClient
        logger.info("🛠️  Initializing AirtableClient...")
        airtable_client = AirtableClient()
        logger.info("✅ AirtableClient initialized.")

        # Step 2: Call the fetch method for warmup accounts
        logger.info("🚀 Calling fetch_account_for_warmup...")
        account_data = airtable_client.fetch_account_for_warmup()
        logger.info("=" * 50)

        # Step 3: Print the result
        if account_data:
            logger.info("✅ Successfully fetched an account for warmup:")
            # Use pprint for a nicely formatted dictionary output
            pprint.pprint(account_data)
        else:
            logger.warning(
                "⚠️ No warmup account was fetched. This might be expected if none are available in the 'Warmup' view."
            )

        logger.info("=" * 50)

    except Exception as e:
        logger.critical(
            f"💥 A critical error occurred during the test: {e}",
            exc_info=True,
        )
    finally:
        logger.info("--- Test 'Fetch Warmup Account' Finished ---")


if __name__ == "__main__":
    run_warmup_fetch_test()
