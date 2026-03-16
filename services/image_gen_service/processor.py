import logging
import os
from typing import Optional, Dict, Any, List, Callable
import time

from services.common.hardware import (
    MODELS_CONFIG, STYLES_CONFIG, ASPECT_RATIO_SIZES, 
    get_vram_gb, get_available_models
)
from services.common.schemas import IMAGE_GEN_METADATA_DEFAULTS

logger = logging.getLogger(__name__)


def get_compute_device() -> tuple:
    """
    Detect and return the best available compute device.
    Supports: NVIDIA CUDA, AMD ROCm, Intel GPU (OpenVINO), CPU
    """
    try:
        import torch
        
        # Check for NVIDIA CUDA
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"NVIDIA GPU detected: {device_name} ({vram_gb:.1f}GB VRAM)")
            return "cuda", torch.float16, "cuda"
        
        # Check for AMD ROCm GPUs
        if hasattr(torch.version, 'hip') and torch.version.hip is not None:
            try:
                import torch.cuda
                if torch.cuda.is_available():
                    device_name = torch.cuda.get_device_name(0)
                    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    logger.info(f"AMD GPU detected (ROCm): {device_name} ({vram_gb:.1f}GB VRAM)")
                    return "cuda", torch.float16, "hip"
            except Exception as e:
                logger.warning(f"ROCm available but failed to get device info: {e}")
        
        # Check for Intel GPU (集成显卡/独立显卡)
        try:
            import torch
            # Intel GPUs via OpenVINO or DP4A
            if hasattr(torch, 'xpu') and torch.xpu.is_available():
                device_name = torch.xpu.get_device_name(0)
                logger.info(f"Intel GPU detected (XPU): {device_name}")
                return "xpu", torch.float16, "xpu"
        except Exception:
            pass
        
        # Check for Intel GPU via oneDNN
        try:
            import torch
            # Check if running on Intel GPU via oneDNN
            if hasattr(torch, 'backends') and hasattr(torch.backends, 'onednn'):
                torch.backends.onednn.enabled = True
                logger.info("Intel oneDNN backend enabled")
        except Exception:
            pass
        
        # Fallback to CPU
        logger.info("No GPU detected, using CPU")
        return "cpu", torch.float32, "cpu"
        
    except ImportError:
        logger.warning("PyTorch not available, using CPU")
        return "cpu", "float32", "cpu"
    except Exception as e:
        logger.warning(f"Error detecting compute device: {e}, using CPU")
        return "cpu", "float32", "cpu"


