import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

MODELS_CONFIG = {
    "sd15": {
        "name": "Stable Diffusion 1.5",
        "model_id": os.getenv("SD15_MODEL_ID", "runwayml/stable-diffusion-v1-5"),
        "min_vram_gb": 0,
        "default_size": (512, 512),
        "description": "Быстрая, работает на CPU",
    },
    "sdxl": {
        "name": "Stable Diffusion XL",
        "model_id": os.getenv("SDXL_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0"),
        "min_vram_gb": 8,
        "default_size": (1024, 1024),
        "description": "Высокое качество, требует GPU",
    },
    "flux": {
        "name": "FLUX.1 Dev",
        "model_id": os.getenv("FLUX_MODEL_ID", "black-forest-labs/FLUX.1-dev"),
        "min_vram_gb": 16,
        "default_size": (1024, 1024),
        "description": "Лучшее качество, требует мощный GPU",
    },
}

STYLES_CONFIG = {
    "": {"name": "Без стиля", "model_id": None, "negative_prompt": ""},
    "photorealistic": {
        "name": "Фотореализм",
        "model_id": "SG161222/Realistic_Vision_V5.1_noVAE",
        "negative_prompt": "cartoon, anime, 3d, illustration, painting, drawing, art, cartoonish, unrealistic",
    },
    "anime": {
        "name": "Аниме",
        "model_id": "cagliostrolab/animagine-xl-3.1",
        "negative_prompt": "realistic, photo, 3d, human, person, realistic skin, detailed eyes",
    },
    "art": {
        "name": "Арт",
        "model_id": "oc蜀黍/Comic-Diffusion",
        "negative_prompt": "photo, realistic, 3d, photograph, realistic skin",
    },
    "3d": {
        "name": "3D",
        "model_id": "GuGuangkai/ToonYou-Beta5",
        "negative_prompt": "2d, anime, illustration, painting, drawing, art, flat",
    },
}

ASPECT_RATIO_SIZES = {
    "1:1": (1024, 1024),
    "16:9": (1024, 576),
    "9:16": (576, 1024),
    "4:3": (1024, 768),
    "3:2": (1024, 683),
    "2:3": (683, 1024),
}

ASPECT_RATIO_NAMES = {
    "1:1": "Квадрат (1:1)",
    "16:9": "Горизонтально (16:9)",
    "9:16": "Вертикально (9:16)",
    "4:3": "Классический (4:3)",
    "3:2": "Фото (3:2)",
    "2:3": "Портрет (2:3)",
}

NUM_VARIATIONS_OPTIONS = [1, 2, 3, 4]

VARIATION_LABELS = {
    1: "1 вариация",
    2: "2 вариации",
    3: "3 вариации",
    4: "4 вариации",
}


def get_vram_gb() -> float:
    try:
        import torch
        if not torch.cuda.is_available():
            return 0
        return torch.cuda.get_device_properties(0).total_memory / (1024**3)
    except Exception:
        return 0


def get_available_models() -> List[str]:
    vram = get_vram_gb()
    available = []
    
    for model_id, config in MODELS_CONFIG.items():
        if vram >= config["min_vram_gb"]:
            available.append(model_id)
    
    if not available:
        available = ["sd15"]
    
    logger.info(f"Available models for {vram:.1f}GB VRAM: {available}")
    return available


def is_model_available(model: str) -> bool:
    return model in get_available_models()


def get_model_info(model: str) -> Optional[Dict]:
    return MODELS_CONFIG.get(model)


def get_style_info(style: str) -> Optional[Dict]:
    return STYLES_CONFIG.get(style)


def get_aspect_ratio_size(aspect: str) -> tuple:
    return ASPECT_RATIO_SIZES.get(aspect, (1024, 1024))


def get_model_display_name(model: str) -> str:
    info = MODELS_CONFIG.get(model)
    if not info:
        return model
    
    if not is_model_available(model):
        return f"{info['name']} ⚠️"
    return info['name']


def get_style_display_name(style: str) -> str:
    info = STYLES_CONFIG.get(style)
    if not info:
        return style
    return info['name']
