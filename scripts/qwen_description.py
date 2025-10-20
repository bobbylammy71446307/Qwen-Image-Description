from qwen_llm import qwen_llm
from PIL import Image, ImageDraw, ImageFont


class QwenDescriber:
    """
    Class for generating security surveillance descriptions and annotating images
    """

    def __init__(self, detection_objects= ["plastic bag", "plastic bottle", "cardboard", "water puddle", "smoker"]
):
        """
        Initialize the describer
        Args:
            detection_objects: List of objects to detect (e.g., ["plastic bag", "water puddle"])
        """
        self.describer = qwen_llm("image description")
        self.chatter = qwen_llm("chatter")
        self.detection_objects = detection_objects or ["plastic bag", "plastic bottle", "cardboard", "water puddle", "smoker"]
        self.font_header = None
        self.font_body = None
        self._load_fonts()

    def _load_fonts(self):
        """Load fonts for image annotation"""
        # Try to load header font
        try:
            self.font_header = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/Trebuchet_MS_Bold.ttf", 32)
        except:
            try:
                self.font_header = ImageFont.truetype("trebucbd.ttf", 32)
            except:
                try:
                    self.font_header = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/trebucbd.ttf", 32)
                except:
                    self.font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)

        # Try to load body font
        try:
            self.font_body = ImageFont.truetype("/usr/share/fonts/truetype/Fjord.ttf", 28)
        except:
            try:
                self.font_body = ImageFont.truetype("Fjord.ttf", 28)
            except:
                try:
                    self.font_body = ImageFont.truetype("FjordOne-Regular.ttf", 28)
                except:
                    self.font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)

    @staticmethod
    def extract_points(text):
        """Extract bullet points into separate variables"""
        points = []
        raw_lines = text.split('\n')
        for line in raw_lines:
            line = line.strip()
            if line:  # Skip empty lines
                parts = line.split(',')
                # Ensure we have at least 2 parts (description and status)
                if len(parts) >= 2:
                    points.append([parts[0].strip(), parts[1].strip()])
                else:
                    # If no comma, treat entire line as description with "no" status
                    print(f"[DEBUG] Line without comma, treating as 'no' status: {line}")
                    points.append([line, "no"])
        return points

    @staticmethod
    def wrap_text_lines(description, suggestion, max_chars=60):
        """
        Create formatted text lines with description and suggestion
        Args:
            description: Description text
            suggestion: Suggestion text
            max_chars: Maximum characters per line for wrapping
        Returns:
            Array: ["Description:", "- (description text)", "Suggestion:", "- (suggestion text)"]
        """
        wrapped = []

        # Add Description section
        wrapped.append("Description:")
        # Wrap description text with bullet point
        if description:
            # Capitalize first letter of description
            description = description.strip()
            if description:
                description = description[0].upper() + description[1:]
            words = description.split()
            current_line = "- "
            indent = "  "
            for word in words:
                test_line = current_line + word + ' '
                if len(test_line.strip()) > max_chars and current_line != "- ":
                    wrapped.append(current_line.rstrip())
                    current_line = indent + word + ' '
                else:
                    current_line = test_line
            if current_line.strip() != "-":
                wrapped.append(current_line.rstrip())

        # Add Suggestion section
        wrapped.append("Suggestion:")
        # Wrap suggestion text with bullet points
        suggestion_list = suggestion.split('\n')
        for item in suggestion_list:
            item = item.strip()
            if item:
                # If it already starts with -, use it as is but wrap it
                if item.startswith('-'):
                    text = item[1:].strip()
                    words = text.split()
                    current_line = "- "
                    indent = "  "
                    for word in words:
                        test_line = current_line + word + ' '
                        if len(test_line.strip()) > max_chars and current_line != "- ":
                            wrapped.append(current_line.rstrip())
                            current_line = indent + word + ' '
                        else:
                            current_line = test_line
                    if current_line.strip() != "-":
                        wrapped.append(current_line.rstrip())
                else:
                    # Add bullet point and wrap
                    words = item.split()
                    current_line = "- "
                    indent = "  "
                    for word in words:
                        test_line = current_line + word + ' '
                        if len(test_line.strip()) > max_chars and current_line != "- ":
                            wrapped.append(current_line.rstrip())
                            current_line = indent + word + ' '
                        else:
                            current_line = test_line
                    if current_line.strip() != "-":
                        wrapped.append(current_line.rstrip())

        return wrapped
    def _filter_security_response(self, response_str: str) -> str:
        """
        Deterministic local filtering to avoid contradictory lines produced by the LLM.
        - If any line contains 'not all' (fluorescent lamps not all lit), keep that line and remove any
          'all fluorescent ...' lines to avoid contradiction.
        - Normalize any remaining 'all fluorescent' lines to the exact form:
            "All fluorescent lamps are lit up, no"
        - Remove lines that indicate "no emergency exit" (they should not appear).
        - Remove lines that start with "no visible" or contain "no visible".
        - If gate is closed, replace the line with "no".
        - Keep all other lines unchanged.
        """
        if not response_str:
            return ""
        raw_lines = [l.strip() for l in response_str.splitlines() if l.strip()]
        if not raw_lines:
            return ""
        # Detect presence of an explicit "not all" fluorescent statement
        has_not_all = any("not all" in l.lower() or "not all lit" in l.lower() for l in raw_lines)
        out_lines = []
        for line in raw_lines:
            low = line.lower()
            # Drop explicit "no emergency exit" lines
            if "no emergency exit" in low or "no emergency exit door" in low:
                continue
            # Drop lines containing "no visible"
            if "no visible" in low:
                continue
            # If gate is closed, replace with "no"
            if "gate" in low and "closed" in low:
                out_lines.append("no")
                continue
            # If line explicitly states fluorescent lamps are NOT all lit, keep it exactly
            if "not all" in low or "not all lit" in low:
                out_lines.append(line)
                continue
            # Normalize any "all fluorescent/all lit" statements
            if ("all fluorescent" in low) or ("all lit" in low) or ("all lit up" in low):
                # If we already have a "not all" line, skip this contradictory "all" line
                if has_not_all:
                    continue
                out_lines.append("All fluorescent lamps are lit up, no")
                continue
            # Keep any other lines unchanged
            out_lines.append(line)
        return "\n".join(out_lines)
    
    def process_and_annotate(self, image_path, output_path=None):
        """
        Process an image and generate annotated version with security observations
        Args:
            image_path: Path to the image (local file or HTTP URL)
            output_path: Optional output path for annotated image
        Returns:
            Tuple of (points, output_path) where points is list of observations
        """
        try:
            print(f"[DEBUG] Starting image processing: {image_path}")

            # Get initial security observations
            print("[DEBUG] Step 1: Getting security observations...")
            # self.describer.action(question="you are a security guard and performing daily surveillance," \
            #                                "check whether **ALL** fluorescent lamps are lit up if lamp is present" \
            #                                "check is there a highly visible emergency exit door, if yes is it closed?" \
            #                                "also get 2 more distinct observations from the image which a security guard should take note of" \
            #                                "for each observation whether the observation requires immediate handling as yes or no only" \
            #                                "do not output the above observation thought process" \
            #                                "Answer in format: ... , ... with observation coming first and state coming next",
            #                        image=image_path
            #                    )
            self.describer.action(
                question=(
                    "You are a security guard of a factory reviewing the image. Follow instructions exactly and output only the "
                    "required observations — no explanation, no reasoning, no extra text.\n\n"
                    "1) Check gate closure status: if any gate is visible, report whether gate is closed. "
                    "If none are visible, state \"No gate visible\".\n"
                    "2) Provide exactly two additional distinct security-relevant observations (e.g., persons, "
                    "obstructions, water on floor, smoke, broken glass). Do not repeat observations and keep each one short.\n"
                    "3) For every observation, append whether it requires immediate handling: \"yes\" or \"no\" (only yes/no).\n"
                    "4) Output format: three separate lines, each line exactly: <observation>, <yes|no>\n"
                    "- use minimal phrasing (no full sentences, no labels, no numbering).\n"
                    "- if an item cannot be determined from the image, use \"Not visible\" as the observation and \"no\" as the state.\n\n"
                    "Example:\n"
                    "Fluorescent lamps not all lit, yes\n"
                    "Emergency exit door closed, no\n"
                    "Unattended bag by bench, yes\n"
                    "Wet floor near entrance, yes"
                ),
                image=image_path
            )

            response = self.describer.response
            print(f"[DEBUG] Initial response: {response}")

            print("[DEBUG] Step 2: Filtering response...")
            filtered = self._filter_security_response(response)
            print(f"[DEBUG] Filtered response:\\n{filtered}")
            points = self.extract_points(filtered)
            print(f"[DEBUG] Extracted points after filtering: {points}")

            print("[DEBUG] Step 3: Checking for specific objects...")
            # Check for specific objects
            self.describer.action(
                question=f"Are there {self.detection_objects} in the photo?" \
                         "Example answer format:\n" \
                         "rubbish, no\n" \
                         "water puddle, no" \
                         "smoker , no",
                image=image_path
            )
            obj_detection_list = self.extract_points(self.describer.response)
            print(f"[DEBUG] Object detection results: {obj_detection_list}")

            # Add visible objects to points
            for obj in obj_detection_list:
                if len(obj) >= 2 and obj[1].replace(" ", "").replace(".","").lower() == "yes":
                    points.append([f"{obj[0]} detected", "no"])

            # Filter out any malformed points (safety check)
            points = [p for p in points if len(p) >= 2]
            print(f"[DEBUG] Total points after filtering: {len(points)}")

            # Sort points: items with "no" in position [1] come first
            points.sort(key=lambda x: 0 if x[1].replace(' ', '').replace(".","").lower() == 'no' else 1)

            print(f"[DEBUG] Step 4: Generating annotated image with {len(points)} observations...")
            # Generate annotated image
            annotated_path = self._annotate_image(image_path, points, output_path)

            print(f"[DEBUG] Successfully completed processing. Output: {annotated_path}")
            return annotated_path

        except Exception as e:
            print(f"[ERROR] Failed to process image {image_path}: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _annotate_image(self, image_path, points, output_path=None):
        """
        Annotate image with observations and suggestions
        Args:
            image_path: Path to input image
            points: List of observation points
            output_path: Optional output path
        Returns:
            Path to annotated image
        """
        print(f"[DEBUG] _annotate_image called with {len(points)} points")
        print(f"[DEBUG] Image path: {image_path}")
        print(f"[DEBUG] Points: {points}")

        # Load the image
        print(f"[DEBUG] Loading image...")
        if image_path.startswith(('http://', 'https://')):
            import requests
            from io import BytesIO
            print(f"[DEBUG] Downloading image from URL...")
            response = requests.get(image_path)
            print(f"[DEBUG] Download complete. Status: {response.status_code}")
            img = Image.open(BytesIO(response.content))
        else:
            print(f"[DEBUG] Loading local image file...")
            img = Image.open(image_path)

        print(f"[DEBUG] Image loaded. Size: {img.size}")
        draw = ImageDraw.Draw(img)

        # Track the vertical position for stacking text boxes
        current_y_position = 60
        current_x_position = 60
        description_only_column_count = 0
        row_max_height = 0

        for point in points:
            is_description_only = point[1].replace(" ", "").replace(".","").lower() == 'no'

            if point[1].replace(" ", "").replace(".","").lower() == 'yes':
                # For items with suggestions, complete any ongoing description-only row first
                if description_only_column_count > 0:
                    current_y_position = current_y_position + row_max_height + 80
                    current_x_position = 60
                    description_only_column_count = 0
                    row_max_height = 0
                print("ask_4")
                self.describer.action(
                    question=f"give precaution actions suggestions for the problem {point[0]} " \
                             "response in minimal point form: -... , -..., -... " \
                             "give minimal description and suggestions only with no more than 5 words, " \
                             "give only **1** suggestion point with minimal information",
                    image=image_path
                )
                response_text = self.describer.response
                wrapped_lines = self.wrap_text_lines(point[0], response_text, max_chars=40)

            else:
                description = point[0][0].upper() + point[0][1:]
                wrapped_lines = ["Description:", f"- {description}"]

            # Add text with background for readability
            text_position = (current_x_position, current_y_position)
            line_height = 42
            y_offset = text_position[1]
            max_width = 0
            total_height = 0

            for line in wrapped_lines:
                current_font = self.font_header if line.startswith("Description:") or line.startswith("Suggestion:") else self.font_body
                bbox = draw.textbbox((text_position[0], y_offset), line, font=current_font)
                width = bbox[2] - bbox[0]
                max_width = max(max_width, width)
                total_height += line_height
                y_offset += line_height

            # Draw background rectangle
            background_bbox = (
                text_position[0] - 35,
                text_position[1] - 35,
                text_position[0] + max_width + 35,
                text_position[1] + total_height + 20
            )

            # Create a semi-transparent overlay
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rounded_rectangle(
                background_bbox,
                radius=15,
                fill=(0, 0, 0, 150)
            )

            # Composite the overlay onto the original image
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)

            draw = ImageDraw.Draw(img)

            # Draw the text in white
            y_offset = text_position[1]
            for line in wrapped_lines:
                current_font = self.font_header if line.startswith("Description:") or line.startswith("Suggestion:") else self.font_body
                draw.text((text_position[0], y_offset), line, fill=(255, 255, 255), font=current_font)
                y_offset += line_height

            # Update position for next text box
            if is_description_only:
                description_only_column_count += 1
                row_max_height = max(row_max_height, total_height)

                if description_only_column_count >= 2:
                    current_y_position = current_y_position + row_max_height + 80
                    current_x_position = 60
                    description_only_column_count = 0
                    row_max_height = 0
                else:
                    current_x_position = current_x_position + max_width + 100
            else:
                current_y_position = text_position[1] + total_height + 80
                current_x_position = 60

        # Generate output path if not provided
        if output_path is None:
            from pathlib import Path
            from datetime import datetime

            # Get current timestamp
            now = datetime.now()
            year = now.strftime('%Y')
            month = now.strftime('%m')
            day = now.strftime('%d')
            hour = now.strftime('%H')

            # Create hierarchical directory structure: output/yyyy/mm/dd/hh/images
            images_dir = Path("output") / year / month / day / hour / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            if image_path.startswith(('http://', 'https://')):
                # For URLs, extract filename from URL or use timestamp
                url_parts = image_path.split('/')
                filename = url_parts[-1] if url_parts[-1] else "image"
                # Remove query parameters if any
                filename = filename.split('?')[0]
                # If no extension or no proper filename, use timestamp
                if '.' not in filename or len(filename) < 5:
                    timestamp = now.strftime('%Y%m%d_%H%M%S')
                    filename = f"image_{timestamp}.jpg"
                # Add _annotated before extension
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    output_filename = f"{name_parts[0]}_annotated.{name_parts[1]}"
                else:
                    output_filename = f"{filename}_annotated.jpg"
            else:
                # For local files, extract filename
                filename = Path(image_path).name
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    output_filename = f"{name_parts[0]}_annotated.{name_parts[1]}"
                else:
                    output_filename = f"{filename}_annotated.jpg"

            # Save to output directory
            output_path = str(images_dir / output_filename)

            print(f"[DEBUG] Output path set to: {output_path}")
            print(f"[DEBUG] Directory exists: {images_dir.exists()}")

            # Return path in AI format
            return_path = f"AI/{year}/{month}/{day}/{hour}/images/{output_filename}"
        else:
            return_path = output_path
            print(f"[DEBUG] Using provided output path: {output_path}")

        # Convert back to RGB and save
        print(f"[DEBUG] Converting image to RGB...")
        img = img.convert('RGB')
        print(f"[DEBUG] Saving image to: {output_path}")

        try:
            img.save(output_path)
            print(f"[SUCCESS] Image saved to {output_path}")

            # Verify file was created
            from pathlib import Path
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                print(f"[SUCCESS] File verified. Size: {file_size} bytes")
            else:
                print(f"[WARNING] File was not created at {output_path}")
        except Exception as save_error:
            print(f"[ERROR] Failed to save image: {save_error}")
            import traceback
            traceback.print_exc()
            raise

        return return_path


if __name__ == "__main__":
    # Example usage of the QwenDescriber class
    image = "https://hkpic1.aimo.tech/securityClockOut/20251016/as00107/23/20251016233359219-as00107-%E5%8F%B3.jpg"  # Local image path

    # Create describer instance with custom detection objects (optional)
    detection_objects = ["plastic bag", "plastic bottle", "cardboard", "water puddle", "smoker"]
    describer = QwenDescriber(detection_objects=detection_objects)

    # Process and annotate the image
    output_path = describer.process_and_annotate(image)