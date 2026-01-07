#!/usr/bin/env python3
"""
Standalone script to annotate images with text boxes
Similar to the annotation method used in qwen_description.py
"""

import sys
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os


class ImageAnnotator:
    """Simple image annotator for adding text boxes to images"""

    def __init__(self, language="english"):
        """
        Initialize the annotator
        Args:
            language: "english" or "chinese" (determines fonts)
        """
        self.language = language.lower()
        self.font_header = None
        self.font_body = None
        self._load_fonts()

    def _load_fonts(self):
        """Load fonts for image annotation"""
        if self.language == "chinese":
            # Load Chinese-compatible fonts (same as qwen_description.py)
            chinese_font_paths = [
                # Traditional Chinese fonts
                "/usr/share/fonts/truetype/arphic/uming.ttc",
                "/usr/share/fonts/truetype/arphic/ukai.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansTC-Bold.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansTC-Bold.ttf",
                # CJK fonts
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                # WenQuanYi fonts
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                # Fallback
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ]

            font_loaded = False
            for font_path in chinese_font_paths:
                try:
                    if os.path.exists(font_path):
                        self.font_header = ImageFont.truetype(font_path, 48)
                        self.font_body = ImageFont.truetype(font_path, 40)
                        font_loaded = True
                        print(f"[INFO] Loaded Chinese fonts: {font_path} (header:48px, body:40px)")
                        break
                except Exception:
                    continue

            if not font_loaded:
                print("[WARNING] No suitable Chinese font found, using PIL default")
                print("[INFO] To fix this, install fonts: apt-get install fonts-noto-cjk fonts-wqy-zenhei")
                self.font_header = ImageFont.load_default()
                self.font_body = ImageFont.load_default()
        else:
            # Load English fonts (same as qwen_description.py)
            try:
                self.font_header = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/Trebuchet_MS_Bold.ttf", 48)
                self.font_body = ImageFont.truetype("/usr/share/fonts/truetype/Fjord.ttf", 40)
                print(f"[INFO] Loaded English fonts: Trebuchet_MS_Bold (header:48px), Fjord (body:40px)")
            except:
                try:
                    self.font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
                    self.font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
                    print(f"[INFO] Loaded English fonts: DejaVuSans-Bold (header:48px), DejaVuSans (body:40px)")
                except:
                    self.font_header = ImageFont.load_default()
                    self.font_body = ImageFont.load_default()
                    print(f"[WARNING] No suitable English font found, using PIL default (very small!)")

    def annotate_image(self, image_path, text_boxes, output_path=None, auto_layout=True):
        """
        Annotate an image with text boxes

        Args:
            image_path: Path to input image (local file or URL)
            text_boxes: List of text boxes, each is a dict with:
                - 'text': str or list of str (lines of text)
                - 'position': tuple (x, y) for top-left corner (optional if auto_layout=True)
                - 'is_header': bool (optional, default False)
            output_path: Path to save annotated image (optional)
            auto_layout: If True, automatically position boxes (default: True)

        Returns:
            Path to saved annotated image
        """
        # Load image
        if image_path.startswith(('http://', 'https://')):
            import requests
            from io import BytesIO
            print(f"[INFO] Downloading image from URL...")
            response = requests.get(image_path)
            img = Image.open(BytesIO(response.content))
        else:
            print(f"[INFO] Loading local image file...")
            img = Image.open(image_path)

        print(f"[INFO] Image loaded. Size: {img.size}")
        img_width, img_height = img.size
        draw = ImageDraw.Draw(img)

        # Auto-layout parameters
        if auto_layout:
            current_y = 60
            current_x = 60

        # Process each text box
        for idx, box in enumerate(text_boxes):
            text = box.get('text', '')
            is_header = box.get('is_header', True)  # Default to True for header font

            # Determine position
            if 'position' in box and box['position'] is not None:
                position = box['position']
            elif auto_layout:
                # Auto-position the box
                position = (current_x, current_y)
            else:
                # Default position if no auto-layout and no position specified
                position = (60, 60 + idx * 150)

            # Convert text to list of lines if it's a string
            if isinstance(text, str):
                lines = text.split('\n')
            else:
                lines = text

            # Calculate dimensions
            line_height = 60  # Increased from 42 to match larger font
            y_offset = position[1]
            max_width = 0
            total_height = 0

            for line in lines:
                current_font = self.font_header if is_header else self.font_body
                bbox = draw.textbbox((position[0], y_offset), line, font=current_font)
                width = bbox[2] - bbox[0]
                max_width = max(max_width, width)
                total_height += line_height
                y_offset += line_height

            # Draw background rectangle with larger padding
            background_bbox = (
                position[0] - 40,  # Increased from 35
                position[1] - 40,  # Increased from 35
                position[0] + max_width + 40,  # Increased from 35
                position[1] + total_height + 25  # Increased from 20
            )

            # Create semi-transparent overlay
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rounded_rectangle(
                background_bbox,
                radius=15,
                fill=(0, 0, 0, 150)
            )

            # Composite overlay onto original image
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)

            # Draw the text in white
            y_offset = position[1]
            for line in lines:
                current_font = self.font_header if is_header else self.font_body
                draw.text((position[0], y_offset), line, fill=(255, 255, 255), font=current_font)
                y_offset += line_height

            # Update auto-layout positions for next box
            if auto_layout and (box.get('position') is None):
                # Stack boxes vertically - move from the current box's top position
                # We need: position[1] (top of box) + total_height (text) + spacing
                # Increased spacing from 80 to 120 for more space between boxes
                next_y = position[1] + total_height + 120
                print(f"[DEBUG] Box at Y={position[1]}, height={total_height}, next Y={next_y}")
                current_y = next_y

        # Generate output path if not provided
        if output_path is None:
            from datetime import datetime
            now = datetime.now()
            timestamp = now.strftime('%Y%m%d_%H%M%S')

            if image_path.startswith(('http://', 'https://')):
                output_filename = f"annotated_{timestamp}.jpg"
            else:
                input_filename = Path(image_path).stem
                output_filename = f"{input_filename}_annotated.jpg"

            output_path = f"output/{output_filename}"
            Path("output").mkdir(exist_ok=True)

        # Convert back to RGB and save
        img = img.convert('RGB')
        img.save(output_path)
        print(f"[SUCCESS] Annotated image saved to: {output_path}")

        return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Annotate images with text boxes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-layout (default): Automatically stacks text boxes vertically
  python annotate_image.py image.jpg -t "Alert 1" -t "Alert 2" -t "Alert 3"

  # Manual positioning: Specify exact positions
  python annotate_image.py image.jpg -t "Warning" -p 100 100 -t "Caution" -p 300 100

  # Mixed: Some positioned, others auto-stacked below
  python annotate_image.py image.jpg -t "Header" -p 50 50 -t "Auto positioned 1" -t "Auto positioned 2"

  # Chinese text with auto-layout
  python annotate_image.py image.jpg -t "警告1" -t "警告2" --language chinese

  # Disable auto-layout (requires position for each box)
  python annotate_image.py image.jpg -t "Text" -p 100 100 --no-auto-layout

  # Custom output file
  python annotate_image.py image.jpg -t "Alert" -o annotated_output.jpg
        """
    )

    parser.add_argument('input', help='Path to input image (local file or URL)')
    parser.add_argument('-t', '--text', action='append', help='Text to add (can be used multiple times)')
    parser.add_argument('-p', '--position', action='append', nargs=2, type=int, metavar=('X', 'Y'),
                       help='Position (x, y) for each text box (can be used multiple times, optional with auto-layout)')
    parser.add_argument('-o', '--output', help='Output file path (default: auto-generated)')
    parser.add_argument('--language', choices=['english', 'chinese'], default='english',
                       help='Language for font selection (default: english)')
    parser.add_argument('--no-auto-layout', action='store_true',
                       help='Disable automatic positioning (requires -p for each text box)')

    args = parser.parse_args()

    # Validate inputs
    if not args.text:
        print("[ERROR] At least one text box is required (use -t)")
        sys.exit(1)

    if args.no_auto_layout and (not args.position or len(args.position) != len(args.text)):
        print("[ERROR] With --no-auto-layout, you must provide position for each text box")
        sys.exit(1)

    if args.position and len(args.position) != len(args.text):
        print("[WARNING] Number of positions doesn't match number of text boxes. Auto-layout will be used for missing positions.")

    # Prepare text boxes
    text_boxes = []
    for i, text in enumerate(args.text):
        if args.position and i < len(args.position):
            position = tuple(args.position[i])
        else:
            # Let auto-layout handle it
            position = None

        text_boxes.append({
            'text': text,
            'position': position,
            'is_header': True
        })

    # Create annotator and process image
    annotator = ImageAnnotator(language=args.language)
    auto_layout = not args.no_auto_layout
    output_path = annotator.annotate_image(args.input, text_boxes, args.output, auto_layout=auto_layout)

    print(f"\n[COMPLETE] Annotation finished: {output_path}")


if __name__ == "__main__":
    main()
