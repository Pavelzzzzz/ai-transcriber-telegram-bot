import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class ImageGenerationProcessor:
    def __init__(self, model_id: str = "stabilityai/stable-diffusion-xl-base-1.0"):
        self.model_id = model_id
        self._pipeline = None
    
    def _validate_prompt(self, prompt: str) -> bool:
        if not prompt or len(prompt.strip()) < 3:
            raise ValueError("Prompt must be at least 3 characters")
        return True
    
    def _get_pipeline(self):
        if self._pipeline is None:
            try:
                import torch
                from diffusers import StableDiffusionXLPipeline
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                torch_dtype = torch.float16 if device == "cuda" else torch.float32
                
                logger.info(f"Loading Stable Diffusion XL on {device}...")
                
                self._pipeline = StableDiffusionXLPipeline.from_pretrained(
                    self.model_id,
                    torch_dtype=torch_dtype,
                )
                
                if device == "cuda":
                    self._pipeline.enable_model_cpu_offload()
                else:
                    self._pipeline = self._pipeline.to(device)
                
                logger.info("Stable Diffusion XL loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load SDXL pipeline: {e}")
                raise
        
        return self._pipeline
    
    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5
    ) -> dict:
        try:
            logger.info(f"Generating image for prompt: {prompt[:50]}...")
            
            self._validate_prompt(prompt)
            
            pipe = self._get_pipeline()
            
            result = pipe(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
            )
            
            image = result.images[0]
            
            output_filename = f"generated_{hash(prompt)}_{os.urandom(4).hex()}.png"
            output_path = os.path.join("downloads", output_filename)
            os.makedirs("downloads", exist_ok=True)
            image.save(output_path)
            
            logger.info(f"Image generated: {output_path}")
            
            return {
                "file_path": output_path,
                "prompt": prompt,
                "width": width,
                "height": height,
                "model": self.model_id,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise
