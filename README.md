# ComfyUI Open WebUI API 

This set of custom nodes enables you to access Ollama Models through the Open WebUI.

## Nodes
- Connection
- Generate
- ImageGenerate

## Usage
To use this you will need to have Ollama set up with Open WebUI.  
Log into the web interface, go to your user settings and create an API Token. In Comfy UI Add this token (the one labeled JWT-Token) to the Connection Node alongside with the IP and Port of Open WebUI (it should be the same as you need to access the web view).  
The connection Node outputs models, which is a string of all availablle model names, use them for the Generate Node.  
The connection output contains the data needed for the API requests, sonnect it to your Generate and ImageGenerate Nodes.

To use the image input on the Generate Node, you need to choose a model that supports vision (for example qwen3.6 or llava).

If you have set up image generation in Open WebUI you can also use a basic version of it through this connection with the ImageGenerate Node.