class ImageGenerationProcessor:
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    def __init__(self):
        self._pipelines: Dict[str, Any] = {}
        self._current_model = None
        self._device_type, self._dtype, self._device_name = get_compute_device()
        
    def _validate_prompt(self, prompt: str) -> bool:
        if not prompt or len(prompt.strip()) < 3:
            raise ValueError("Prompt must be at least 3 characters")
        return True
    
    def _get_device(self) -> tuple:
        return self._device_type, self._dtype
    
    def _load_pipeline(self, model: str):
        if model in self._pipelines:
            return self._pipelines[model]
        
        if not get_available_models() and model != "sd15":
            logger.warning(f"Model {model} not available, falling back to sd15")
            model = "sd15"
        
        config = MODELS_CONFIG.get(model, MODELS_CONFIG["sd15"])
        model_id = config["model_id"]
        
        device, torch_dtype = self._get_device()
        
        try:
            if model == "flux":
                from diffusers import FluxPipeline
                logger.info(f"Loading FLUX.1 on {device}...")
                pipeline = FluxPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch_dtype,
                )
            elif model == "sdxl":
                from diffusers import StableDiffusionXLPipeline
                logger.info(f"Loading SDXL on {device}...")
                pipeline = StableDiffusionXLPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch_dtype,
                )
            else:
                from diffusers import StableDiffusionPipeline
                logger.info(f"Loading SD 1.5 on {device}...")
                pipeline = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch_dtype,
                )
            
            # Move pipeline to appropriate device
            if device == "cpu":
                pipeline = pipeline.to(device)
            elif device == "xpu":
                # Intel GPU
                try:
                    pipeline = pipeline.to(device)
                except Exception as e:
                    logger.warning(f"XPU not supported, using CPU: {e}")
                    pipeline = pipeline.to("cpu")
            else:
                # NVIDIA CUDA or AMD ROCm
                try:
                    pipeline.enable_model_cpu_offload()
                except Exception:
                    try:
                        pipeline.enable_sequential_cpu_offload()
                    except Exception:
                        pipeline = pipeline.to(device)
            
            self._pipelines[model] = pipeline
            self._current_model = model
            logger.info(f"Model {model} loaded successfully on {device}")
            return pipeline
            
        except Exception as e:
            logger.error(f"Failed to load {model} pipeline: {e}")
            if model != "sd15":
                logger.warning("Falling back to SD 1.5")
                return self._load_pipeline("sd15")
            raise
    
    def _get_pipeline_for_model(self, model: str):
        available = get_available_models()
        if model not in available:
            if available:
                model = available[0]
            else:
                model = "sd15"
        return self._load_pipeline(model)
    
    async def generate_image(
        self,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> dict:
        start_time = time.time()
        
        meta = {**IMAGE_GEN_METADATA_DEFAULTS, **(metadata or {})}
        
        model = meta.get("model", "sdxl")
        style = meta.get("style", "")
        aspect_ratio = meta.get("aspect_ratio", "1:1")
        num_variations = meta.get("num_variations", 1)
        negative_prompt = meta.get("negative_prompt", "")
        num_inference_steps = meta.get("num_inference_steps", 30)
        guidance_scale = meta.get("guidance_scale", 7.5)
        seed = meta.get("seed")
        
        width, height = ASPECT_RATIO_SIZES.get(aspect_ratio, (1024, 1024))
        
        if model == "sd15":
            width = min(width, 512)
            height = min(height, 512)
        
        if style and style in STYLES_CONFIG:
            style_config = STYLES_CONFIG[style]
            if style_config.get("model_id"):
                negative_prompt = negative_prompt or style_config.get("negative_prompt", "")
        
        self._validate_prompt(prompt)
        
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"Generating image (attempt {attempt + 1}/{self.MAX_RETRIES}): {prompt[:50]}...")
                
                pipeline = self._get_pipeline_for_model(model)
                
                generate_kwargs = {
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_inference_steps": num_inference_steps,
                    "guidance_scale": guidance_scale,
                    "negative_prompt": negative_prompt if negative_prompt else None,
                }
                
                if seed is not None:
                    generate_kwargs["seed"] = seed
                
                step_callback = None
                if progress_callback and num_inference_steps:
                    current_step = [0]
                    
                    def step_callback_fn(args):
                        current_step[0] += 1
                        progress_callback(current_step[0], num_inference_steps)
                    
                    step_callback = step_callback_fn
                
                if step_callback:
                    def callback_wrapper(pipeline, step_index, timestep, callback_kwargs):
                        step_callback()
                        return callback_kwargs
                    generate_kwargs["callback"] = callback_wrapper
                
                result = pipeline(**generate_kwargs)
                
                generated_images = result.images[:num_variations]
                output_paths = []
                
                os.makedirs("/app/downloads", exist_ok=True)
                
                for i, image in enumerate(generated_images):
                    output_filename = f"generated_{hash(prompt + str(i))}_{os.urandom(4).hex()}.png"
                    output_path = os.path.join("/app/downloads", output_filename)
                    image.save(output_path)
                    output_paths.append(output_path)
                    logger.info(f"Image {i+1} saved: {output_path}")
                
                elapsed_time = time.time() - start_time
                logger.info(f"Image generation completed in {elapsed_time:.2f}s")
                
                return {
                    "file_paths": output_paths,
                    "file_path": output_paths[0] if output_paths else None,
                    "prompt": prompt,
                    "model": model,
                    "style": style,
                    "aspect_ratio": aspect_ratio,
                    "width": width,
                    "height": height,
                    "num_variations": num_variations,
                    "num_inference_steps": num_inference_steps,
                    "guidance_scale": guidance_scale,
                    "negative_prompt": negative_prompt,
                    "seed": seed,
                    "generation_time": elapsed_time,
                }
                
            except Exception as e:
                last_error = e
                logger.error(f"Image generation failed (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
        
        raise last_error or Exception("Unknown error during image generation")
    
    def clear_cache(self):
        for model in list(self._pipelines.keys()):
            try:
                del self._pipelines[model]
            except Exception:
                pass
        self._pipelines = {}
        self._current_model = None
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        logger.info("Pipeline cache cleared")
