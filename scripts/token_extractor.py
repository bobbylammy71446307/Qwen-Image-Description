"""
Automated token extraction for AIMO API
Extracts X-Token and Cookie from browser session using Selenium
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException


class TokenExtractor:
    """
    Extracts authentication tokens from AIMO web interface
    """

    def __init__(self, base_url="https://bj-robot.aimo.tech", headless=False):
        self.base_url = base_url
        self.headless = headless
        self.driver = None

    def _setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Enable performance logging to capture network requests
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def extract_tokens_from_logs(self):
        """Extract tokens from browser performance logs"""
        logs = self.driver.get_log('performance')

        for entry in logs:
            try:
                log = json.loads(entry['message'])['message']

                # Look for network requests
                if log['method'] == 'Network.requestWillBeSent':
                    request = log['params']['request']
                    url = request.get('url', '')

                    # Check if this is the API request we want
                    if 'getClockOutList' in url or 'api' in url:
                        headers = request.get('headers', {})

                        x_token = headers.get('X-Token') or headers.get('x-token')
                        cookie = headers.get('Cookie') or headers.get('cookie')

                        if x_token:
                            return {
                                'x_token': x_token,
                                'cookie': cookie,
                                'url': url,
                                'host': headers.get('Host', 'bj-robot.aimo.tech')
                            }
            except Exception as e:
                continue

        return None

    def extract_tokens_interactive(self, login_url=None):
        """
        Interactive token extraction - user logs in manually

        Args:
            login_url: URL to navigate to (default: base_url/new-alarm-handle)
        """
        if login_url is None:
            login_url = f"{self.base_url}/new-alarm-handle"

        print("[INFO] Setting up browser...")
        self._setup_driver()

        try:
            print(f"[INFO] Navigating to {login_url}")
            self.driver.get(login_url)

            print("\n" + "="*60)
            print("INSTRUCTIONS:")
            print("1. Log in to the website if needed")
            print("2. Navigate to the page that makes API calls")
            print("3. Wait for the page to load completely")
            print("4. The script will automatically extract tokens")
            print("="*60 + "\n")

            # Wait for user to log in and navigate
            print("[INFO] Waiting for API calls to be made...")
            print("[INFO] This window will stay open for 60 seconds")

            # Check logs periodically
            max_wait = 60
            check_interval = 2
            elapsed = 0

            while elapsed < max_wait:
                tokens = self.extract_tokens_from_logs()

                if tokens:
                    print("\n[SUCCESS] Tokens extracted successfully!")
                    print(f"[INFO] X-Token: {tokens['x_token']}")
                    print(f"[INFO] Cookie: {tokens['cookie']}")
                    return tokens

                time.sleep(check_interval)
                elapsed += check_interval

                if elapsed % 10 == 0:
                    print(f"[INFO] Still waiting... ({max_wait - elapsed}s remaining)")

            print("\n[WARNING] Timeout reached. Trying to extract from current cookies...")
            return self._extract_from_cookies()

        except Exception as e:
            print(f"[ERROR] Error during extraction: {e}")
            return None
        finally:
            if self.driver:
                print("\n[INFO] Closing browser...")
                self.driver.quit()

    def _extract_from_cookies(self):
        """Extract tokens from browser cookies as fallback"""
        try:
            cookies = self.driver.get_cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            # Try to get X-Token from localStorage
            x_token = self.driver.execute_script("return localStorage.getItem('token') || sessionStorage.getItem('token')")

            if not x_token:
                # Try common token storage locations
                possible_keys = ['x-token', 'X-Token', 'authToken', 'auth_token', 'accessToken']
                for key in possible_keys:
                    x_token = self.driver.execute_script(f"return localStorage.getItem('{key}') || sessionStorage.getItem('{key}')")
                    if x_token:
                        break

            if x_token or cookie_str:
                return {
                    'x_token': x_token,
                    'cookie': cookie_str,
                    'host': self.base_url.replace('https://', '').replace('http://', '')
                }

        except Exception as e:
            print(f"[ERROR] Could not extract from cookies: {e}")

        return None

    def extract_tokens_auto(self, username=None, password=None, login_url=None):
        """
        Automated token extraction with login credentials

        Args:
            username: Login username
            password: Login password
            login_url: Login page URL
        """
        if not username or not password:
            print("[ERROR] Username and password required for automatic extraction")
            return None

        if login_url is None:
            login_url = f"{self.base_url}/login"

        print("[INFO] Setting up browser for automatic login...")
        self._setup_driver()

        try:
            print(f"[INFO] Navigating to {login_url}")
            self.driver.get(login_url)

            # Wait for login form
            print("[INFO] Waiting for login form...")
            wait = WebDriverWait(self.driver, 10)

            # Try common login form selectors
            username_selectors = [
                "input[name='username']",
                "input[type='text']",
                "#username",
                "input[placeholder*='username' i]",
                "input[placeholder*='user' i]"
            ]

            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "#password"
            ]

            # Find and fill username
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue

            if not username_field:
                print("[ERROR] Could not find username field")
                return None

            print("[INFO] Entering username...")
            username_field.send_keys(username)

            # Find and fill password
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue

            if not password_field:
                print("[ERROR] Could not find password field")
                return None

            print("[INFO] Entering password...")
            password_field.send_keys(password)

            # Find and click submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button.login-button",
                "button.btn-login",
                "button",  # Any button
                ".el-button--primary",  # Element UI primary button
                "button.el-button",  # Element UI button
                "a.btn-login",  # Link styled as button
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    # Verify it's likely a submit button by checking text
                    button_text = submit_button.text.lower()
                    if any(word in button_text for word in ['login', 'submit', '登录', '提交', '']):
                        print(f"[INFO] Found button with text: {submit_button.text}")
                        break
                except:
                    continue

            if not submit_button:
                # Try finding all buttons and clicking the first visible one
                try:
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    print(f"[INFO] Found {len(all_buttons)} buttons on page")
                    for btn in all_buttons:
                        if btn.is_displayed():
                            print(f"[INFO] Trying button: {btn.text}")
                            submit_button = btn
                            break
                except:
                    pass

            if not submit_button:
                print("[ERROR] Could not find submit button")
                print("[INFO] Switching to interactive mode - please submit manually")
                print("[INFO] Waiting 30 seconds for you to click the login button...")
                time.sleep(30)
            else:
                print("[INFO] Submitting login form...")
                submit_button.click()

            # Wait for login to complete
            time.sleep(5)

            # Navigate to the API page
            print(f"[INFO] Navigating to {self.base_url}/new-alarm-handle")
            self.driver.get(f"{self.base_url}/new-alarm-handle")

            # Wait for API calls
            print("[INFO] Waiting for API calls...")
            time.sleep(5)

            # Extract tokens
            tokens = self.extract_tokens_from_logs()

            if not tokens:
                print("[INFO] No tokens in logs, trying cookies...")
                tokens = self._extract_from_cookies()

            if tokens:
                print("\n[SUCCESS] Tokens extracted successfully!")
                print(f"[INFO] X-Token: {tokens['x_token']}")
                print(f"[INFO] Cookie: {tokens['cookie']}")
            else:
                print("[ERROR] Could not extract tokens")

            return tokens

        except Exception as e:
            print(f"[ERROR] Error during automatic extraction: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if self.driver:
                print("\n[INFO] Closing browser...")
                self.driver.quit()


def save_tokens_to_file(tokens, filename='tokens.json'):
    """Save extracted tokens to a JSON file"""
    if not tokens:
        print("[ERROR] No tokens to save")
        return False

    try:
        with open(filename, 'w') as f:
            json.dump(tokens, f, indent=2)
        print(f"[SUCCESS] Tokens saved to {filename}")
        return True
    except Exception as e:
        print(f"[ERROR] Could not save tokens: {e}")
        return False


def load_tokens_from_file(filename='tokens.json'):
    """Load tokens from a JSON file"""
    try:
        with open(filename, 'r') as f:
            tokens = json.load(f)
        print(f"[SUCCESS] Tokens loaded from {filename}")
        return tokens
    except FileNotFoundError:
        print(f"[ERROR] File {filename} not found")
        return None
    except Exception as e:
        print(f"[ERROR] Could not load tokens: {e}")
        return None


if __name__ == "__main__":
    import sys

    print("="*60)
    print("AIMO Token Extractor")
    print("="*60)
    print("\nChoose extraction method:")
    print("1. Interactive (you log in manually)")
    print("2. Automatic (provide username/password)")
    print("3. Load from saved file")

    choice = input("\nEnter choice (1/2/3): ").strip()

    extractor = TokenExtractor(base_url="https://bj-robot.aimo.tech")
    tokens = None

    if choice == "1":
        tokens = extractor.extract_tokens_interactive()
        if tokens:
            save_tokens_to_file(tokens)

    elif choice == "2":
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        tokens = extractor.extract_tokens_auto(username, password)
        if tokens:
            save_tokens_to_file(tokens)

    elif choice == "3":
        tokens = load_tokens_from_file()

    else:
        print("Invalid choice")
        sys.exit(1)

    if tokens:
        print("\n" + "="*60)
        print("EXTRACTED TOKENS:")
        print("="*60)
        print(f"X-Token: {tokens.get('x_token', 'N/A')}")
        print(f"Cookie: {tokens.get('cookie', 'N/A')}")
        print("="*60)
