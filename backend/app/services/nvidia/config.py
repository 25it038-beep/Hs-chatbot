NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

NVIDIA_MODELS = {
    # Chat
    "glm-5.2": {
        "id": "z-ai/glm-5.2",
        "name": "GLM 5.2",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "reasoning", "tools"],
        "max_tokens": 16384,
        "default_temp": 1.0,
        "supports_thinking": True,
    },
    "llama-3.3-70b": {
        "id": "meta/llama-3.3-70b-instruct",
        "name": "Llama 3.3 70B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "tools"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "llama-3.1-70b": {
        "id": "meta/llama-3.1-70b-instruct",
        "name": "Llama 3.1 70B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "tools"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    # Coding (uses GLM 5.2)
    "glm-coder": {
        "id": "z-ai/glm-5.2",
        "name": "GLM 5.2 (Coding)",
        "type": "coding",
        "capabilities": ["chat", "streaming", "code", "reasoning"],
        "max_tokens": 16384,
        "default_temp": 0.2,
        "supports_thinking": True,
    },
    # Vision
    "nemotron-vl": {
        "id": "nvidia/nemotron-nano-12b-v2-vl",
        "name": "Nemotron Nano VL",
        "type": "vision",
        "capabilities": ["chat", "vision", "streaming"],
        "max_tokens": 4096,
        "default_temp": 1.0,
        "supports_images": True,
    },
    "llama-3.2-vision": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 Vision",
        "type": "vision",
        "capabilities": ["chat", "vision", "streaming"],
        "max_tokens": 4096,
        "default_temp": 1.0,
        "supports_images": True,
    },
    # Image Generation
    "flux-2-klein": {
        "id": "black-forest-labs/flux.2-klein-4b",
        "name": "FLUX.2 Klein 4B",
        "type": "image_generation",
        "capabilities": ["image-generation"],
        "default_steps": 4,
    },
    "flux-1-schnell": {
        "id": "black-forest-labs/flux.1-schnell",
        "name": "FLUX.1 Schnell (Fast)",
        "type": "image_generation",
        "capabilities": ["image-generation"],
        "default_steps": 4,
    },
    "flux-1-dev": {
        "id": "black-forest-labs/flux.1-dev",
        "name": "FLUX.1 Dev",
        "type": "image_generation",
        "capabilities": ["image-generation"],
        "default_steps": 20,
    },
    # Embeddings
    "nv-embed-v1": {
        "id": "nvidia/nv-embed-v1",
        "name": "NV-Embed v1",
        "type": "embeddings",
        "capabilities": ["embeddings"],
        "dimensions": 1024,
        "max_input_length": 512,
    },
    "nv-embedcode-7b": {
        "id": "nvidia/nv-embedcode-7b-v1",
        "name": "NV-EmbedCode 7B",
        "type": "embeddings",
        "capabilities": ["embeddings", "code-embeddings"],
        "dimensions": 1024,
        "max_input_length": 512,
    },
}

# Task routing configuration
TASK_ROUTES = {
    "chat": {
        "default": "llama-3.1-70b",
        "fallback": ["glm-5.2"],
    },
    "coding": {
        "default": "glm-coder",
        "fallback": ["glm-5.2", "llama-3.1-70b"],
    },
    "reasoning": {
        "default": "glm-5.2",
        "fallback": ["llama-3.1-70b"],
    },
    "vision": {
        "default": "nemotron-vl",
        "fallback": ["llama-3.2-vision"],
    },
    "image_generation": {
        "default": "flux-2-klein",
        "fallback": ["flux-1-schnell", "flux-1-dev"],
    },
    "embeddings": {
        "default": "nv-embed-v1",
        "fallback": ["nv-embedcode-7b"],
    },
}

# Task detection patterns
TASK_PATTERNS = {
    "coding": [
        "write code", "implement", "algorithm", "algorithms",
        "debug", "refactor", "generate code", "sql query", "api endpoint",
        "coding", "programming", "script", "pipeline", "workflow",
        "python function", "javascript function", "typescript function",
        "write a function", "sort a list", "sort an array",
        "def ", "function", "import ", "const ", "let ", "var ",
        "class ", "interface ", "async ", "await ", "export ",
    ],
    "reasoning": [
        "explain", "why", "how does", "reason", "think step by step",
        "analyze", "compare", "contrast", "what is the difference",
        "solve", "mathematics", "proof", "logic", "philosophy",
    ],
    "vision": [
        "what is in this image", "describe this image", "analyze this image",
        "what do you see", "extract text from image", "ocr",
    ],
    "image_generation": [
        "/image", "/img", "/draw", "/generate-image",
        "generate", "create", "draw", "render", "illustrate",
        "make an image", "make a picture", "make a photo",
        "generate an image", "generate a picture", "generate a photo",
        "create an image", "create a picture", "create a photo",
        "draw an image", "draw a picture", "draw a photo",
        "generate image", "create image", "generate picture",
        "generate photo", "make image", "make picture",
        "generate art", "create art",
        "generate a diagram", "generate a chart",
        "draw a", "draw an", "draw me",
        "render a", "render an", "render me",
        "illustrate a", "illustrate an",
    ],

}

CHAT_TASK_KEYWORDS = {
    "chat": [
        "hello", "hi", "how are you", "what can you do", "help",
    ],
}
