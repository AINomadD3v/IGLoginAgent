
import uiautomator2 as u2
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_to_device(device_id=None):
    """
    Connects to an ADB device using uiautomator2.
    If device_id is None, it tries to connect to the first available device.
    """
    if device_id:
        logging.info(f"Attempting to connect to device: {device_id}")
    else:
        logging.info("Attempting to connect to the first available device.")
    try:
        if device_id:
            d = u2.connect(device_id)
        else:
            d = u2.connect() # Connect to the first available device
        
        if d.device_info:
            logging.info(f"Successfully connected to device: {d.device_info.get('serial')}")
            return d
        else:
            logging.error(f"Failed to connect to device: {device_id if device_id else 'any device'}. Device info not available.")
            return None
    except Exception as e:
        logging.error(f"Error connecting to device {device_id if device_id else 'any device'}: {e}")
        return None

def close_current_app(device):
    """
    Closes the currently foregrounded application on the device.
    """
    if device:
        try:
            current_package = device.app_current()['package']
            if current_package:
                logging.info(f"Closing app: {current_package}")
                device.app_stop(current_package)
                logging.info(f"App {current_package} closed successfully.")
            else:
                logging.warning("No app in foreground to close.")
        except Exception as e:
            logging.error(f"Error closing current app: {e}")
    else:
        logging.warning("No device connected, cannot close app.")

def open_instagram(device):
    """
    Opens the Instagram application on the device.
    """
    instagram_package = "com.instagram.android"
    if device:
        try:
            logging.info(f"Opening Instagram app: {instagram_package}")
            device.app_start(instagram_package)
            logging.info("Instagram app opened successfully.")
        except Exception as e:
            logging.error(f"Error opening Instagram app: {e}")
    else:
        logging.warning("No device connected, cannot open Instagram.")

def click_on_screen(device):
    """
    Performs a click action on the center of the device screen.
    """
    if device:
        try:
            screen_width = device.info['displayWidth']
            screen_height = device.info['displayHeight']
            center_x = screen_width // 2
            center_y = screen_height // 2
            logging.info(f"Clicking on screen at coordinates: ({center_x}, {center_y})")
            device.click(center_x, center_y)
            logging.info("Click action performed successfully.")
        except Exception as e:
            logging.error(f"Error performing click on screen: {e}")
    else:
        logging.warning("No device connected, cannot perform click.")

if __name__ == "__main__":
    logging.info("Starting ADB connection, click, close app, and open Instagram process.")
    device = connect_to_device() # Attempt to connect to the first available device directly
    if device:
        click_on_screen(device)
        close_current_app(device)
        open_instagram(device)
    else:
        logging.error("No devices found or failed to connect to any device.")
    logging.info("ADB process finished.")

