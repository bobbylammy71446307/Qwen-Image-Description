#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime, timedelta
import pytz
import yaml
import requests
from qwen_description import QwenDescriber
from image_get import ClockOutReader

PROCESSED_FILE = "processed_images.json"

def load_processed_list(filepath=PROCESSED_FILE):
    """Load the list of already processed image URLs"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                print(f"[INFO] Loaded {len(data)} processed URLs from {filepath}")
                return set(data)
        except Exception as e:
            print(f"[WARNING] Error loading processed list: {e}")
            return set()
    return set()

def save_processed_list(processed_urls, filepath=PROCESSED_FILE):
    """Save the list of processed image URLs"""
    try:
        with open(filepath, 'w') as f:
            json.dump(list(processed_urls), f, indent=2)
        print(f"[INFO] Saved {len(processed_urls)} processed URLs to {filepath}")
        return True
    except Exception as e:
        print(f"[ERROR] Error saving processed list: {e}")
        return False

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
    robot_name = os.getenv('ROBOT_NAME', 'as00108')  # Default to 'as00214' if not set
    dept_id = int(os.getenv('DEPT_ID', '10'))  # Default to 10 if not set
    # Get time range from environment variable (in hours, supports decimals like 0.5 for 30 minutes)
    fetch_time_range_hours = float(os.getenv('FETCH_TIME_RANGE_HOURS', '10'))

    # Get language setting from environment variable (english or chinese)
    language = os.getenv('LANGUAGE', 'chinese').lower()

    # Get API credentials for automatic token extraction
    api_username = os.getenv('API_USERNAME')
    api_password = os.getenv('API_PASSWORD')
    api_base_url = os.getenv('API_BASE_URL', 'https://hk1.aimo.tech')

    print(f"[INFO] Robot name: {robot_name}")
    print(f"[INFO] Department ID: {dept_id}")
    print(f"[INFO] Fetch time range: {fetch_time_range_hours} hour(s)")
    print(f"[INFO] API Base URL: {api_base_url}")
    print(f"[INFO] Language: {language}")

    # Setup credentials if provided
    credentials = None
    if api_username and api_password:
        credentials = {
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
        token_file='tokens.json',
        base_url=api_base_url,
        credentials=credentials  # Fresh tokens will be acquired on initialization
    )

    # Initialize unified describer with language setting
    if language == 'chinese':
        print("[INFO] Using Chinese mode with prompt_chinese.txt")
        describer = QwenDescriber(prompt_file='prompt_chinese.txt', language='chinese')
    else:
        print("[INFO] Using English mode with prompt_english.txt")
        describer = QwenDescriber(prompt_file='prompt_english.txt', language='english')

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

    # Load previously processed URLs
    processed_urls = load_processed_list()

    # Fetch clock out list for the specified time range
    result = reader.get_clockout_list(page_no=1, start_time=start_time, end_time=current_time)

    if not result:
        print("[WARNING] No data received from API")
        sys.exit(0)

    # Extract all data items from the result (including location data)
    all_items = []
    if result and 'data' in result and 'rows' in result['data']:
        for row in result['data']['rows']:
            if 'picUrl' in row:
                all_items.append({
                    'picUrl': row['picUrl'],
                    'lon': row.get('lon'),
                    'lat': row.get('lat'),
                    'clockOutPlace': row.get('clockOutPlace')
                })

    print(f"[INFO] Found {len(all_items)} total items in response")

    # Filter out already processed URLs
    unprocessed_items = [item for item in all_items if item['picUrl'] not in processed_urls]
    print(f"[INFO] {len(unprocessed_items)} new items to process ({len(all_items) - len(unprocessed_items)} already processed)")

    if len(unprocessed_items) == 0:
        print("[INFO] No new URLs to process. Exiting.")
        sys.exit(0)

    processed_count = 0
    failed_count = 0
    post_success_count = 0
    post_failed_count = 0

    # Process each unprocessed item
    for idx, item in enumerate(unprocessed_items, 1):
        try:
            url = item['picUrl']
            print(f"[PROCESSING] ({idx}/{len(unprocessed_items)}) {url}")

            output_path = describer.process_and_annotate(url)

            # Add to processed set immediately after success
            processed_urls.add(url)
            processed_count += 1
            print(f"[SUCCESS] Processed: {url}")

            # Post to server immediately after annotation completion
            try:
                annotation_time = datetime.now(hong_kong_tz)

                # Determine how many posts to send based on unique_labels
                if len(describer.unique_labels) == 0:
                    # No detections - send single post with ai_description
                    print(f"[INFO] No detections found. Sending single post with model_type: ai_description")
                    post_data = {
                        "model_type": "ai_description",
                        "time": annotation_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "robot": robot,
                        "camera": camera,
                        "pose": get_robot_pose(),
                        "image_path": [output_path],  # Single image path in array
                        "lon": item.get('lon'),
                        "lat": item.get('lat'),
                        "clockOutPlace": item.get('clockOutPlace'),
                        "aiText": describer.ai_text  # Add AI-generated text description
                    }
                    if post_json_data(post_data, post_endpoint, timeout=api_timeout):
                        post_success_count += 1
                        print(f"[SUCCESS] Posted annotation to server: {output_path}")
                    else:
                        post_failed_count += 1
                        print(f"[WARNING] Failed to post annotation to server: {output_path}")
                else:
                    # One or more detections - send one post per unique label
                    print(f"[INFO] Found {len(describer.unique_labels)} unique detection(s). Sending post for each label.")
                    for label in describer.unique_labels:
                        post_data = {
                            "model_type": label,
                            "time": annotation_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "robot": robot,
                            "camera": camera,
                            "pose": get_robot_pose(),
                            "image_path": [output_path],  # Single image path in array
                            "lon": item.get('lon'),
                            "lat": item.get('lat'),
                            "clockOutPlace": item.get('clockOutPlace'),
                            "aiText": describer.ai_text  # Add AI-generated text description
                        }
                        if post_json_data(post_data, post_endpoint, timeout=api_timeout):
                            post_success_count += 1
                            print(f"[SUCCESS] Posted annotation with model_type '{label}' to server: {output_path}")
                        else:
                            post_failed_count += 1
                            print(f"[WARNING] Failed to post annotation with model_type '{label}' to server: {output_path}")

            except Exception as post_error:
                post_failed_count += 1
                print(f"[ERROR] Error posting to server: {post_error}")

        except Exception as e:
            print(f"[ERROR] Failed processing {url}: {e}")
            failed_count += 1

    # Save updated processed list
    save_processed_list(processed_urls)

    print(f"[INFO] Processing complete: {processed_count} successful, {failed_count} failed")
    print(f"[INFO] Server posting: {post_success_count} successful, {post_failed_count} failed")
    sys.exit(0)

if __name__=="__main__":
    main()