from qwen_llm import qwen_llm
from PIL import Image, ImageDraw, ImageFont


class QwenDescriber_chinese:
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
        """Load fonts for image annotation - Traditional Chinese compatible"""
        # Try to load Traditional Chinese fonts
        chinese_font_paths = [
            # Traditional Chinese fonts (優先)
            "/usr/share/fonts/truetype/arphic/uming.ttc",  # AR PL UMing (明體) - Traditional Chinese
            "/usr/share/fonts/truetype/arphic/ukai.ttc",  # AR PL UKai (楷體) - Traditional Chinese
            "/usr/share/fonts/opentype/noto/NotoSansTC-Bold.ttf",  # Noto Sans Traditional Chinese
            "/usr/share/fonts/opentype/noto/NotoSerifTC-Bold.ttf",  # Noto Serif Traditional Chinese
            "/usr/share/fonts/truetype/noto/NotoSansTC-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSerifTC-Bold.ttf",
            # CJK fonts (support both simplified and traditional)
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            # WenQuanYi fonts (support both)
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            # Fallback fonts
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/System/Library/Fonts/PingFang.ttc",  # macOS PingFang TC
            "C:\\Windows\\Fonts\\msjh.ttc",  # Windows Microsoft JhengHei (正黑體) - Traditional Chinese
            "C:\\Windows\\Fonts\\mingliu.ttc",  # Windows MingLiU (細明體) - Traditional Chinese
        ]

        # Try to load header font (bold, larger)
        font_loaded = False
        for font_path in chinese_font_paths:
            try:
                self.font_header = ImageFont.truetype(font_path, 32)
                font_loaded = True
                print(f"[DEBUG] Loaded header font: {font_path}")
                break
            except:
                continue

        if not font_loaded:
            print("[WARNING] No Chinese font found for header, using default")
            self.font_header = ImageFont.load_default()

        # Try to load body font (regular, smaller)
        font_loaded = False
        for font_path in chinese_font_paths:
            try:
                self.font_body = ImageFont.truetype(font_path, 26)
                font_loaded = True
                print(f"[DEBUG] Loaded body font: {font_path}")
                break
            except:
                continue

        if not font_loaded:
            print("[WARNING] No Chinese font found for body, using default")
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
    def wrap_text_lines(description, suggestion, max_chars=30):
        """
        Create formatted text lines with description and suggestion (Chinese compatible)
        Args:
            description: Description text (Chinese or English)
            suggestion: Suggestion text (Chinese or English)
            max_chars: Maximum characters per line for wrapping (reduced for Chinese)
        Returns:
            Array: ["描述:", "- (description text)", "建议:", "- (suggestion text)"]
        """
        def wrap_chinese_text(text, prefix="- ", indent="  ", max_len=30):
            """Wrap text supporting both Chinese and English"""
            if not text:
                return []

            lines = []
            current_line = prefix

            # For Chinese text, wrap by character; for English, try to wrap by word
            i = 0
            while i < len(text):
                char = text[i]

                # Check if current character is Chinese
                is_chinese = '\u4e00' <= char <= '\u9fff'

                if is_chinese:
                    # For Chinese characters, add one at a time
                    if len(current_line) >= max_len and current_line != prefix:
                        lines.append(current_line)
                        current_line = indent + char
                    else:
                        current_line += char
                    i += 1
                else:
                    # For English text, try to get the whole word
                    word_end = i
                    while word_end < len(text) and text[word_end] not in ' \n\t,.:;!?':
                        word_end += 1

                    word = text[i:word_end]

                    # Add the word if it fits
                    if len(current_line + word) > max_len and current_line != prefix:
                        lines.append(current_line.rstrip())
                        current_line = indent + word
                    else:
                        current_line += word

                    i = word_end

                    # Handle spaces and punctuation
                    if i < len(text) and text[i] in ' \t':
                        current_line += ' '
                        i += 1

            if current_line.strip() not in [prefix.strip(), indent.strip()]:
                lines.append(current_line.rstrip())

            return lines

        wrapped = []

        # Add Description section
        wrapped.append("描述:")
        if description:
            description = description.strip()
            wrapped.extend(wrap_chinese_text(description, max_len=max_chars))

        # Add Suggestion section
        wrapped.append("建議:")
        # Wrap suggestion text with bullet points
        suggestion_list = suggestion.split('\n')
        for item in suggestion_list:
            item = item.strip()
            if item:
                # Remove leading dash if present
                if item.startswith('-'):
                    item = item[1:].strip()
                wrapped.extend(wrap_chinese_text(item, max_len=max_chars))

        return wrapped
    def _filter_security_response(self, response_str: str) -> str:
        """
        Deterministic local filtering to avoid contradictory lines produced by the LLM.
        - If any line contains 'not all' (fluorescent lamps not all lit), keep that line and remove any
          'all fluorescent ...' lines to avoid contradiction.
        - Normalize any remaining 'all fluorescent' lines to the exact form:
            "All fluorescent lamps are lit up, no"
        - Remove lines that indicate "no emergency exit" (they should not appear).
        - Remove lines that contain both "gate" and "visible" together (e.g., "gate not visible", "no gate visible").
        - Remove lines that contain "no visible" or "not visible".
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
            if "沒有可見的門" in low:
                continue
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
                    "你是工廠的保安人員,正在檢查圖像。請嚴格按照指示操作,只輸出所需的觀察結果——不要解釋、不要推理、不要額外文字。\n\n"
                    "1) 檢查門的關閉狀態:如果有可見的門,報告門是否關閉,如果沒有可見的門,說明\"沒有可見的門\"。\n"
                    "2) 除了門的狀態外,提供恰好兩個額外的、不同的、與安全相關的觀察(例如:人員、障礙物、地面積水、煙霧、破碎玻璃)。不要重複觀察,每個觀察保持簡短。\n"
                    "3) 對於每個觀察,附加是否需要立即處理:\"是\"或\"否\"(只能是是/否)。\n"
                    "4) 輸出格式:三行獨立的內容,每行格式為:<觀察>, <是|否>\n"
                    "- 使用最簡短的措辭(不要完整句子,不要標籤,不要編號)。\n"
                    "示例:\n"
                    "螢光燈未全部點亮, 是\n"
                    "緊急出口門已關閉, 否\n"
                    "長椅旁有無人看管的包, 是\n"
                    "入口處地面潮濕, 是"
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
            # Check for specific objects (translate detection objects to Chinese if needed)
            objects_chinese = {
                "plastic bag": "塑膠袋",
                "plastic bottle": "塑膠瓶",
                "cardboard": "紙板",
                "water puddle": "水坑",
                "smoker": "吸煙者"
            }
            translated_objects = [objects_chinese.get(obj, obj) for obj in self.detection_objects]
            self.describer.action(
                question=f"照片中是否有{translated_objects}?" \
                         "示例回答格式:\n" \
                         "垃圾, 否\n" \
                         "水坑, 否\n" \
                         "吸煙者, 否",
                image=image_path
            )
            obj_detection_list = self.extract_points(self.describer.response)
            print(f"[DEBUG] Object detection results: {obj_detection_list}")

            # Add visible objects to points
            for obj in obj_detection_list:
                if len(obj) >= 2 and obj[1].replace(" ", "").replace(".","").lower() in ["yes", "是"]:
                    points.append([f"檢測到{obj[0]}", "否"])

            # Filter out any malformed points (safety check)
            points = [p for p in points if len(p) >= 2]
            print(f"[DEBUG] Total points after filtering: {len(points)}")

            # Sort points: items with "否" in position [1] come first
            points.sort(key=lambda x: 0 if x[1].replace(' ', '').replace(".","").lower() in ['no', '否'] else 1)

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
            is_description_only = point[1].replace(" ", "").replace(".","").lower() in ['no', '否']

            if point[1].replace(" ", "").replace(".","").lower() in ['yes', '是']:
                # For items with suggestions, complete any ongoing description-only row first
                if description_only_column_count > 0:
                    current_y_position = current_y_position + row_max_height + 80
                    current_x_position = 60
                    description_only_column_count = 0
                    row_max_height = 0
                print("ask_4")
                self.describer.action(
                    question=f"針對問題 {point[0]} 給出預防措施建議 " \
                             "以最簡短的要點形式回答: -... , -..., -... " \
                             "描述和建議都要簡短,不超過20個字, " \
                             "只給出**1**條建議要點,信息要最簡短",
                    image=image_path
                )
                response_text = self.describer.response
                wrapped_lines = self.wrap_text_lines(point[0], response_text, max_chars=25)

            else:
                # For description only items, just capitalize first letter if it's a letter
                description = point[0].strip()
                if description and description[0].isalpha():
                    description = description[0].upper() + description[1:]
                wrapped_lines = ["描述:", f"- {description}"]

            # Add text with background for readability
            text_position = (current_x_position, current_y_position)
            line_height = 42
            y_offset = text_position[1]
            max_width = 0
            total_height = 0

            for line in wrapped_lines:
                current_font = self.font_header if line.startswith("描述:") or line.startswith("建議:") else self.font_body
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
                current_font = self.font_header if line.startswith("描述:") or line.startswith("建議:") else self.font_body
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
    image = "https://hkpic1.aimo.tech/securityClockOut/20251021/as00107/22/20251021223359650-as00107-%E5%8F%B3.jpg"  # Local image path

    # Create describer instance with custom detection objects (optional)
    detection_objects = ["plastic bag", "plastic bottle", "cardboard", "water puddle", "smoker"]
    describer = QwenDescriber(detection_objects=detection_objects)

    # Process and annotate the image
    output_path = describer.process_and_annotate(image)