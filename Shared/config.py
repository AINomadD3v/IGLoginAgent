# Shared/config.py
# A single, unified configuration file for all bot settings, popups, and XPath selectors.


class ScrollerConfig:
    """All settings for the Warmup/Scroller bot."""

    KEYWORDS = [
        "female model",
        "female fitness",
        "american model",
        "bikini",
        "gym girl",
        "fit girls",
        "fitness model",
        "hot woman",
        "blonde model",
        "asian model",
    ]
    DELAYS = {
        "after_like": [1.8, 2.3],
        "between_scrolls": [2.0, 3.0],
        "before_scroll": [1.5, 2.2],
        "after_post_tap": [1.0, 1.5],
        "after_comment": [1.2, 2.0],
        "default": [1.0, 2.0],
    }
    MAX_SCROLLS = 100
    PERCENT_REELS_TO_WATCH = 0.8
    WATCH_TIME_RANGE = [4.0, 9.0]
    LIKE_PROBABILITY = 0.7
    COMMENT_PROBABILITY = 0.25
    IDLE_AFTER_ACTIONS_RANGE = [3, 6]
    IDLE_DURATION_RANGE = [2, 6]


class PopupConfig:
    """
    Configuration for all popups handled by the watcher.
    Each watcher uses a robust XPath selector to identify the popup and take action.
    """

    WATCHERS = [
        # --- Core App/System Popups ---
        {
            "name": "save_login_info_prompt",
            "text_xpath": "//*[@content-desc='Save your login info?']",
            "button_xpath": "//*[@content-desc='Save']",
            "callback": "handle_save_login_info",
        },
        {
            "name": "allow_notifications",
            "text_xpath": "//*[contains(@text, 'send you notifications')]",
            "button_xpath": "//*[contains(@resource-id, 'permission_allow_button')]",
        },
        {
            "name": "old_android_version_warning",
            "text_xpath": "//*[@resource-id='android:id/message' and contains(@text, 'built for an older version')]",
            "button_xpath": "//*[@resource-id='android:id/button1' and (contains(@text, 'OK') or contains(@text, 'Ok'))]",
        },
        {
            "name": "allow_media_access",
            "text_xpath": "//*[contains(@text, 'access photos')]",
            "button_xpath": "//*[contains(@resource-id, 'permission_allow_button')]",
        },
        {
            "name": "setup_new_device_contacts",
            "text_xpath": "//*[contains(@text, 'contacts') and contains(@text, 'people to follow')]",
            "button_xpath": "//*[@content-desc='Skip' or @text='Skip']",
        },
        # --- Account Status/Warning Popups ---
        {
            "name": "account_suspended_popup",
            "text_xpath": "//*[starts-with(@text, 'We suspended your account') or contains(@text, 'account has been suspended')]",
            "button_xpath": None,
            "callback": "handle_suspension",
        },
        {
            "name": "account_restriction_popup",
            "text_xpath": "//*[contains(@content-desc, 'We added a restriction to your account')]",
            "button_xpath": "//*[@content-desc='Cancel' or @text='Cancel']",
        },
        {
            "name": "photo_removed_popup",
            "text_xpath": "//*[starts-with(@text, 'We removed your')]",
            "button_xpath": None,
            "callback": "photo_removed_callback",
        },
        # --- Generic/Miscellaneous Popups ---
        {
            "name": "generic_error_toast",
            "text_xpath": "//*[contains(@text, 'Something went wrong')]",
            "button_xpath": None,
            "callback": "handle_generic_error_toast",
        },
        {
            "name": "edit_reel_draft_popup",
            "text_xpath": "//*[contains(@text, 'editing your draft?')]",
            "button_xpath": "//*[contains(@text, 'Start new video')]",
        },
        {
            "name": "new_ways_to_reuse_popup",
            "text_xpath": "//*[contains(@text, 'New ways to reuse')]",
            "button_xpath": "//*[@content-desc='OK' or @text='OK']",
        },
        {
            "name": "reels_create_prompt",
            "text_xpath": "//*[contains(@text, 'Create longer Reels')]",
            "button_xpath": "//*[@text='OK']",
        },
        {
            "name": "samsung_pass_autofill",
            "text_xpath": "//*[@resource-id='android:id/autofill_save_icon']",
            "button_xpath": "//*[@resource-id='android:id/autofill_save_no']",
        },
        # --- VPN/External App Popups ---
        {
            "name": "nordvpn_slow_connection",
            "text_xpath": "//*[@content-desc='Connecting…, It’s taking a bit longer than usual.']",
            "button_xpath": None,
            "callback": "handle_vpn_slow_connection",
        },
    ]


