import os
from typing import Any, Dict, Optional, Sequence, cast

from dotenv import load_dotenv
from pyairtable import Api, Table
from requests.exceptions import HTTPError

from Shared.Utils.logger_config import setup_logger

logger = setup_logger(__name__)

# --- Load dotenv from project root ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
dotenv_path = os.path.join(project_root, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    raise RuntimeError(f"🚨 .env file not found at expected location: {dotenv_path}")


class AirtableClient:
    """
    A streamlined Airtable client with specialized methods for fetching login and warmup
    accounts, designed to be safe for concurrent use.
    """

    def __init__(self):
        """Initializes the Airtable client and loads configuration from environment variables."""
        api_key = os.getenv("AIRTABLE_API_KEY")
        if not api_key:
            raise ValueError("Missing required environment variable: AIRTABLE_API_KEY")

        base_id = os.getenv("IG_ARMY_BASE_ID")
        if not base_id:
            raise ValueError("Missing required environment variable: IG_ARMY_BASE_ID")

        accounts_table_id = os.getenv("IG_ARMY_ACCS_TABLE_ID")
        if not accounts_table_id:
            raise ValueError(
                "Missing required environment variable: IG_ARMY_ACCS_TABLE_ID"
            )

        self.api_key = api_key
        self.base_id = base_id
        self.accounts_table_id = accounts_table_id
        self.warmup_table_id = os.getenv("IG_ARMY_WARMUP_ACCOUNTS_TABLE_ID")

        self.api = Api(self.api_key)
        self.accounts_table = self.api.table(self.base_id, self.accounts_table_id)
        self.warmup_table = (
            self.api.table(self.base_id, self.warmup_table_id)
            if self.warmup_table_id
            else None
        )
        logger.info("AirtableClient initialized successfully.")

    def _flatten_field(self, value: Any) -> Optional[str]:
        """
        Takes a value from Airtable. If it's a list, returns the first element.
        Strips whitespace from strings. Returns None if the value is empty.
        """
        if isinstance(value, list):
            if not value:
                return None
            value = value[0]

        if isinstance(value, str):
            return value.strip()

        if value is not None:
            return str(value)

        return None

    def _process_login_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validates and processes a record for the Login Bot.
        Requires Account, Password, Package Name, and Device ID.
        """
        record_id = record.get("id")
        if not isinstance(record_id, str):
            logger.error(f"Record is missing a valid string ID. Record data: {record}")
            return None

        fields = record.get("fields", {})
        account_data = {
            "record_id": record_id,
            "instagram_username": self._flatten_field(fields.get("Account")),
            "instagram_password": self._flatten_field(fields.get("Password")),
            "package_name": self._flatten_field(fields.get("Package Name")),
            "device_id": self._flatten_field(fields.get("Device ID")),
            "email_address": self._flatten_field(fields.get("Email")),
            "email_password": self._flatten_field(fields.get("Email Password")),
        }

        required_fields = [
            "instagram_username",
            "instagram_password",
            "package_name",
            "device_id",
        ]
        if not all(account_data.get(field) for field in required_fields):
            logger.warning(
                f"Skipping login record {record_id} due to missing credentials."
            )
            self.update_record(
                self.accounts_table, record_id, {"Status": "Missing Credentials"}
            )
            return None

        return account_data

    def _process_warmup_record(
        self, record: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Validates and processes a record for the standalone Warmup Bot.
        Requires Username, Package Name, and Device ID from the Warmup Accounts table.
        """
        record_id = record.get("id")
        if not isinstance(record_id, str):
            logger.error(f"Record is missing a valid string ID. Record data: {record}")
            return None

        fields = record.get("fields", {})
        account_data = {
            "record_id": record_id,
            "instagram_username": self._flatten_field(fields.get("Username")),
            "package_name": self._flatten_field(fields.get("Package Name")),
            "device_id": self._flatten_field(fields.get("Device ID")),
        }

        required_fields = ["instagram_username", "package_name", "device_id"]
        if not all(account_data.get(field) for field in required_fields):
            logger.warning(
                f"Skipping warmup record {record_id} due to missing required fields (Username, Package Name, Device ID)."
            )
            return None

        return account_data

    def fetch_and_claim_account_for_device(
        self, device_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Finds a ready-to-use account for a specific device, atomically claims it
        by updating its status, and returns the processed account data.
        """
        logger.info(
            f"Attempting to fetch and claim an account for device '{device_id}'..."
        )

        # This formula now ALSO includes 'Assigned' as a valid status.
        ready_status_formula = "OR({Status} = 'Assigned', {Status} = 'Ready for Login', {Status} = 'Unused')"
        formula = f"AND({{Device ID}} = '{device_id}', {ready_status_formula})"

        # The status to set immediately after claiming the account.
        claim_status = "Login In Progress"

        try:
            potential_accounts: Sequence[Dict[str, Any]] = self.accounts_table.all(
                formula=formula,
                max_records=5,
            )

            if not potential_accounts:
                logger.warning(
                    f"No available accounts found for device '{device_id}' with a ready status."
                )
                return None

            for record in potential_accounts:
                record_id = record.get("id")
                if not isinstance(record_id, str):
                    continue  # Skip invalid records

                try:
                    self.update_record(
                        self.accounts_table, record_id, {"Status": claim_status}
                    )
                    logger.info(
                        f"✅ Successfully claimed record {record_id} for device {device_id}."
                    )
                    # Use your existing processing function to ensure data is consistent.
                    return self._process_login_record(record)
                except HTTPError:
                    logger.warning(
                        f"Failed to claim record {record_id} (likely claimed by another process)."
                    )
                    continue

        except Exception as e:
            logger.error(
                f"❌ An unexpected error occurred while fetching account for device {device_id}: {e}",
                exc_info=True,
            )

        logger.error(f"Could not claim any available account for device {device_id}.")
        return None

    def fetch_and_claim_account_for_login(self) -> Optional[Dict[str, Any]]:
        """
        Fetches an account from the 'Unused Accounts' view and atomically claims it.
        """
        view_name = "Unused Accounts"
        claim_status = "Login In Progress"
        logger.info(
            f"Attempting to fetch and claim a login account from view '{view_name}'..."
        )

        try:
            potential_accounts: Sequence[Dict[str, Any]] = self.accounts_table.all(
                view=view_name, max_records=5
            )
            if not potential_accounts:
                logger.warning(f"No accounts found in the '{view_name}' view.")
                return None

            for record in potential_accounts:
                record_id = record.get("id")
                if not isinstance(record_id, str):
                    continue
                try:
                    self.accounts_table.update(
                        record_id, {"Status": claim_status}, typecast=True
                    )
                    logger.info(
                        f"✅ Successfully claimed record {record_id} for login."
                    )
                    return self._process_login_record(record)
                except HTTPError:
                    logger.warning(
                        f"Failed to claim record {record_id} (likely claimed by another process)."
                    )
                    continue
        except Exception as e:
            logger.error(
                f"❌ An error occurred while fetching login accounts: {e}",
                exc_info=True,
            )

        return None

    def get_devices_with_ready_accounts(self) -> set[str]:
        """
        Scans the Airtable base and returns a unique set of Device IDs
        that have at least one account marked as ready for login.
        """
        logger.info("Querying Airtable for devices with ready accounts...")

        # This formula now includes 'Assigned' as a valid status to start a login task.
        formula = "OR({Status} = 'Assigned', {Status} = 'Ready for Login', {Status} = 'Unused')"

        ready_device_ids = set()
        try:
            # Fetch all records that match the formula
            records = self.accounts_table.all(formula=formula)

            for record in records:
                # The _flatten_field helper handles cases where the field might be a list
                device_id = self._flatten_field(
                    record.get("fields", {}).get("Device ID")
                )
                if device_id:
                    ready_device_ids.add(device_id)

            logger.info(
                f"Found {len(ready_device_ids)} devices with ready accounts in Airtable."
            )
            return ready_device_ids

        except Exception as e:
            logger.error(
                f"Failed to query Airtable for available devices: {e}", exc_info=True
            )
            return set()  # Return an empty set on error

    def fetch_account_for_warmup(self) -> Optional[Dict[str, Any]]:
        """
        Fetches an account that needs warming up from the 'Warmup' view.
        This is for a STANDALONE warmup bot run.
        """
        if not self.warmup_table:
            logger.error(
                "Warmup table ID is not configured. Cannot fetch warmup accounts."
            )
            return None

        logger.info("Fetching a warmup account...")
        try:
            records: Sequence[Dict[str, Any]] = self.warmup_table.all(
                view="Warmup", max_records=1
            )
            if not records:
                logger.warning("No accounts found in the 'Warmup' view.")
                return None
            return self._process_warmup_record(records[0])
        except Exception as e:
            logger.error(f"❌ Failed to fetch warmup account: {e}", exc_info=True)
            return None

    def update_record(
        self, table: Table, record_id: str, fields: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """A generic method to update any record in a given table."""
        if not record_id:
            logger.error("Update failed: record_id cannot be None.")
            return None
        try:
            logger.info(f"Updating record {record_id} with fields: {fields}")
            raw_updated_record = table.update(record_id, fields, typecast=True)
            return cast(Dict[str, Any], raw_updated_record)
        except Exception as e:
            logger.error(f"❌ Failed to update Airtable record {record_id}: {e}")
            return None
