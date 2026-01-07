from openai import OpenAI
import base64
import os

import json
import requests

from PIL import Image as PIL_Image
from PIL import ImageDraw
from io import BytesIO


class qwen_llm():

    def __init__(self, mode, detection_list=[]):
        api_key = os.getenv("qwen_api")
        if not api_key:
            raise ValueError("Environment variable 'qwen_api' is not set. Please set it with your Qwen API key.")

        self.client = OpenAI(api_key=api_key,
                            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                            )
        self.mode=mode
        self.detection_list=detection_list
        self.response=""

    def encode_image(self,image_path):
        if image_path.startswith(('http://', 'https://')):
            # Handle HTTP/HTTPS URLs
            response = requests.get(image_path)
            response.raise_for_status()  # Raise exception for bad status codes
            return base64.b64encode(response.content).decode("utf-8")
        else:
            # Handle local file paths
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        
    def extract_json_from_string(self,text: str) -> str:
        try:
            start_brace = text.find('{')
            start_bracket = text.find('[')

            if start_brace == -1:
                start_index = start_bracket
            elif start_bracket == -1:
                start_index = start_brace
            else:
                start_index = min(start_brace, start_bracket)

            end_brace = text.rfind('}')
            end_bracket = text.rfind(']')
            end_index = max(end_brace, end_bracket)

            if start_index == -1 or end_index == -1:
                return text 

            return text[start_index : end_index + 1]
        except Exception:
            return text

    def draw_normalized_bounding_boxes(self,image_path: str, llm_output_string: str):
        if image_path.startswith(('http', 'https')):
            response = requests.get(image_path)
            img = PIL_Image.open(BytesIO(response.content))
        else:
            img = PIL_Image.open(image_path)

        img_width, img_height = img.size

        clean_json_str = self.extract_json_from_string(llm_output_string)

        locations = json.loads(clean_json_str)
        draw = ImageDraw.Draw(img)

        for loc in locations:
            norm_box = loc['bbox_2d']

            pixel_box = [
                (norm_box[0] / 1000) * img_width,
                (norm_box[1] / 1000) * img_height,
                (norm_box[2] / 1000) * img_width,
                (norm_box[3] / 1000) * img_height,
            ]

            draw.rectangle(pixel_box, outline='lime', width=3)

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        annotated_img = buffer.getvalue()

        return annotated_img
    
    def create_prompt(self, question, image=None):
        if self.mode == "chatter":
            return [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                    ],
                },
            ]
        elif self.mode == "detector":
            return [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{self.encode_image(image)}"},
                        },
                        {"type": "text", "text": f"Locate the object: {', '.join(self.detection_list)}."},
                    ],
                },
            ]
        elif self.mode == "image description":
            return [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{self.encode_image(image)}"},
                        },
                        {"type": "text", "text": question},
                    ],
                },
            ]
        elif self.mode=="ocr":
            return [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{self.encode_image(image)}"},
                        },
                        {"type": "text", "text": "Extract the text from the image."},
                    ],
                },
            ]
        
        elif self.mode == "license plate detection":
            return [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{self.encode_image(image)}"},
                        },
                        {"type": "text", "text": "What is the license plate number of the car, answer the license plate number only"},
                    ],
                },
            ]

    def get_full_content(self,completion):
        full_content = ""
        try:
            for chunk in completion:
                if chunk.choices:
                    choice_deltas = chunk.choices[0].delta
                    if choice_deltas.content:
                        full_content += choice_deltas.content
        except Exception as e:
            print(f"[ERROR] Error in streaming: {e}")
            import traceback
            traceback.print_exc()
        return full_content
    
    def extract_json_from_string(self,text: str) -> str:
        try:
            start_brace = text.find('{')
            start_bracket = text.find('[')

            if start_brace == -1:
                start_index = start_bracket
            elif start_bracket == -1:
                start_index = start_brace
            else:
                start_index = min(start_brace, start_bracket)

            end_brace = text.rfind('}')
            end_bracket = text.rfind(']')
            end_index = max(end_brace, end_bracket)

            if start_index == -1 or end_index == -1:
                return text 

            return text[start_index : end_index + 1]
        except Exception:
            return text

    def draw_normalized_bounding_boxes(self,image_path: str, llm_output_string: str):
        if image_path.startswith(('http', 'https')):
            response = requests.get(image_path)
            img = PIL_Image.open(BytesIO(response.content))
        else:
            img = PIL_Image.open(image_path)

        img_width, img_height = img.size

        clean_json_str = self.extract_json_from_string(llm_output_string)

        locations = json.loads(clean_json_str)
        draw = ImageDraw.Draw(img)

        for loc in locations:
            norm_box = loc['bbox_2d']

            pixel_box = [
                (norm_box[0] / 1000) * img_width,
                (norm_box[1] / 1000) * img_height,
                (norm_box[2] / 1000) * img_width,
                (norm_box[3] / 1000) * img_height,
            ]

            draw.rectangle(pixel_box, outline='lime', width=3)

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        annotated_img = buffer.getvalue()

        return annotated_img

    def run_model(self, question, image):
        try:
            prompt_message = self.create_prompt(question, image)
            completion = self.client.chat.completions.create(
                model="qwen3-omni-flash",
                messages=prompt_message,
                modalities=["text"],
                stream=True,
                stream_options={"include_usage": True},
                temperature=0.1,
                top_p=0.7
                )
            response=self.get_full_content(completion)
            return response
        except Exception as e:
            print(f"[ERROR] Model execution error: {e}")
            import traceback
            traceback.print_exc()
            return ""
    

    def action(self,question="",image=None):
        if self.mode not in ["chatter","detector","ocr", "image description", "license plate detection"]:
            print ("[ERROR] Unspecified mode please reinitialize with proper mode")
            return
        try:
            self.response=self.run_model(question,image)
            # # print(self.response)
            # if self.mode == "detector":
            #     annotated_image_bytes = self.draw_normalized_bounding_boxes(image, self.response)
            #     # Convert bytes back to PIL Image and display
            #     annotated_image = PIL_Image.open(BytesIO(annotated_image_bytes))
            #     annotated_image.show()
        except Exception as e:
            print(f"[ERROR] Action failed: {e}")
            import traceback
            traceback.print_exc()
            self.response = ""

