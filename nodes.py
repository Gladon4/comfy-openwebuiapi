import base64
import io

import numpy as np
import requests
import torch
from PIL import Image


class ConnecitonNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ip": ("STRING", {"default": "localhost"}),
                "port": ("INT", {"default": 3000, "min": 0, "max": 65535}),
                "api_token": ("STRING", {"default": ""}),
            }
        }

    RETURN_NAMES = ("connection", "models")
    RETURN_TYPES = ("*", "*")

    FUNCTION = "connect"

    CATEGORY = "open_web_ui"

    def connect(self, ip, port, api_token):
        url = f"http://{ip}:{port}/ollama/api/tags"
        headers = {"Authorization": f"Bearer {api_token}"}

        response = requests.get(url, headers=headers).json()
        models = [model_dict["name"] for model_dict in response["models"]]

        connection = {"ip": ip, "port": port, "api_token": api_token}

        return (connection, models)


class Generate:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "connection": ("*", {"forceInput": True}),
                "prompt": ("STRING", {"default": "Why is the sky blue?"}),
                "model": ("STRING", {"default": "gpt-oss:120b"}),
            },
            "optional": {
                "context": ("*", {"default": []}),
                "image": ("IMAGE", {"default": []}),
            },
        }

    RETURN_NAMES = ("connection", "response", "context")
    RETURN_TYPES = ("*", "STRING", "*")

    FUNCTION = "generate"

    CATEGORY = "open_web_ui"

    def generate(self, connection, prompt, model, **kwargs):
        if "context" in kwargs:
            context = kwargs["context"]
        else:
            context = []

        url = f"http://{connection['ip']}:{connection['port']}/ollama/api/chat"
        headers = {
            "Authorization": f"Bearer {connection['api_token']}",
            "Content-Type": "application/json",
        }

        message = {"role": "user", "content": prompt}

        if "image" in kwargs:
            tensor_image = kwargs["image"]
            # squeeze(): shape (1, H, W, 3) -> shape (H, W, 3)
            np_img = tensor_image.squeeze().detach().cpu().numpy()
            np_img = (np_img * 255).clip(0, 255).astype(np.uint8)

            image = Image.fromarray(np_img)

            base64_image = self.convert_image_to_base64(image)

            message["images"] = [str(base64_image)]

        context.append(message)

        data = {"model": model, "messages": context, "stream": False}

        response = requests.post(url, headers=headers, json=data, stream=False)

        answer = response.json()["message"]["content"]
        context += [response.json()["message"]]

        return (connection, answer, context)

    def convert_image_to_base64(self, image: Image):
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str


class ImageGenerate:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "connection": ("*", {"forceInput": True}),
                "prompt": ("STRING", {"default": "A cool car."}),
            },
        }

    RETURN_NAMES = ("connection", "image")
    RETURN_TYPES = ("*", "IMAGE")

    FUNCTION = "generate"

    CATEGORY = "open_web_ui"

    def generate(self, connection, prompt):
        url = (
            f"http://{connection['ip']}:{connection['port']}/api/v1/images/generations"
        )
        headers = {
            "Authorization": f"Bearer {connection['api_token']}",
            "Content-Type": "application/json",
        }

        data = {"prompt": prompt}

        gen = requests.post(url, headers=headers, json=data, stream=False).json()
        relative_url = gen[0]["url"]
        img_url = f"http://{connection['ip']}:{connection['port']}{relative_url}"
        img = requests.get(img_url, headers=headers).content

        image = Image.open(io.BytesIO(img)).convert("RGB")  # ensure 3 channels

        np_image = np.array(image)  # shape (H, W, 3)
        tensor_image = torch.from_numpy(np_image).float() / 255.0

        # Add batch dimension
        tensor_image = tensor_image.unsqueeze(0)  # shape (1, H, W, 3)

        return (connection, tensor_image)


NODE_CLASS_MAPPINGS = {
    "Connection Node": ConnecitonNode,
    "Generate": Generate,
    "ImageGenerate": ImageGenerate,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "Connection Node": "Connection Node",
    "Generate": "Generate",
    "ImageGenerate": "Generate Image",
}
