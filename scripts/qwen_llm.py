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
            # print(self.response)
            if self.mode == "detector":
                annotated_image_bytes = self.draw_normalized_bounding_boxes(image, self.response)
                # Convert bytes back to PIL Image and display
                annotated_image = PIL_Image.open(BytesIO(annotated_image_bytes))
                annotated_image.show()
        except Exception as e:
            print(f"[ERROR] Action failed: {e}")
            import traceback
            traceback.print_exc()
            self.response = ""


if __name__=="__main__":
    # image="images/lab_2.png"
    # detection_list=["plastic bag","cardboard", "rubbish bin"]
    # detection_list=["person"]
    # detection_list=["light not lighted up"]
    # talker=qwen_llm("detector",detection_list)
    # talker.action(image=image)

    # image="images/lab_2.png"
    # talker=qwen_llm("image description")
    # talker.action(question="Are there unlit light in the photo? Answer yes or no only.",image=image)
    # if talker.response == "yes":
    #     detection_list=["water puddle"]
    #     detector=qwen_llm("detector",detection_list)
    #     detector.action(image=image)

    # image="water_3_cropped.jpeg"
    # talker=qwen_llm("image description")
    # talker.action(question="Are there water puddles in the photo? Answer yes or no only.",image=image)
    # if talker.response == "yes":
    #     detection_list=["water puddle"]
    #     detector=qwen_llm("detector",detection_list)
    #     detector.action(image=image)



    # talker.action("is there a person in the infrared image, answer yes or no only", image)

    # image="license_plate_3.jpg"
    # talker=qwen_llm("license plate detection")
    # talker.action(image=image)

    # image="image_copy.png"
    # describer=qwen_llm("image description")
    # detector = qwen_llm("detector", detection_list=["person not wearing safety helmet on their head"])
    # describer.action(question=(
    #     "你是工地安全檢查員。你的任務是找出**沒有**佩戴安全帽的人。\n\n"
    #     "安全帽識別標準：\n"
    #     "- 安全帽是**堅硬的頭盔**（通常是黃色、白色、紅色或藍色）\n"
    #     "- 普通帽子、鴨舌帽、布帽**不是**安全帽\n"
    #     "- 如果頭上什麼都沒戴，或只戴了普通帽子 = **未佩戴安全帽**\n\n"
    #     "檢查任務：\n"
    #     "請仔細觀察圖片中**每一個人的頭部**。\n"
    #     "找出所有**沒有佩戴硬質頭盔**的人。\n\n"
    #     "回答要求：\n"
    #     "- 如果發現有人**沒戴**安全帽（硬質頭盔），回答：\"有人未佩戴安全帽\"，並具體說明是哪一個人（位置、穿著特徵）\n"
    #     "- 只有當**每個人**頭上都有硬質頭盔時，才回答：\"所有人都佩戴安全帽\"\n"
    #     "- 有疑問時，請傾向於報告\"有人未佩戴安全帽\"\n\n"
    #     "現在請檢查圖片並給出答案："
    # ), image=image)
    # print(describer.response)

    chatter = qwen_llm("chatter")
    question = "停車場的保安人員,關於停車場環境請列出兩項你需要注意的事項 "
    chatter.action(question=question)
    print(chatter.response)