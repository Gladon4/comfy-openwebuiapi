import requests
import io
from PIL import Image
import torch
import numpy as np

class ConnecitonNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ip": ("STRING", {"default": "localhost"}),
                "port": ("INT", {"default": 3000, "min": 0, "max": 65535}),
                "api_token": ("STRING", {"default": ""})
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
                "model": ("STRING", {"default": "gpt-oss:120b"})
            },
            "optional": {
                "context": ("*", {"default": []}),
            }
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

        url = f"http://{connection["ip"]}:{connection["port"]}/ollama/api/chat"
        headers = {"Authorization": f"Bearer {connection["api_token"]}", "Content-Type": "application/json"}

        context += [{
                "role": "user",
                "content": prompt
                }]

        data = {
            "model": model,
            "messages": context,
            "stream": False
            
        }

        response = requests.post(url, headers=headers, json=data, stream=False)
        answer = response.json()["message"]["content"]
        context += [response.json()["message"]]

        return (connection, answer, context)



class ImageGenerate:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "connection": ("*", {"forceInput": True}),
                "prompt": ("STRING", {"default": "A cool car."})
            },
        }
    
    RETURN_NAMES = ("connection", "image")
    RETURN_TYPES = ("*", "IMAGE")

    FUNCTION = "generate"

    CATEGORY = "open_web_ui"
    
    def generate(self, connection, prompt):
        url = f"http://{connection["ip"]}:{connection["port"]}/api/v1/images/generations"
        headers = {"Authorization": f"Bearer {connection["api_token"]}", "Content-Type": "application/json"}


        data = {
            "prompt": prompt            
        }

        gen = requests.post(url, headers=headers, json=data, stream=False).json()
        relative_url = gen[0]["url"]
        img_url = f"http://{connection["ip"]}:{connection["port"]}{relative_url}"
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
    # "DisplayText": "Displays Text"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']