class XpathConfig:
    """A single, consolidated source for all XPath selectors, using robust patterns."""

    def __init__(self, package_name: str):
        if not package_name:
            raise ValueError("Package name cannot be empty for XpathConfig")
        self.package_name = package_name

    # --- Login, 2FA, and Account Status ---
    @property
    def login_page_identifier(self):
        return "//*[@content-desc='Forgot password?']"

    @property
    def login_username_field(self):
        return "//*[contains(@text, 'Username, email')]"

    @property
    def login_password_field(self):
        return "//*[contains(@text, 'Password')]"

    @property
    def login_button(self):
        return "//android.widget.Button[@content-desc='Log in']"

    @property
    def login_loading_indicator(self):
        return "//android.widget.Button[@content-desc='Loading...']"

    @property
    def incorrect_password_text(self):
        return "//*[@text='Incorrect password' or @text='Incorrect Password']"

    @property
    def incorrect_password_ok_button(self):
        return "//android.widget.Button[@text='OK']"

    @property
    def two_fa_page_identifier(self):
        return "//*[@text='Check your email' or @content-desc='two_factor_required_challenge']"

    @property
    def two_fa_code_input(self):
        return "//*[starts-with(@text, 'Enter') and contains(@text, 'code')]"

    @property
    def two_fa_confirm_button(self):
        return "//*[contains(@text, 'Continue') or contains(@text, 'Confirm')]"

    @property
    def account_suspended_text(self):
        return "//*[contains(@text, 'account has been suspended')]"

    # --- Post-Login & Home Screen ---
    @property
    def save_login_info_prompt(self):
        return "//*[@content-desc='save_login_info_dialog_title' or contains(@text, 'Save your login info')]"

    @property
    def save_login_info_save_button(self):
        return "//android.widget.Button[@content-desc='Save']"

    @property
    def turn_on_notifications_prompt(self):
        return "//*[contains(@text, 'Turn on notifications')]"

    @property
    def home_feed_identifier(self):
        return "//*[@text='Your story']"

    # --- Navigation ---
    @property
    def nav_creation_tab(self):
        return f"//android.widget.FrameLayout[@resource-id='{self.package_name}:id/creation_tab']"

    @property
    def nav_explore_tab(self):
        return '//*[contains(@content-desc, "Search and explore")]'

    @property
    def nav_back_button(self):
        return '//*[@content-desc="Back"]'

    @property
    def nav_next_button(self):
        return '//*[@content-desc="Next" or @text="Next"]'

    @property
    def nav_share_button(self):
        return '//*[@content-desc="Share" or @text="Share"]'

    @property
    def nav_done_button(self):
        return '//*[@content-desc="Done" or @text="Done"]'

    # --- Search & Discovery (Scroller) ---
    @property
    def explore_search_bar(self):
        return f"//*[@resource-id='{self.package_name}:id/action_bar_search_edit_text']"

    @property
    def search_results_container(self):
        return f"//*[contains(@resource-id, 'recycler_view')]"

    @property
    def search_layout_container_frame(self):
        return f"//android.widget.FrameLayout[contains(@resource-id, 'layout_container') or .//android.widget.ImageView]"

    @property
    def search_image_post_button(self):
        return ".//android.widget.Button[contains(@content-desc, 'photos by')]"

    @property
    def search_reel_imageview(self):
        return ".//android.widget.ImageView[contains(@content-desc, 'Reel by')]"

    def search_reel_imageview_template(self, desc):
        return f'//android.widget.ImageView[@content-desc="{desc}"]'

    # --- In-Reel Viewing (Scroller) ---
    @property
    def reel_profile_picture(self):
        return (
            "//android.widget.ImageView[contains(@content-desc, 'Profile picture of')]"
        )

    @property
    def reel_caption_container(self):
        return f"//*[@resource-id='{self.package_name}:id/clips_caption_component']"

    @property
    def reel_likes_button(self):
        return "//*[contains(@content-desc, 'likes')]"

    @property
    def reel_comment_button(self):
        return '//*[contains(@content-desc, "Comment")]'

    @property
    def reel_reshare_button(self):
        return "//*[contains(@content-desc, 'Reshare number')]"

    @property
    def reel_audio_link(self):
        return "//*[contains(@content-desc, 'Original audio')]"

    @property
    def reel_follow_button(self):
        return "//android.widget.Button[@text='Follow']"

    @property
    def reel_like_or_unlike_button(self):
        return '//*[@content-desc="Like" or @content-desc="Unlike"]'
