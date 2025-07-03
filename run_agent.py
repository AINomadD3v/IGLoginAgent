import argparse
import subprocess
import time
from multiprocessing import Pool, freeze_support

# Adjust the import path to match your project structure
from Shared.Utils.airtable_manager import AirtableClient

# --- Define the available workflows ---
WORKFLOWS = {
    "login": "Login/login_bot.py",
    "warmup": "Warmup/scroller.py",
}

# --- Helper Functions ---


def get_connected_devices() -> set[str]:
    """
    Gets a set of connected ADB device serials.
    Using a set provides fast, duplicate-free lookups.
    """
    print("🔌 Checking for connected ADB devices...")
    try:
        # Execute 'adb devices' and capture the output
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, check=True, timeout=10
        )
        devices = set()
        # Parse the output to get device serials, skipping the header line
        for line in result.stdout.strip().split("\n")[1:]:
            if "device" in line:
                devices.add(line.split("\t")[0])
        print(f"   Found: {devices or 'None'}")
        return devices
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ) as e:
        print(
            f"   ❌ Error getting ADB devices: {e}. Is ADB installed and in your PATH?"
        )
        return set()


def run_worker_process(process_id: int, script_to_run: str, device_id: str):
    """
    This function is executed by each process in the pool.
    It runs the target script with a specific device_id.
    """
    worker_log_prefix = f"[Device: {device_id} | Worker-{process_id}]"
    print(f"🚀 {worker_log_prefix} Starting...")

    try:
        # Pass the device_id to the worker script as a command-line argument.
        # Capturing output allows for cleaner logs unless a failure occurs.
        result = subprocess.run(
            ["python3", script_to_run, "--device-id", device_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=1800,  # 30-minute timeout per worker
        )
        print(f"✅ {worker_log_prefix} Finished successfully.")
        # Uncomment the line below if you want to see the worker's output on success
        # if result.stdout: print(f"   - STDOUT: {result.stdout}")

    except subprocess.CalledProcessError as e:
        # This catches errors where the script runs but returns a non-zero exit code
        print(f"❌ {worker_log_prefix} Failed with an error!")
        print(f"   - STDOUT: {e.stdout}")
        print(f"   - STDERR: {e.stderr}")

    except subprocess.TimeoutExpired as e:
        print(f"⏰ {worker_log_prefix} Timed out after {e.timeout} seconds.")

    except Exception as e:
        # This catches other errors, like the script not being found
        print(f"💥 {worker_log_prefix} An unexpected error occurred: {e}")

    return device_id


# --- Main Execution Block ---

if __name__ == "__main__":
    # freeze_support() is necessary for multiprocessing to work correctly when frozen (e.g., in an executable)
    freeze_support()

    # 1. Set up the argument parser
    parser = argparse.ArgumentParser(
        description="Airtable-driven parallel automation orchestrator."
    )
    parser.add_argument(
        "--flow",
        type=str,
        choices=WORKFLOWS.keys(),
        required=True,
        help="The automation flow to run ('login' or 'warmup').",
    )
    args = parser.parse_args()
    target_script = WORKFLOWS[args.flow]

    print(f"\n--- Starting Orchestrator for '{args.flow}' flow ---")
    start_time = time.time()

    # 2. Identify all devices ready for work
    physically_connected_devices = get_connected_devices()

    print("📋 Querying Airtable for devices with ready accounts...")
    airtable_client = AirtableClient()
    devices_in_airtable = airtable_client.get_devices_with_ready_accounts()
    print(f"   Found: {devices_in_airtable or 'None'}")

    # 3. Find the intersection of devices that are both connected and configured in Airtable
    devices_to_run = list(
        physically_connected_devices.intersection(devices_in_airtable)
    )

    # 4. Check if there is any work to do
    if not devices_to_run:
        print(
            "\n🛑 No devices to process. A device must be both physically connected and have a 'Ready' account in Airtable."
        )
        exit()

    num_processes = len(devices_to_run)
    print(f"\n▶️ Found {num_processes} device(s) ready for work: {devices_to_run}")

    # 5. Prepare arguments and launch the process pool
    worker_args = [
        (i, target_script, device_id) for i, device_id in enumerate(devices_to_run)
    ]

    print(f"--- Launching {num_processes} worker(s) for script: {target_script} ---\n")

    with Pool(processes=num_processes) as pool:
        # starmap is used to pass multiple arguments to the worker function
        results = pool.starmap(run_worker_process, worker_args)

    end_time = time.time()
    print("\n--- Orchestrator Finished ---")
    print(f"✅ All {len(results)} launched worker(s) have completed.")
    print(f"⏱️ Total execution time: {end_time - start_time:.2f} seconds.")