if __name__=="__main__":
    # Universal prompt testing
    image = "https://hkpic1.aimo.tech/securityClockOut/20251210/as00213/15/20251210154016410-as00213-%E5%B7%A6.jpg"

    # Test objects to detect
    detection_objects = ["unattended bag","person seated in front of slot machine but not playing the slot machine"]

    # Universal prompt that requests detailed explanation then extracts list
    def create_universal_filter_prompt(objects_list):
        """
        Creates a universal prompt that:
        1. Takes a list of objects/scenarios as input
        2. Requests detailed explanation for each
        3. Returns a Python list of detailed descriptions of detected objects
        """
        prompt = f"""Analyze the image carefully for the following objects/scenarios:
{objects_list}

For EACH item in the list above:
1. Examine the image thoroughly
2. Verify ALL conditions mentioned (e.g., if it says "not playing", verify the person is truly idle with hands away from controls, not engaged with the machine)
3. Check negative conditions carefully (e.g., "not playing" means hands idle AND not looking at screen AND not pressing buttons)
4. Provide a brief explanation of what you observe for each item
5. Be strict and conservative: only confirm existence if ALL conditions are definitively met. When in doubt, exclude it.

After your detailed analysis, for each object that truly exists, provide a detailed description including its location, posture, and state.

Response format:
Analysis: [your detailed reasoning for each item]
Result: ['detailed description of detected object 1', 'detailed description of detected object 2'] or [] if none exist

For example, instead of returning ['person not playing'], return ['person seated at third slot machine on left with hands resting on lap, not engaging with controls']"""
        return prompt

    # Test the universal prompt
    print("=" * 80)
    print("TESTING UNIVERSAL FILTER PROMPT")
    print("=" * 80)

    talker = qwen_llm("image description")
    universal_prompt = create_universal_filter_prompt(detection_objects)

    print(f"\nPrompt:\n{universal_prompt}\n")
    print("-" * 80)

    talker.action(image=image, question=universal_prompt)
    print(f"\nResponse:\n{talker.response}\n")
    print("=" * 80)

    # Extract the list from response
    import ast
    try:
        response_text = talker.response.strip()
        if '[' in response_text and ']' in response_text:
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            list_str = response_text[start_idx:end_idx]
            extracted_list = ast.literal_eval(list_str)
            print(f"\nExtracted List: {extracted_list}")
        else:
            print("\nNo list found in response")
    except Exception as e:
        print(f"\nError extracting list: {e}")

    print("\n" + "=" * 80)

    # Also test detector for comparison
    print("\nCOMPARISON: DETECTOR MODE")
    print("=" * 80)
    detector = qwen_llm("detector", detection_list=detection_objects)
    detector.action(image=image)
    print(f"\nDetector Response:\n{detector.response}\n")
    print("=" * 80)