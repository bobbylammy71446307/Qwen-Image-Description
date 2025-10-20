import requests
import json
from datetime import datetime, timedelta
import threading
import time
import pytz
import os

class ClockOutReader:
    """
    Class to read and monitor clock out data from the API
    """
    def __init__(self, vin="as00214", dept_id=10, page_size=50, filter_mode='day', auto_refresh_tokens=False, token_file='tokens.json', base_url="https://hk1.aimo.tech", auto_extract_credentials=None):
        self.vin = vin
        self.dept_id = dept_id
        self.page_size = page_size
        self.filter_mode = filter_mode  # 'day' or 'hour'
        self.auto_refresh_tokens = auto_refresh_tokens
        self.token_file = token_file
        self.base_url = base_url
        self.auto_extract_credentials = auto_extract_credentials  # Dict with 'username' and 'password'
        self.running = False
        self.thread = None
        self.latest_urls = []
        self.all_urls = []  # Stores all URLs collected over time
        self.lock = threading.Lock()
        self.timezone = pytz.timezone('Asia/Hong_Kong')  # GMT+8
        self.token_expired = False

        # Try to load tokens from file if auto_refresh is enabled
        if self.auto_refresh_tokens and os.path.exists(self.token_file):
            self._load_tokens_from_file()
        else:
            self._set_default_headers()

    def _set_default_headers(self):
        """Set default headers with hardcoded tokens"""
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": "hk1.aimo.tech",
            "Referer": "https://hk1.aimo.tech/new-alarm-handle",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "X-Token": "BqzUCninVZUQ3v17XpxlBw==",
            "lang": "zh_TW",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "Cookie": "JSESSIONID=239B28B7FF97293918501C4D196D274E"
        }

    def _load_tokens_from_file(self):
        """Load tokens from JSON file and update headers"""
        try:
            with open(self.token_file, 'r') as f:
                tokens = json.load(f)

            print(f"[INFO] Loading tokens from {self.token_file}")

            # Set default headers first
            self._set_default_headers()

            # Update with tokens from file
            if 'x_token' in tokens and tokens['x_token']:
                self.headers['X-Token'] = tokens['x_token']
                print(f"[INFO] X-Token updated from file")

            if 'cookie' in tokens and tokens['cookie']:
                self.headers['Cookie'] = tokens['cookie']
                print(f"[INFO] Cookie updated from file")

            if 'host' in tokens and tokens['host']:
                self.headers['Host'] = tokens['host']
                self.headers['Referer'] = f"https://{tokens['host']}/new-alarm-handle"
                print(f"[INFO] Host updated to {tokens['host']}")

            return True

        except FileNotFoundError:
            print(f"[WARNING] Token file {self.token_file} not found, using default tokens")
            self._set_default_headers()
            return False
        except Exception as e:
            print(f"[ERROR] Error loading tokens: {e}")
            self._set_default_headers()
            return False

    def refresh_tokens(self):
        """Manually refresh tokens from token file"""
        return self._load_tokens_from_file()

    def update_tokens(self, x_token=None, cookie=None, host=None):
        """
        Manually update tokens

        Args:
            x_token: New X-Token value
            cookie: New Cookie value
            host: New host value
        """
        if x_token:
            self.headers['X-Token'] = x_token
            print(f"[INFO] X-Token updated")

        if cookie:
            self.headers['Cookie'] = cookie
            print(f"[INFO] Cookie updated")

        if host:
            self.headers['Host'] = host
            self.headers['Referer'] = f"https://{host}/new-alarm-handle"
            print(f"[INFO] Host updated to {host}")

        # Save to file if auto_refresh is enabled
        if self.auto_refresh_tokens:
            try:
                tokens = {
                    'x_token': self.headers.get('X-Token'),
                    'cookie': self.headers.get('Cookie'),
                    'host': self.headers.get('Host')
                }
                with open(self.token_file, 'w') as f:
                    json.dump(tokens, f, indent=2)
                print(f"[INFO] Tokens saved to {self.token_file}")
            except Exception as e:
                print(f"[ERROR] Could not save tokens: {e}")

    def _auto_extract_tokens(self):
        """
        Automatically extract fresh tokens using TokenExtractor
        Returns True if successful, False otherwise
        """
        try:
            # Import here to avoid dependency if not using auto-extract
            from token_extractor import TokenExtractor, save_tokens_to_file

            print("[INFO] Token expired or invalid. Attempting automatic token extraction...")

            if not self.auto_extract_credentials:
                print("[WARNING] No credentials provided for automatic token extraction")
                print("[INFO] Set auto_extract_credentials={'username': 'xxx', 'password': 'xxx'} to enable")
                return False

            username = self.auto_extract_credentials.get('username')
            password = self.auto_extract_credentials.get('password')

            if not username or not password:
                print("[ERROR] Invalid credentials for token extraction")
                return False

            print(f"[INFO] Extracting tokens for user: {username}")
            extractor = TokenExtractor(base_url=self.base_url, headless=True)
            tokens = extractor.extract_tokens_auto(username, password)

            if tokens:
                # Save to file
                save_tokens_to_file(tokens, self.token_file)

                # Update current headers
                if 'x_token' in tokens and tokens['x_token']:
                    self.headers['X-Token'] = tokens['x_token']
                    print("[INFO] X-Token updated")

                if 'cookie' in tokens and tokens['cookie']:
                    self.headers['Cookie'] = tokens['cookie']
                    print("[INFO] Cookie updated")

                if 'host' in tokens and tokens['host']:
                    self.headers['Host'] = tokens['host']
                    self.headers['Referer'] = f"https://{tokens['host']}/new-alarm-handle"
                    print(f"[INFO] Host updated to {tokens['host']}")

                self.token_expired = False
                print("[SUCCESS] Tokens automatically refreshed")
                return True
            else:
                print("[ERROR] Failed to extract tokens automatically")
                return False

        except ImportError:
            print("[ERROR] TokenExtractor not available. Please ensure token_extractor.py is in the same directory")
            return False
        except Exception as e:
            print(f"[ERROR] Error during automatic token extraction: {e}")
            return False

    def _check_token_expiration(self, response_data):
        """
        Check if the response indicates token expiration
        Returns True if token appears to be expired
        """
        if not response_data:
            return True

        # Common patterns for token expiration
        if isinstance(response_data, dict):
            code = response_data.get('code')
            msg = str(response_data.get('msg', '')).lower()

            # Check for common expiration codes/messages
            if code in [401, 403, -1]:
                return True
            if any(keyword in msg for keyword in ['token', 'unauthorized', 'expired', 'invalid', '未授权', '过期']):
                return True

        return False

    def get_clockout_list(self, page_no=1, start_time=None, end_time=None):
        """
        Get clock out list from the API
        """
        # Set default times if not provided (use GMT+8)
        if end_time is None:
            end_time = datetime.now(self.timezone)
        if start_time is None:
            start_time = end_time - timedelta(days=1)

        # Format times
        start_str = start_time.strftime("%Y-%m-%d+%H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d+%H:%M:%S")

        # API endpoint - use the host from headers
        api_host = self.headers.get('Host', 'hk1.aimo.tech')
        url = f"https://{api_host}/api/getClockOutList"

        # Parameters
        params = {
            "pageNo": page_no,
            "pageSize": self.page_size,
            "startTime": start_str,
            "endTime": end_str,
            "vin": self.vin,
            "deptId": self.dept_id
        }

        print(f"[DEBUG] Current time (GMT+8): {datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[DEBUG] API Request URL: {url}")
        print(f"[DEBUG] Parameters: {params}")
        print(f"[DEBUG] Time range: {start_str} to {end_str}")

        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            print(f"[DEBUG] Response status code: {response.status_code}")
            print(f"[DEBUG] Response content length: {len(response.content)}")
            print(f"[DEBUG] Response text preview: {response.text[:200]}")

            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Check if token expired
            if self._check_token_expiration(data):
                print("[WARNING] Token appears to be expired")
                self.token_expired = True

                # Try to auto-extract new tokens if enabled
                if self.auto_extract_credentials:
                    if self._auto_extract_tokens():
                        # Retry the request with new tokens
                        print("[INFO] Retrying request with new tokens...")
                        return self.get_clockout_list(page_no, start_time, end_time)
                    else:
                        print("[ERROR] Could not refresh tokens automatically")
                        return None
                else:
                    print("[ERROR] Token expired. Enable auto_extract_credentials or manually refresh tokens")
                    return None

            print(f"[DEBUG] Response keys: {data.keys() if data else 'None'}")
            if data and 'data' in data:
                print(f"[DEBUG] Data keys: {data['data'].keys()}")
                if 'rows' in data['data']:
                    print(f"[DEBUG] Number of rows: {len(data['data']['rows'])}")
                    if len(data['data']['rows']) > 0:
                        print(f"[DEBUG] First row sample: {data['data']['rows'][0]}")
            return data

        except json.JSONDecodeError as e:
            print(f"[ERROR] Error parsing JSON: {e}")
            print(f"[ERROR] Response text: {response.text[:500]}")

            # Empty response might indicate expired token
            if self.auto_extract_credentials and not self.token_expired:
                print("[INFO] Attempting token refresh due to JSON decode error...")
                if self._auto_extract_tokens():
                    return self.get_clockout_list(page_no, start_time, end_time)

            return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error making request: {e}")
            print(f"[ERROR] Response content (if available): {getattr(e.response, 'text', 'N/A')}")

            # 401/403 status codes indicate auth issues
            if hasattr(e.response, 'status_code') and e.response.status_code in [401, 403]:
                if self.auto_extract_credentials and not self.token_expired:
                    print("[INFO] Attempting token refresh due to authentication error...")
                    if self._auto_extract_tokens():
                        return self.get_clockout_list(page_no, start_time, end_time)

            return None

    def get_filtered_urls(self, result, filter_mode='day'):
        """
        Extract URLs from API result based on filter mode
        Parses timestamp from URL format: .../YYYYMMDD/HH/YYYYMMDDHHMMSS-...

        Args:
            result: API result containing rows with picUrl
            filter_mode: 'day' for same day, 'hour' for same hour (default: 'day')
        """
        if not result or 'data' not in result or 'rows' not in result['data']:
            print("[DEBUG] No result data or rows found")
            return []

        # Use GMT+8 timezone
        current_datetime = datetime.now(self.timezone)
        current_year = current_datetime.year
        current_month = current_datetime.month
        current_day = current_datetime.day
        current_hour = current_datetime.hour

        if filter_mode == 'hour':
            print(f"[DEBUG] Filtering for same hour (GMT+8): {current_year}-{current_month:02d}-{current_day:02d} {current_hour:02d}:00")
        else:  # filter_mode == 'day'
            print(f"[DEBUG] Filtering for same day (GMT+8): {current_year}-{current_month:02d}-{current_day:02d}")

        filtered_urls = []
        total_urls = 0

        for row in result['data']['rows']:
            if 'picUrl' not in row:
                continue

            pic_url = row['picUrl']
            total_urls += 1

            try:
                # Extract timestamp from URL
                # Format: .../YYYYMMDD/HH/YYYYMMDDHHMMSS-...
                parts = pic_url.split('/')

                # Find the timestamp part (YYYYMMDDHHMMSS-...)
                timestamp_part = None
                for part in parts:
                    if '-' in part and len(part.split('-')[0]) >= 14:
                        timestamp_part = part.split('-')[0]
                        break

                if not timestamp_part or len(timestamp_part) < 10:
                    print(f"[DEBUG] Skipping URL (no valid timestamp): {pic_url[:100]}")
                    continue

                # Parse timestamp: YYYYMMDDHHMMSS
                url_year = int(timestamp_part[0:4])
                url_month = int(timestamp_part[4:6])
                url_day = int(timestamp_part[6:8])
                url_hour = int(timestamp_part[8:10])

                # Check based on filter mode
                if filter_mode == 'hour':
                    match = (url_year == current_year and
                            url_month == current_month and
                            url_day == current_day and
                            url_hour == current_hour)
                    print(f"[DEBUG] URL timestamp: {url_year}-{url_month:02d}-{url_day:02d} {url_hour:02d}:00 | Match: {match}")
                else:  # filter_mode == 'day'
                    match = (url_year == current_year and
                            url_month == current_month and
                            url_day == current_day)
                    print(f"[DEBUG] URL timestamp: {url_year}-{url_month:02d}-{url_day:02d} {url_hour:02d}:00 | Match: {match}")

                if match:
                    filtered_urls.append(pic_url)

            except (ValueError, IndexError) as e:
                # Skip URLs that don't match expected format
                print(f"[DEBUG] Error parsing URL: {e} | URL: {pic_url[:100]}")
                continue

        print(f"[DEBUG] Total URLs in response: {total_urls}")
        print(f"[DEBUG] Filtered URLs for {filter_mode}: {len(filtered_urls)}")

        return filtered_urls

    def get_current_hour_urls(self, result):
        """
        Extract URLs for the current hour from API result (backward compatibility)
        """
        return self.get_filtered_urls(result, filter_mode='hour')

    def get_current_day_urls(self, result):
        """
        Extract URLs for the current day from API result
        """
        return self.get_filtered_urls(result, filter_mode='day')

    def _monitor_loop(self, interval=60):
        """
        Background monitoring loop
        """
        while self.running:
            result = self.get_clockout_list()
            if result:
                urls = self.get_filtered_urls(result, filter_mode=self.filter_mode)
                with self.lock:
                    self.latest_urls = urls
                    # Add new URLs to all_urls (avoid duplicates)
                    for url in urls:
                        if url not in self.all_urls:
                            self.all_urls.append(url)
                print(f"[{datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S')} GMT+8] Found {len(urls)} URLs for current {self.filter_mode} (Total: {len(self.all_urls)})")
            time.sleep(interval)

    def start_monitoring(self, interval=60):
        """
        Start monitoring in background
        """
        if self.running:
            print("Monitoring already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self.thread.start()
        print(f"Started monitoring (checking every {interval} seconds)")

    def stop_monitoring(self):
        """
        Stop background monitoring
        """
        if not self.running:
            print("Monitoring not running")
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Stopped monitoring")

    def get_latest_urls(self):
        """
        Get the latest URLs from background monitoring
        """
        with self.lock:
            return self.latest_urls.copy()

    def get_all_urls(self):
        """
        Get all URLs collected from monitoring
        """
        with self.lock:
            return self.all_urls.copy()

    def clear_all_urls(self):
        """
        Clear the accumulated URLs
        """
        with self.lock:
            self.all_urls.clear()

# Usage example
if __name__ == "__main__":
    # Start background monitoring
    # filter_mode can be 'day' (default) or 'hour'
    reader = ClockOutReader(vin="as00122", dept_id=10, page_size=50, filter_mode='day')
    reader.start_monitoring(interval=30)  # Check every 30 seconds

    print(f"Monitoring started (filter mode: {reader.filter_mode}). Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(5)  # Check for new URLs every 5 seconds
            urls = reader.get_latest_urls()
            if urls:
                print(f"\nCurrent {reader.filter_mode} URLs ({len(urls)}):")
                for url in urls[:5]:  # Show first 5 URLs
                    print(url)
                if len(urls) > 5:
                    print(f"... and {len(urls) - 5} more")
    except KeyboardInterrupt:
        print("\n\nStopping monitoring...")
        reader.stop_monitoring()