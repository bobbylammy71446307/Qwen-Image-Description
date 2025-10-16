import requests
import json
from datetime import datetime, timedelta
import threading
import time

class ClockOutReader:
    """
    Class to read and monitor clock out data from the API
    """
    def __init__(self, vin="as00214", dept_id=10, page_size=50):
        self.vin = vin
        self.dept_id = dept_id
        self.page_size = page_size
        self.running = False
        self.thread = None
        self.latest_urls = []
        self.all_urls = []  # Stores all URLs collected over time
        self.lock = threading.Lock()

        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": "bj-robot.aimo.tech",
            "Referer": "https://bj-robot.aimo.tech/new-alarm-handle",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "X-Token": "ChLGo8Wri53Hli61qdCxYw==",
            "lang": "zh_TW",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "Cookie": "JSESSIONID=AB3677EBCF4B75781B674BCC7B5087D4"
        }

    def get_clockout_list(self, page_no=1, start_time=None, end_time=None):
        """
        Get clock out list from the API
        """
        # Set default times if not provided
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=1)

        # Format times
        start_str = start_time.strftime("%Y-%m-%d+%H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d+%H:%M:%S")

        # API endpoint
        url = "https://bj-robot.aimo.tech/api/getClockOutList"

        # Parameters
        params = {
            "pageNo": page_no,
            "pageSize": self.page_size,
            "startTime": start_str,
            "endTime": end_str,
            "vin": self.vin,
            "deptId": self.dept_id
        }

        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()

            # Parse JSON response
            data = response.json()
            return data

        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return None

    def get_current_hour_urls(self, result):
        """
        Extract URLs for the current hour from API result
        Parses timestamp from URL format: .../YYYYMMDD/HH/YYYYMMDDHHMMSS-...
        """
        if not result or 'data' not in result or 'rows' not in result['data']:
            return []

        current_datetime = datetime.now()
        current_year = current_datetime.year
        current_month = current_datetime.month
        current_day = current_datetime.day
        current_hour = current_datetime.hour

        filtered_urls = []

        for row in result['data']['rows']:
            if 'picUrl' not in row:
                continue

            pic_url = row['picUrl']

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
                    continue

                # Parse timestamp: YYYYMMDDHHMMSS
                url_year = int(timestamp_part[0:4])
                url_month = int(timestamp_part[4:6])
                url_day = int(timestamp_part[6:8])
                url_hour = int(timestamp_part[8:10])

                # Check if it matches current date and hour
                if (url_year == current_year and
                    url_month == current_month and
                    url_day == current_day and
                    url_hour == current_hour):
                    filtered_urls.append(pic_url)

            except (ValueError, IndexError):
                # Skip URLs that don't match expected format
                continue

        return filtered_urls

    def _monitor_loop(self, interval=60):
        """
        Background monitoring loop
        """
        while self.running:
            result = self.get_clockout_list()
            if result:
                urls = self.get_current_hour_urls(result)
                with self.lock:
                    self.latest_urls = urls
                    # Add new URLs to all_urls (avoid duplicates)
                    for url in urls:
                        if url not in self.all_urls:
                            self.all_urls.append(url)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Found {len(urls)} URLs for current hour (Total: {len(self.all_urls)})")
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
    reader = ClockOutReader(vin="as00214", dept_id=10, page_size=50)
    reader.start_monitoring(interval=30)  # Check every 30 seconds

    print("Monitoring started. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(5)  # Check for new URLs every 5 seconds
            urls = reader.get_latest_urls()
            if urls:
                print(f"\nCurrent hour URLs ({len(urls)}):")
                for url in urls:
                    print(url)
    except KeyboardInterrupt:
        print("\n\nStopping monitoring...")
        reader.stop_monitoring()