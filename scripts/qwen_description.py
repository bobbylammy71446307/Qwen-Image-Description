import pytz
from qwen_llm import qwen_llm
from PIL import Image, ImageDraw, ImageFont


class QwenDescriber:
    """
    Simplified class for generating security surveillance descriptions and annotating images
    Uses direct object detection without pre-filtering
    Supports both English and Chinese languages
    """

    def __init__(self,
                #  detection_objects= ["unattended object", "pets that are not leashed", "water puddle", "unclosed doors", "bicycle", "violent actions"],
                 detection_objects= ["alarm light","industrial valve"],
                 prompt_file="prompt_english.txt",
                 language="english",
                 text_alignment="left"):
        self.describer = qwen_llm("image description")
        self.detector = qwen_llm("detector",detection_list=detection_objects)
        self.detection_objects = detection_objects
        self.prompt_file = prompt_file
        self.language = language.lower()
        self.text_alignment = text_alignment.lower()  # "left" or "right"
        self.security_prompt = self._load_prompt()
        self.font_header = None
        self.font_body = None
        self._load_fonts()
        self.unique_labels = set()
        self.ai_text = ""  # Store full text description for POST data

    def _load_prompt(self):
        """Load the security observation prompt from file"""
        try:
            with open(self.prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
            print(f"[INFO] Loaded prompt from {self.prompt_file}")
            return prompt
        except FileNotFoundError:
            print(f"[WARNING] Prompt file {self.prompt_file} not found, using empty prompt")
            return ""
        except Exception as e:
            print(f"[ERROR] Failed to load prompt file: {e}")
            raise

    def _load_fonts(self):
        """Load fonts for image annotation"""
        import os

        if self.language == "chinese":
            # Load Chinese-compatible fonts
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
                        self.font_header = ImageFont.truetype(font_path, 32)
                        self.font_body = ImageFont.truetype(font_path, 26)
                        font_loaded = True
                        print(f"[INFO] Loaded Chinese fonts: {font_path}")
                        break
                except Exception:
                    continue

            if not font_loaded:
                print("[WARNING] No suitable Chinese font found, using PIL default")
                print("[INFO] To fix this, install fonts: apt-get install fonts-noto-cjk fonts-wqy-zenhei")
                self.font_header = ImageFont.load_default()
                self.font_body = ImageFont.load_default()
        else:
            # Load English fonts
            try:
                self.font_header = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/Trebuchet_MS_Bold.ttf", 32)
            except:
                try:
                    self.font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
                except:
                    self.font_header = ImageFont.load_default()

            try:
                self.font_body = ImageFont.truetype("/usr/share/fonts/truetype/Fjord.ttf", 28)
            except:
                try:
                    self.font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
                except:
                    self.font_body = ImageFont.load_default()

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
    def wrap_text_lines(description, suggestion, max_chars=60, language="english"):
        """
        Create formatted text lines with description and suggestion
        Args:
            description: Description text
            suggestion: Suggestion text
            max_chars: Maximum characters per line for wrapping
            language: "english" or "chinese"
        Returns:
            Array: ["Description:", "- (description text)", "Suggestion:", "- (suggestion text)"]
        """
        # Adjust max_chars for Chinese (characters are wider)
        if language == "chinese":
            max_chars = 30

        wrapped = []

        # Headers based on language
        desc_header = "描述:" if language == "chinese" else "Description:"
        sugg_header = "建議:" if language == "chinese" else "Suggestion:"

        # Add Description section
        wrapped.append(desc_header)
        # Wrap description text with bullet point
        if description:
            # Capitalize first letter of description (English only)
            description = description.strip()
            if description and language == "english":
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
        wrapped.append(sugg_header)
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


    def process_and_annotate(self, image_path, output_path=None):
        """
        Process an image and generate annotated version with security observations
        Uses simple direct detection without pre-filtering
        Args:
            image_path: Path to the image (local file or HTTP URL)
            output_path: Optional output path for annotated image
        Returns:
            Path to annotated image
        """
        try:
            print(f"[DEBUG] Starting image processing: {image_path}")

            # Get initial security observations
            print("[DEBUG] Step 1: Getting security observations...")
            self.describer.action(
                question=self.security_prompt,
                image=image_path
            )

            response = self.describer.response
            points = self.extract_points(response)
            print(f"[DEBUG] Extracted points: {points}")

            print("[DEBUG] Step 2: Checking for specific objects...")

            self.detected_obj_list = []

            # Translate detection objects to Chinese if needed
            detection_objects_for_query = self.detection_objects
            if self.language == "chinese":
                objects_chinese = {
                    "pets": "寵物",
                    "rubbish": "垃圾",
                    "water puddle": "水坑",
                    "smoker": "吸煙者",
                    "pet not leashed": "寵物未牽繩",
                    "pets that are not leashed": "寵物未牽繩",
                    "person on skateboard": "滑板人士",
                    "person on bicycle": "騎自行車人士",
                    "person playing ball game": "打球人士",
                    "person injured": "受傷人士",
                    "unattended object": "無人看管物品",
                    "unclosed doors": "未關門",
                    "bicycle": "自行車",
                    "violent actions": "暴力行為"
                }
                detection_objects_for_query = [objects_chinese.get(obj, obj) for obj in self.detection_objects]

            # Use simple pre-filtering prompt to check if objects exist
            if self.language == "chinese":
                filter_question = f"圖像中是否存在以下任何物體？{detection_objects_for_query} 如果存在，請列出存在的物體。只返回存在的物體列表，格式：['物體1', '物體2'] 如果沒有則返回 []"
            else:
                filter_question = f"Are any of the following objects present in the image? {detection_objects_for_query} If yes, list which ones exist. Return only a list of existing objects in format: ['object1', 'object2'] or [] if none"

            self.describer.action(image=image_path, question=filter_question)

            # Parse the filtered list
            filtered_objects = []
            try:
                import ast
                filter_response = self.describer.response.strip()
                print(f"[DEBUG] Filter response: {filter_response}")

                # Extract list from response
                if '[' in filter_response and ']' in filter_response:
                    start_idx = filter_response.find('[')
                    end_idx = filter_response.rfind(']') + 1
                    list_str = filter_response[start_idx:end_idx]
                    filtered_objects = ast.literal_eval(list_str)
                    print(f"[DEBUG] Filtered objects that exist in image: {filtered_objects}")
                else:
                    print("[WARNING] No list found in response")
                    filtered_objects = []
            except Exception as e:
                print(f"[WARNING] Failed to parse filtered objects: {e}")
                filtered_objects = []

            # Only run detector if there are objects to detect
            if filtered_objects:
                print(f"[DEBUG] Step 3: Running detector on filtered objects: {filtered_objects}")
                # Update detector with filtered list
                self.detector.detection_list = filtered_objects
                self.detector.action(image=image_path)
            else:
                print("[DEBUG] No objects from detection list found in image, skipping detector")
                self.detector.response = "[]"  # Empty detection result

            # Parse detector response (expects JSON array format)
            import json
            detection_img = None  # Store image with bounding boxes if detections exist
            try:
                # Extract JSON from detector response
                clean_json_str = self.detector.extract_json_from_string(self.detector.response)
                detections = json.loads(clean_json_str)
                print(f"[DEBUG] Detector response: {detections}")

                # If there are detections, draw bounding boxes on the image
                if detections and len(detections) > 0:
                    print(f"[DEBUG] Drawing {len(detections)} bounding boxes...")
                    # Draw bounding boxes on image (modifies image in place)
                    annotated_img_bytes = self.detector.draw_normalized_bounding_boxes(
                        image_path,
                        self.detector.response
                    )

                    # Update image in memory instead of saving to temp path
                    # This preserves the original image_path for final save naming
                    from io import BytesIO
                    from PIL import Image as PIL_Image
                    detection_img = PIL_Image.open(BytesIO(annotated_img_bytes))
                    print(f"[DEBUG] Loaded annotated image with bounding boxes into memory")

                    # Add detected objects to points as priors (one point per unique label)
                    self.unique_labels = set()
                    for detection in detections:
                        if "label" in detection and "bbox_2d" in detection:
                            label = detection["label"]
                            if label not in self.unique_labels:
                                self.unique_labels.add(label)

                                # Simplify label for display
                                # Map detailed descriptions to concise labels
                                if "bag" in label.lower() and ("unattended" in label.lower() or "alone" in label.lower() or "no person" in label.lower()):
                                    simplified_label = "unattended bag"
                                elif "person" in label.lower() and ("slot machine" in label.lower() or "arcade" in label.lower()) and ("not playing" in label.lower() or "idle" in label.lower() or "not engaging" in label.lower()):
                                    simplified_label = "person occupying a slot machine"
                                else:
                                    # Fallback: use the original label if no pattern matches
                                    simplified_label = label

                                if self.language == "chinese":
                                    points.append([f"檢測到 {simplified_label}", "否"])
                                else:
                                    points.append([f"{simplified_label} detected", "no"])
                    print(f"[DEBUG] Added {len(self.unique_labels)} unique detection labels to points")
                else:
                    print("[DEBUG] No detections found")

            except json.JSONDecodeError as e:
                print(f"[WARNING] Failed to parse detector response as JSON: {e}")
                print(f"[DEBUG] Detector response was: {self.detector.response}")
            except Exception as e:
                print(f"[WARNING] Error processing detections: {e}")
                import traceback
                traceback.print_exc()

            # Filter out any malformed points (safety check)
            points = [p for p in points if len(p) >= 2]
            print(f"[DEBUG] Total points after filtering: {len(points)}")

            # Sort points: items with "no"/"否" in position [1] come first
            no_values = ['no', '否'] if self.language == "chinese" else ['no']
            points.sort(key=lambda x: 0 if x[1].replace(' ', '').replace(".","").lower() in no_values else 1)

            print(f"[DEBUG] Step 4: Generating annotated image with {len(points)} observations...")
            # Generate annotated image, passing pre-loaded detection image if available
            annotated_path = self._annotate_image(image_path, points, output_path, detection_img)

            print(f"[DEBUG] Successfully completed processing. Output: {annotated_path}")
            return annotated_path

        except Exception as e:
            print(f"[ERROR] Failed to process image {image_path}: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _annotate_image(self, image_path, points, output_path=None, preloaded_img=None):
        """
        Annotate image with observations and suggestions
        Args:
            image_path: Path to input image (used for naming even if preloaded_img is provided)
            points: List of observation points
            output_path: Optional output path
            preloaded_img: Optional pre-loaded PIL Image (e.g., with bounding boxes already drawn)
        Returns:
            Path to annotated image
        """
        # Load the image
        print(f"[DEBUG] Loading image...")
        if preloaded_img is not None:
            print(f"[DEBUG] Using pre-loaded image with detections...")
            img = preloaded_img
        elif image_path.startswith(('http://', 'https://')):
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
        img_width, img_height = img.size
        draw = ImageDraw.Draw(img)

        # Track the vertical position for stacking text boxes
        current_y_position = 60

        # Set initial x position based on alignment
        # For right alignment, we'll calculate after knowing box width
        if self.text_alignment == "right":
            current_x_position = None  # Will be calculated per box
        else:  # left alignment (default)
            current_x_position = 60
        description_only_column_count = 0
        row_max_height = 0

        # Initialize AI text collection
        self.ai_text = ""
        text_lines = []

        # Define no/yes values based on language
        no_values = ['no', '否']
        yes_values = ['yes', '是']

        for point in points:
            is_description_only = point[1].replace(" ", "").replace(".","").lower() in no_values

            if point[1].replace(" ", "").replace(".","").lower() in yes_values:
                # For items with suggestions, complete any ongoing description-only row first
                if description_only_column_count > 0:
                    current_y_position = current_y_position + row_max_height + 80
                    current_x_position = 60
                    description_only_column_count = 0
                    row_max_height = 0

                # Generate suggestion based on language
                if self.language == "chinese":
                    suggestion_question = f"對於問題 {point[0]} 給出預防措施建議,以最少的點形式回應: -... , -..., -... 給出最少的描述和建議,每個建議不超過 5 個字,只給出**1**個建議點,資訊最少"
                else:
                    suggestion_question = f"give precaution actions suggestions for the problem {point[0]} response in minimal point form: -... , -..., -... give minimal description and suggestions only with no more than 5 words, give only **1** suggestion point with minimal information"

                self.describer.action(
                    question=suggestion_question,
                    image=image_path
                )
                response_text = self.describer.response
                wrapped_lines = self.wrap_text_lines(point[0], response_text, max_chars=40, language=self.language)

            else:
                description = point[0][0].upper() + point[0][1:] if point[0] else point[0]
                if self.language == "chinese":
                    wrapped_lines = ["描述:", f"- {description}"]
                else:
                    wrapped_lines = ["Description:", f"- {description}"]

            # Collect text for AI text output
            text_lines.extend(wrapped_lines)
            text_lines.append("")  # Add empty line between observations

            # Calculate dimensions first (needed for positioning)
            line_height = 42
            max_width = 0
            total_height = 0

            # Calculate box dimensions
            header_keywords = ["Description:", "Suggestion:", "描述:", "建議:"]
            temp_y = current_y_position
            for line in wrapped_lines:
                current_font = self.font_header if any(line.startswith(kw) for kw in header_keywords) else self.font_body
                # Use a temporary position for measurement
                bbox = draw.textbbox((0, temp_y), line, font=current_font)
                width = bbox[2] - bbox[0]
                max_width = max(max_width, width)
                total_height += line_height
                temp_y += line_height

            # Calculate x position based on alignment
            if self.text_alignment == "right":
                # Right-align: position from right edge
                text_x = img_width - max_width - 60 - 70  # 60 margin + 70 for padding (35*2)
            else:  # left alignment
                text_x = current_x_position if current_x_position is not None else 60

            # Set text position
            text_position = (text_x, current_y_position)
            y_offset = text_position[1]

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
                current_font = self.font_header if any(line.startswith(kw) for kw in header_keywords) else self.font_body
                draw.text((text_position[0], y_offset), line, fill=(255, 255, 255), font=current_font)
                y_offset += line_height

            # Update position for next text box
            if is_description_only:
                description_only_column_count += 1
                row_max_height = max(row_max_height, total_height)

                # For right alignment, always stack vertically (no columns)
                if self.text_alignment == "right":
                    # Stack all boxes vertically with reduced spacing
                    current_y_position = text_position[1] + total_height + 20 + 35 + 40
                    current_x_position = None  # Will recalculate
                    description_only_column_count = 0
                    row_max_height = 0
                elif description_only_column_count >= 2:
                    # Left alignment: multi-column layout
                    current_y_position = current_y_position + row_max_height + 80
                    current_x_position = 60
                    description_only_column_count = 0
                    row_max_height = 0
                else:
                    # Left alignment: move to next column
                    current_x_position = current_x_position + max_width + 100
            else:
                # Move to next position accounting for:
                # - total_height (text)
                # - 20 (bottom padding of current box)
                # - 35 (top padding of next box)
                # - 40 (spacing between boxes - reduced from 80)
                current_y_position = text_position[1] + total_height + 20 + 35 + 40
                # Reset x position based on alignment
                if self.text_alignment == "right":
                    current_x_position = None  # Will recalculate
                else:
                    current_x_position = 60

        # Generate output path if not provided
        if output_path is None:
            from pathlib import Path
            from datetime import datetime

            # Get current timestamp
            now = datetime.now(pytz.timezone('Asia/Hong_Kong'))
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

        # Join all collected text lines into ai_text
        self.ai_text = "\n".join(text_lines)
        print(f"[DEBUG] AI text collected: {len(self.ai_text)} characters")

        return return_path


if __name__ == "__main__":
    # Trial run with casino image
    print("[INFO] Starting trial run with simple detector...")

    describer = QwenDescriber(
        detection_objects=[
            "bag placed alone on floor or seat with no person nearby within arm's reach",
            "person seated in front of slot machine but not playing the slot machine"
        ],
        prompt_file="prompt_english.txt",
        language="english"
    )

    # Process the image
    image_path = "https://hkpic1.aimo.tech/securityClockOut/20251210/as00213/15/20251210150950218-as00213-%E5%B7%A6.jpg"

    try:
        output_path = describer.process_and_annotate(image_path)
        print(f"[SUCCESS] Trial run completed! Annotated image saved to: {output_path}")
    except Exception as e:
        print(f"[ERROR] Trial run failed: {e}")
        import traceback
        traceback.print_exc()
