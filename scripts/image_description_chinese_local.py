#!/usr/bin/env python3

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import pytz
from qwen_description_chinese import QwenDescriber_chinese


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

  # Process with custom detection objects
  python image_description_chinese_local.py input.jpg -d "塑膠袋" "煙頭" "積水"

  # Use custom prompt file
  python image_description_chinese_local.py input.jpg -p custom_prompt.txt
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

    args = parser.parse_args()

    # Get list of image files to process
    image_files = get_image_files(args.input)

    if not image_files:
        print("[ERROR] No valid image files found")
        sys.exit(1)

    print(f"[INFO] Processing {len(image_files)} image(s)")
    if args.verbose:
        print(f"[INFO] Detection objects: {args.detection_objects}")
        print(f"[INFO] Prompt file: {args.prompt_file}")

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
    output_paths = []

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

    if output_paths:
        print(f"\nOutput files:")
        for path in output_paths:
            print(f"  - {path}")

    # Exit with appropriate code
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
