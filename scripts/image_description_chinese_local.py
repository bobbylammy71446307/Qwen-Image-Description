#!/usr/bin/env python3

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import pytz
import yaml
import requests
from qwen_description_chinese import QwenDescriber_chinese


def load_config(config_path="./config.yaml"):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"[WARNING] Config file not found: {config_path}")
        return {}
    except yaml.YAMLError as e:
        print(f"[WARNING] Error parsing config file: {e}")
        return {}


def post_json_data(json_data, post_url, timeout=10):
    """Post JSON data to server"""
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(post_url, json=json_data, headers=headers, timeout=timeout)
        response.raise_for_status()
        print(f"[SUCCESS] Posted data to {post_url}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to post data to {post_url}: {e}")
        return False


def get_robot_pose():
    """Get robot pose (placeholder)"""
    pose = {
        "x": 0,
        "y": 0,
        "z": 0,
        "r": 0,
        "p": 0,
        "y": 0
    }
    return pose


def get_image_files(input_path):
    """
    Get list of image files from input path (file or directory)

    Args:
        input_path: Path to a single image file or directory

    Returns:
        List of image file paths
    """
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}

    path = Path(input_path)

    if not path.exists():
        print(f"[ERROR] Path does not exist: {input_path}")
        return []

    if path.is_file():
        # Single file
        if path.suffix.lower() in supported_formats:
            return [str(path)]
        else:
            print(f"[ERROR] Unsupported file format: {path.suffix}")
            return []

    elif path.is_dir():
        # Directory - get all image files
        image_files = []
        for ext in supported_formats:
            image_files.extend(path.glob(f"*{ext}"))
            image_files.extend(path.glob(f"*{ext.upper()}"))

        # Sort by name
        image_files = sorted([str(f) for f in image_files])
        print(f"[INFO] Found {len(image_files)} image files in {input_path}")
        return image_files

    else:
        print(f"[ERROR] Invalid path type: {input_path}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Process local images with Chinese security surveillance descriptions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single image
  python image_description_chinese_local.py input.jpg

  # Process all images in a directory
  python image_description_chinese_local.py images/

  # Process with custom output directory
  python image_description_chinese_local.py input.jpg -o results/

  # Process and post to server after each image
  python image_description_chinese_local.py images/ --post-to-server

  # Process with custom robot and camera names
  python image_description_chinese_local.py images/ --post-to-server --robot-name as00212 --camera-name front_camera

  # Process with custom detection objects
  python image_description_chinese_local.py input.jpg -d "塑膠袋" "煙頭" "積水"

  # Use custom prompt file
  python image_description_chinese_local.py input.jpg -p custom_prompt.txt

  # Enable verbose mode
  python image_description_chinese_local.py images/ -v --post-to-server
        """
    )

    parser.add_argument(
        'input',
        help='Path to input image file or directory containing images'
    )

    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory for annotated images (default: output/YYYY/MM/DD/HH/images/)',
        default=None
    )

    parser.add_argument(
        '-d', '--detection-objects',
        nargs='+',
        help='List of objects to detect (default: plastic bag, plastic bottle, cardboard, water puddle, smoker)',
        default=["plastic bag", "plastic bottle", "cardboard", "water puddle", "smoker"]
    )

    parser.add_argument(
        '-p', '--prompt-file',
        help='Path to prompt file (default: prompt_chinese.txt)',
        default='prompt_chinese.txt'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--post-to-server',
        action='store_true',
        help='Post results to server after each image is processed'
    )

    parser.add_argument(
        '--robot-name',
        help='Robot name for posting to server (default: from ROBOT_NAME env or "local")',
        default=os.getenv('ROBOT_NAME', 'local')
    )

    parser.add_argument(
        '--camera-name',
        help='Camera name for posting to server (default: "front_camera")',
        default='front_camera'
    )

    parser.add_argument(
        '--config',
        help='Path to config file (default: ./config.yaml)',
        default='./config.yaml'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    api_config = config.get("api", {})
    post_endpoint = api_config.get("post_endpoint", "http://post-server:8080/api/detections")
    api_timeout = api_config.get("timeout", 10)

    # Get list of image files to process
    image_files = get_image_files(args.input)

    if not image_files:
        print("[ERROR] No valid image files found")
        sys.exit(1)

    print(f"[INFO] Processing {len(image_files)} image(s)")
    if args.verbose:
        print(f"[INFO] Detection objects: {args.detection_objects}")
        print(f"[INFO] Prompt file: {args.prompt_file}")
        if args.post_to_server:
            print(f"[INFO] Will post to server: {post_endpoint}")
            print(f"[INFO] Robot name: {args.robot_name}")
            print(f"[INFO] Camera name: {args.camera_name}")

    # Initialize describer
    try:
        describer = QwenDescriber_chinese(
            detection_objects=args.detection_objects,
            prompt_file=args.prompt_file
        )
    except Exception as e:
        print(f"[ERROR] Failed to initialize describer: {e}")
        sys.exit(1)

    # Process each image
    processed_count = 0
    failed_count = 0
    posted_count = 0
    output_paths = []

    # Get timezone for timestamps
    hong_kong_tz = pytz.timezone('Asia/Hong_Kong')

    for idx, image_path in enumerate(image_files, 1):
        try:
            print(f"\n{'='*60}")
            print(f"[PROCESSING] ({idx}/{len(image_files)}) {image_path}")
            print(f"{'='*60}")

            # Determine output path if output directory is specified
            output_path = None
            if args.output_dir:
                output_dir = Path(args.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)

                # Get input filename and add _annotated suffix
                input_filename = Path(image_path).name
                name_parts = input_filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    output_filename = f"{name_parts[0]}_annotated.{name_parts[1]}"
                else:
                    output_filename = f"{input_filename}_annotated.jpg"

                output_path = str(output_dir / output_filename)

            # Process and annotate the image
            result_path = describer.process_and_annotate(image_path, output_path=output_path)
            output_paths.append(result_path)

            processed_count += 1
            print(f"[SUCCESS] Annotated image saved to: {result_path}")

            # Post to server if enabled
            if args.post_to_server:
                current_time = datetime.now(hong_kong_tz)
                post_data = {
                    "model_type": "ai_description",
                    "time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "robot": args.robot_name,
                    "camera": args.camera_name,
                    "pose": get_robot_pose(),
                    "image_path": [result_path]
                }

                if post_json_data(post_data, post_endpoint, timeout=api_timeout):
                    posted_count += 1
                    print(f"[SUCCESS] Posted result to server")
                else:
                    print(f"[WARNING] Failed to post result to server")

        except Exception as e:
            print(f"[ERROR] Failed to process {image_path}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            failed_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"[SUMMARY] Processing complete")
    print(f"{'='*60}")
    print(f"Total images: {len(image_files)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Failed: {failed_count}")
    if args.post_to_server:
        print(f"Posted to server: {posted_count}/{processed_count}")

    if output_paths:
        print(f"\nOutput files:")
        for path in output_paths:
            print(f"  - {path}")

    # Exit with appropriate code
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
