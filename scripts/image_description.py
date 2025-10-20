#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timedelta
import pytz
import yaml
import requests
from qwen_description import QwenDescriber
from image_get import ClockOutReader

def post_json_data(json_data, post_url, timeout=10):
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(post_url, json=json_data, headers=headers, timeout=timeout)
        response.raise_for_status()
        print(f"Successfully posted JSON data to {post_url}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to post JSON data to {post_url}: {e}")
        return False


def load_model_config(config_path="./config.yaml"):
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config file: {e}")    

        sys.exit(1)

def get_robot_pose():
    pose = {"x" : 0,
            "y" : 0,
            "z" : 0,
            "r" : 0,
            "p" : 0,
            "y" : 0 }
    return pose


def main():
    # Get robot name from environment variable
    robot_name = os.getenv('ROBOT_NAME', 'as00122')  # Default to 'as00214' if not set
    dept_id = int(os.getenv('DEPT_ID', '10'))  # Default to 10 if not set
    # Get time range from environment variable (in hours, default 12)
    fetch_time_range_hours = int(os.getenv('FETCH_TIME_RANGE_HOURS', '12'))

    # Get API credentials for automatic token extraction
    api_username = os.getenv('API_USERNAME')
    api_password = os.getenv('API_PASSWORD')
    api_base_url = os.getenv('API_BASE_URL', 'https://hk1.aimo.tech')

    print(f"[INFO] Robot name: {robot_name}")
    print(f"[INFO] Department ID: {dept_id}")
    print(f"[INFO] Fetch time range: {fetch_time_range_hours} hour(s)")
    print(f"[INFO] API Base URL: {api_base_url}")

    # Setup auto-extraction credentials if provided
    auto_extract_credentials = None
    if api_username and api_password:
        auto_extract_credentials = {
            'username': api_username,
            'password': api_password
        }
        print(f"[INFO] Automatic token extraction enabled for user: {api_username}")
    else:
        print("[WARNING] API credentials not provided. Automatic token refresh disabled.")
        print("[WARNING] Set API_USERNAME and API_PASSWORD environment variables to enable.")

    # Initialize reader as a service (no background thread)
    reader = ClockOutReader(
        vin=robot_name,
        dept_id=dept_id,
        page_size=50,
        auto_refresh_tokens=True,
        token_file='tokens.json',
        base_url=api_base_url,
        auto_extract_credentials=auto_extract_credentials
    )
    describer = QwenDescriber()

    # Load configuration
    config = load_model_config()

    # Get API configuration
    api_config = config.get("api", {})
    post_endpoint = api_config.get("post_endpoint", "http://post-server:8080/api/detections")
    api_timeout = api_config.get("timeout", 10)

    # Create output directories
    hong_kong_tz = pytz.timezone('Asia/Hong_Kong')

    robot = robot_name
    camera = "front_camera"

    current_time = datetime.now(hong_kong_tz)
    start_time = current_time - timedelta(hours=fetch_time_range_hours)

    print(f"[INFO] Processing images from: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Fetch clock out list for the specified time range
    result = reader.get_clockout_list(page_no=1, start_time=start_time, end_time=current_time)

    if not result:
        print("[WARNING] No data received from API")
        sys.exit(0)

    # Extract all URLs from the result (no filtering by current day/hour)
    all_urls = []
    if result and 'data' in result and 'rows' in result['data']:
        for row in result['data']['rows']:
            if 'picUrl' in row:
                all_urls.append(row['picUrl'])

    print(f"[INFO] Found {len(all_urls)} total URLs in response")

    if len(all_urls) == 0:
        print("[INFO] No URLs to process. Exiting.")
        sys.exit(0)

    output_path_list = []
    processed_count = 0
    failed_count = 0

    # Process each URL
    for idx, url in enumerate(all_urls, 1):
        try:
            print(f"[PROCESSING] ({idx}/{len(all_urls)}) {url}")

            output_path = describer.process_and_annotate(url)
            output_path_list.append(output_path)
            processed_count += 1
            print(f"[SUCCESS] Processed: {url}")

        except Exception as e:
            print(f"[ERROR] Failed processing {url}: {e}")
            failed_count += 1

    # Post results if any images were processed
    if output_path_list:
        post_data = {
            "model_type": "ai_description",
            "time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "robot": robot,
            "camera": camera,
            "pose": get_robot_pose(),
            "image_path": output_path_list
        }
        post_json_data(post_data, post_endpoint, timeout=api_timeout)
        print(f"[INFO] Posted {len(output_path_list)} results to API")

    print(f"[INFO] Processing complete: {processed_count} successful, {failed_count} failed")
    sys.exit(0)

if __name__=="__main__":
    main()