NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

NVIDIA_MODELS = {
    # Primary Verified Chat & General Model
    "llama-3.2-11b": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B (Ultra Fast)",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "tools", "vision"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "gpt-oss-20b": {
        "id": "openai/gpt-oss-20b",
        "name": "GPT-OSS 20B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "tools"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "llama-3.2-90b": {
        "id": "meta/llama-3.2-90b-vision-instruct",
        "name": "Llama 3.2 90B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "tools", "vision"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "llama-3.1-70b": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "tools"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "llama-3.3-70b": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "tools"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "glm-5.2": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "reasoning", "tools"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "glm-coder": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B",
        "type": "coding",
        "capabilities": ["chat", "streaming", "code", "reasoning"],
        "max_tokens": 8192,
        "default_temp": 0.2,
    },
    "codestral": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B (Coding)",
        "type": "coding",
        "capabilities": ["chat", "streaming", "code", "json"],
        "max_tokens": 8192,
        "default_temp": 0.2,
    },
    "mistral-large": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "tools"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "nemotron-3-ultra-550b": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B",
        "type": "chat",
        "capabilities": ["chat", "streaming", "reasoning"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "muse-glimmer": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B (Fast)",
        "type": "chat",
        "capabilities": ["chat", "streaming", "json", "tools", "vision"],
        "max_tokens": 8192,
        "default_temp": 0.7,
    },
    "llama-3.2-vision": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 Vision",
        "type": "vision",
        "capabilities": ["chat", "vision", "streaming"],
        "max_tokens": 8192,
        "default_temp": 0.7,
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
        "default": "llama-3.2-11b",
        "fallback": ["gpt-oss-20b"],
    },
    "coding": {
        "default": "llama-3.2-11b",
        "fallback": ["gpt-oss-20b"],
    },
    "game_development": {
        "default": "llama-3.2-11b",
        "fallback": ["gpt-oss-20b"],
    },
    "reasoning": {
        "default": "llama-3.2-11b",
        "fallback": ["gpt-oss-20b"],
    },
    "vision": {
        "default": "llama-3.2-11b",
        "fallback": [],
    },
    "image_generation": {
        "default": "flux-1-dev",
        # flux-1-schnell cold-starts very slowly (>90s) — try flux-2-klein first
        "fallback": ["flux-2-klein", "flux-1-schnell"],
    },
    "web_images": {
        "default": "llama-3.2-11b",
        "fallback": ["llama-3.2-vision"],
    },
    "video_search": {
        "default": "llama-3.2-11b",
        "fallback": ["gpt-oss-20b"],
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
        # Project / site / app creation
        "create a website", "build a website", "make a website",
        "create a site", "build a site", "make a site",
        "create a web app", "build a web app", "build an app",
        "create a project", "build a project", "generate a project",
        "create a landing page", "build a landing page",
        "create a portfolio", "build a portfolio",
        "full stack", "fullstack", "frontend project", "backend project",
        "react app", "react project", "next.js", "nextjs",
        "express server", "fastapi project", "flask app", "django project",
        "rest api", "graphql api", "node app", "node project",
        "mobile app", "flutter app", "react native",
        "chrome extension", "browser extension",
        "discord bot", "telegram bot", "cli tool",
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
