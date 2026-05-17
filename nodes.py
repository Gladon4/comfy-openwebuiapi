import base64
import io

import numpy as np
import requests
import torch
from aiohttp import web
from PIL import Image

from server import PromptServer


@PromptServer.instance.routes.get("/comfy-openwebui/models")
async def get_models(request):
    ip = request.query.get("ip")
    port = request.query.get("port")
    token = request.query.get("token")

    url = f"http://{ip}:{port}/ollama/api/tags"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers).json()
        models = [m["name"] for m in response.get("models", [])]
        return web.json_response(models)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


class ConnecitonNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ip": ("STRING", {"default": "localhost"}),
                "port": ("INT", {"default": 3000, "min": 0, "max": 65535}),
                "api_token": ("STRING",),
            }
        }

    RETURN_NAMES = ("connection",)
    RETURN_TYPES = ("*",)

    FUNCTION = "connect"

    CATEGORY = "open_web_ui"

    def connect(self, ip, port, api_token):
        connection = {"ip": ip, "port": port, "api_token": api_token}

        return (connection,)


class ModelParameters:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "temperature": (
                    "FLOAT",
                    {"default": 0.7, "min": 0, "max": 1, "step": 0.01},
                ),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2**32 - 1}),
                "repeat_penalty": (
                    "FLOAT",
                    {"default": 1.1, "min": 0, "max": 2, "step": 0.01},
                ),
                "num_predict": ("INT", {"default": -1, "min": -1, "max": 4096}),
                "top_k": ("INT", {"default": 40, "min": -1, "max": 10000}),
                "stop": ("STRING", {"default": "", "multiline": False}),
                "num_ctx": ("INT", {"default": 2048, "min": 1, "max": 250000}),
            },
        }

    RETURN_NAMES = ("parameters",)
    RETURN_TYPES = ("*",)

    FUNCTION = "get_params"

    CATEGORY = "open_web_ui"

    def get_params(self, **kwargs):
        params = {}
        if "temperature" in kwargs and kwargs["temperature"] != 0.7:
            params["temperature"] = kwargs["temperature"]
        if "seed" in kwargs and kwargs["seed"] != -1:
            params["seed"] = kwargs["seed"]
        if "repeat_penalty" in kwargs and kwargs["repeat_penalty"] != 1.1:
            params["repeat_penalty"] = kwargs["repeat_penalty"]
        if "num_predict" in kwargs and kwargs["num_predict"] != -1:
            params["num_predict"] = kwargs["num_predict"]
        if "top_k" in kwargs and kwargs["top_k"] != 40:
            params["top_k"] = kwargs["top_k"]
        if "stop" in kwargs and kwargs["stop"] != "":
            params["stop"] = [kwargs["stop"]]
        if "num_ctx" in kwargs and kwargs["num_ctx"] != 2048:
            params["num_ctx"] = kwargs["num_ctx"]
        return (params,)


class Generate:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "connection": ("*", {"forceInput": True}),
                "prompt": ("STRING", {"default": "Why is the sky blue?"}),
                "model": ("STRING", {"default": ""}),
            },
            "optional": {
                "context": ("*", {"default": []}),
                "images": ("IMAGE", {"default": []}),
                "parameters": ("*", {"default": {}}),
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

        ip = connection["ip"]
        port = connection["port"]
        api_token = connection["api_token"]

        url = f"http://{ip}:{port}/ollama/api/chat"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        message = {"role": "user", "content": prompt}

        if "images" in kwargs:
            tensor_images = kwargs["images"]
            batch_size = tensor_images.shape[0]
            message["images"] = []

            for i in range(batch_size):
                tensor_image = tensor_images[i]  # shape: (H, W, 3)

                np_img = tensor_image.detach().cpu().numpy()
                np_img = (np_img * 255).clip(0, 255).astype(np.uint8)

                image = Image.fromarray(np_img)

                base64_image = self.convert_image_to_base64(image)
                message["images"].append(str(base64_image))

        context.append(message)

        data = {"model": model, "messages": context, "stream": False}

        params = kwargs.get("parameters", {})
        if params:
            data["options"] = params

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
        ip = connection["ip"]
        port = connection["port"]
        api_token = connection["api_token"]

        url = f"http://{ip}:{port}/api/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {api_token}",
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
    "ModelParameters": ModelParameters,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "Connection Node": "Connection Node",
    "Generate": "Generate Text",
    "ImageGenerate": "Generate Image",
    "ModelParameters": "Model Parameters",
}
