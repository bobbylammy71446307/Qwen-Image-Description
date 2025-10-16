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
            points.append(line.split(','))
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

    def process_and_annotate(self, image_path, output_path=None):
        """
        Process an image and generate annotated version with security observations
        Args:
            image_path: Path to the image (local file or HTTP URL)
            output_path: Optional output path for annotated image
        Returns:
            Tuple of (points, output_path) where points is list of observations
        """
        # Get initial security observations
        self.describer.action(
            question="you are a security and performing daily surveillance," \
                     "IMPORTANT:list only 2 or less distinct and unrelated observations in the image, " \
                     "do not answer in full sentence give very minimal observation description only" \
                     "do not list an observation if the object is not actually there, " \
                     "for each observation also show the state whether the observation is dangerous answer yes or no only, " \
                     "Answer in format: ... , ... with observation coming first and state coming next, " \
                    #  "check for unlit light and check whether shop gate or door is closed first," \
                    #  "if lights are properly lit up, do not give lighting observations" \
                    #  "if doors are closed shut, only give observation if it is an emergency exit" \
                     "answer in minimal point form only, ",
            image=image_path
        )

        response = self.describer.response
        points = self.extract_points(response)

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

        # Add visible objects to points
        for obj in obj_detection_list:
            if obj[1].replace(" ", "") == "yes":
                points.append([f"visible {obj[0]}", "no"])

        # Sort points: items with "no" in position [1] come first
        points.sort(key=lambda x: 0 if x[1].replace(' ', '').lower() == 'no' else 1)

        # Generate annotated image
        annotated_path = self._annotate_image(image_path, points, output_path)

        return annotated_path

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
        # Load the image
        if image_path.startswith(('http://', 'https://')):
            import requests
            from io import BytesIO
            response = requests.get(image_path)
            img = Image.open(BytesIO(response.content))
        else:
            img = Image.open(image_path)

        draw = ImageDraw.Draw(img)

        # Track the vertical position for stacking text boxes
        current_y_position = 60
        current_x_position = 60
        description_only_column_count = 0
        row_max_height = 0

        for point in points:
            is_description_only = point[1].replace(' ', '').lower() == 'no'

            if point[1].replace(' ', '') == 'yes':
                # For items with suggestions, complete any ongoing description-only row first
                if description_only_column_count > 0:
                    current_y_position = current_y_position + row_max_height + 80
                    current_x_position = 60
                    description_only_column_count = 0
                    row_max_height = 0

                self.describer.action(
                    question=f"give precausion actions suggestions for the problem {point[0]} " \
                             "response in point form: -... , -..., -... " \
                             "give minimal description and suggestions only, " \
                             "give at most 2 suggestion points with minimal information",
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

            # Return path in AI format
            return_path = f"AI/{year}/{month}/{day}/{hour}/images/{output_filename}"
        else:
            return_path = output_path

        # Convert back to RGB and save
        img = img.convert('RGB')
        img.save(output_path)
        print(f"Image saved to {output_path}")

        return return_path


if __name__ == "__main__":
    # Example usage of the QwenDescriber class
    image = "images/lab_1.png"

    # Create describer instance with custom detection objects (optional)
    detection_objects = ["plastic bag", "plastic bottle", "cardboard", "water puddle", "smoker"]
    describer = QwenDescriber(detection_objects=detection_objects)

    # Process and annotate the image
    points, output_path = describer.process_and_annotate(image)