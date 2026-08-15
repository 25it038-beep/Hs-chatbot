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
    "nemotron-3-ultra-550b": {
        "id": "nvidia/nemotron-3-ultra-550b-a55b",
        "name": "Nemotron-3 Ultra 550B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "reasoning"],
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
    "mistral-large": {
        "id": "mistralai/mistral-large-2-instruct",
        "name": "Mistral Large 2",
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
}

# Task routing configuration
TASK_ROUTES = {
    "chat": {
        "default": "llama-3.1-70b",
        "fallback": ["mistral-large"],
    },
    "coding": {
        "default": "llama-3.1-70b",
        "fallback": ["mistral-large"],
    },
    "reasoning": {
        "default": "llama-3.1-70b",
        "fallback": ["mistral-large"],
    },
    "vision": {
        "default": "nemotron-vl",
        "fallback": ["llama-3.2-vision"],
    },
    "image_generation": {
        "default": "flux-1-dev",
        # flux-1-schnell cold-starts very slowly (>90s) — try flux-2-klein first
        "fallback": ["flux-2-klein", "flux-1-schnell"],
    },
    "web_images": {
        "default": "llama-3.1-70b",
        "fallback": ["glm-5.2"],
    },
    "embeddings": {
        "default": "nv-embed-v1",
        # nv-embedcode-7b returns HTTP 500 from NVIDIA — disabled until fixed upstream
        "fallback": [],
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
    "web_images": [
        "show me images of", "show me images for",
        "show me pictures of", "show me pictures for",
        "show me photos of", "show me photos for",
        "images of", "pictures of", "photos of",
        "show me a picture of", "show me a photo of",
        "show me an image of", "show me image of",
        "find images of", "search images of",
        "images for", "pictures for", "photos for",
        "find me images of", "find me pictures of",
        "find me photos of", "image search for",
        "web image of", "web images of",
        "an image of", "a picture of", "a photo of",
        "image of", "picture of", "photo of",
    ],

}

CHAT_TASK_KEYWORDS = {
    "chat": [
        "hello", "hi", "how are you", "what can you do", "help",
    ],
}
