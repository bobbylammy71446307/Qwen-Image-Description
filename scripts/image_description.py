#!/usr/bin/env python3

import cv2
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO
import time
from datetime import datetime
import pytz
import yaml
import requests
import time
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


def detection(detector, frame, json_tmp, conf_threshold,class_list):
    results = detector.predict(frame, conf=conf_threshold, verbose=True, classes=class_list)
    detections,bbox_list = [], []
    frame_height, frame_width = frame.shape[:2]
    for result in results:
        if hasattr(result, 'boxes') and result.boxes is not None:
            boxes = result.boxes
            for box in boxes:
                # Get box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                if (x2 - x1) * (y2 - y1) / (frame_height * frame_width) < 0.9:
                    detections.append({"x1": x1,
                                       "y1": y1, 
                                       "x2": x2,
                                       "y2": y2,
                                       "width": x2 - x1,
                                       "height": y2 - y1
                                       })
                    bbox_list.append([x1,x2,y1,y2])    
    json_tmp.update({ "bounding_box": detections })
    return json_tmp,bbox_list


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


def get_config(config_type, key, config):
    config_list = config.get(config_type, {})
    if key not in config_list:
        available_models = list(config_list.keys())
        print(f"Model type '{key}' not found in config.")
        print(f"Available models: {available_models}")
        sys.exit(1)
    return config_list[key]


def get_time(tz):
    now = datetime.now(tz)
    day = now.strftime('%d')
    month = now.strftime('%m')
    year = now.strftime('%Y')
    hour = now.strftime('%H')
    return day,month,year,hour


def create_output_directories(tz):
    day, month, year, hour = get_time(tz)
    base_path="./output"

    # Create directory path
    dir_path = Path(base_path) / year / month / day / hour
    dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories for images and json
    images_dir = dir_path / "images"
    images_dir.mkdir(exist_ok=True)
    output_path = Path("AI") / year / month / day / hour / "images"

    
    return images_dir, output_path

def rtsp_stream_init(rtsp_url):
    # Initialize RTSP stream with timeout settings
    video_cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    # Optimize buffer settings for low latency and set timeout
    video_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    video_cap.set(cv2.CAP_PROP_FPS, 15)  # Limit FPS
    # Set RTSP timeout to 60 seconds (in milliseconds)
    video_cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 60000)
    video_cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 60000)
    # Additional optimizations
    video_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    video_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    return video_cap

def blur_face(image,frame_count):
    face_detector = YOLO("./models/face_bounding.pt")
    results = face_detector.predict(image, conf=0.5, verbose=True)
    for result in results:
        if hasattr(result, 'boxes') and result.boxes is not None:
            boxes = result.boxes
            for box in boxes:
                # Get box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                # Apply Gaussian blur to the detected face region
                face_region = image[y1:y2, x1:x2]
                blurred_face = cv2.GaussianBlur(face_region, (99, 99), 30)
                image[y1:y2, x1:x2] = blurred_face
                print(f"Blurred face at frame {frame_count}")
    return image

def get_robot_pose():
    pose = {"x" : 0,
            "y" : 0,
            "z" : 0,
            "r" : 0,
            "p" : 0,
            "y" : 0 }
    return pose


def main():
    reader = ClockOutReader(vin="as00214", dept_id=10, page_size=50)
    reader.start_monitoring(interval=30)
    describer=QwenDescriber()
    print("Monitoring started. Press Ctrl+C to stop.\n")
    processed_url=[]
    # Load configuration
    config = load_model_config()
    
    # Get API configuration
    api_config = config.get("api", {})
    post_endpoint = api_config.get("post_endpoint", "http://post-server:8080/api/detections")
    api_timeout = api_config.get("timeout", 10)
    
    # Create output directories
    hong_kong_tz = pytz.timezone('Asia/Hong_Kong')

    robot = "as00214"
    camera = "front_camera"
    post_data={ "model_type": "ai_description",
                "time": datetime.now(hong_kong_tz).strftime("%Y-%m-%d %H:%M:%S"),
                "robot": robot,
                "camera": camera,
                "pose":  get_robot_pose()}
    

    try:
        while True:
            # Get latest URLs from reader
            latest_urls = reader.get_latest_urls()

            # Create list of unprocessed URLs
            unprocessed_urls = [url for url in latest_urls if url not in processed_url]

            output_path_list= []

            # Process each unprocessed URL
            for url in unprocessed_urls:
                try:
                    print(f"Processing URL: {url}")

                    output_path = describer.process_and_annotate(url)
                    output_path_list.append(output_path)

                    # Mark as processed after successful completion
                    processed_url.append(url)
                    print(f"Successfully processed and added to processed list: {url}")

                except Exception as e:
                    print(f"Error processing URL {url}: {e}")
                    # Don't add to processed_url if processing failed

            if len(output_path_list)!=0:
                post_data.update({"image_path": output_path_list})
                post_json_data(post_data, post_endpoint, timeout=10)
                print(post_data)


            # Sleep before checking for new URLs
            time.sleep(30)

    except KeyboardInterrupt:
        print("\nStopping URL processing...")
    finally:
        print(f"Total URLs processed: {len(processed_url)}")
        reader.stop_monitoring()

if __name__=="__main__":
    main()