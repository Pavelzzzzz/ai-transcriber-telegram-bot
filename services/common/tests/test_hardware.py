import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestHardwareConfig:
    """Test hardware configuration constants"""

    def test_models_config_structure(self):
        from services.common.hardware import MODELS_CONFIG

        for model_id, config in MODELS_CONFIG.items():
            assert "name" in config
            assert "model_id" in config
            assert "min_vram_gb" in config
            assert "default_size" in config
            assert "description" in config

    def test_sd15_config(self):
        from services.common.hardware import MODELS_CONFIG

        assert MODELS_CONFIG["sd15"]["min_vram_gb"] == 0
        assert MODELS_CONFIG["sd15"]["default_size"] == (512, 512)

    def test_sdxl_config(self):
        from services.common.hardware import MODELS_CONFIG

        assert MODELS_CONFIG["sdxl"]["min_vram_gb"] == 8
        assert MODELS_CONFIG["sdxl"]["default_size"] == (1024, 1024)

    def test_flux_config(self):
        from services.common.hardware import MODELS_CONFIG

        assert MODELS_CONFIG["flux"]["min_vram_gb"] == 16
        assert MODELS_CONFIG["flux"]["default_size"] == (1024, 1024)

    def test_styles_config_structure(self):
        from services.common.hardware import STYLES_CONFIG

        for style_id, config in STYLES_CONFIG.items():
            assert "name" in config
            assert "model_id" in config
            assert "negative_prompt" in config

    def test_aspect_ratio_sizes(self):
        from services.common.hardware import ASPECT_RATIO_SIZES

        assert ASPECT_RATIO_SIZES["1:1"] == (1024, 1024)
        assert ASPECT_RATIO_SIZES["16:9"] == (1024, 576)
        assert ASPECT_RATIO_SIZES["9:16"] == (576, 1024)
        assert ASPECT_RATIO_SIZES["4:3"] == (1024, 768)
        assert ASPECT_RATIO_SIZES["3:2"] == (1024, 683)
        assert ASPECT_RATIO_SIZES["2:3"] == (683, 1024)

    def test_aspect_ratio_names(self):
        from services.common.hardware import ASPECT_RATIO_NAMES

        assert "1:1" in ASPECT_RATIO_NAMES
        assert "16:9" in ASPECT_RATIO_NAMES
        assert "9:16" in ASPECT_RATIO_NAMES
        assert "4:3" in ASPECT_RATIO_NAMES

    def test_variation_labels(self):
        from services.common.hardware import VARIATION_LABELS

        for num in [1, 2, 3, 4]:
            assert num in VARIATION_LABELS

    def test_get_model_info(self):
        from services.common.hardware import MODELS_CONFIG, get_model_info

        info = get_model_info("sdxl")
        assert info == MODELS_CONFIG["sdxl"]

        info = get_model_info("unknown")
        assert info is None

    def test_get_style_info(self):
        from services.common.hardware import STYLES_CONFIG, get_style_info

        info = get_style_info("photorealistic")
        assert info == STYLES_CONFIG["photorealistic"]

        info = get_style_info("unknown")
        assert info is None

    def test_get_aspect_ratio_size(self):
        from services.common.hardware import get_aspect_ratio_size

        assert get_aspect_ratio_size("1:1") == (1024, 1024)
        assert get_aspect_ratio_size("16:9") == (1024, 576)
        assert get_aspect_ratio_size("unknown") == (1024, 1024)

    def test_get_style_display_name(self):
        from services.common.hardware import get_style_display_name

        assert get_style_display_name("photorealistic") == "Фотореализм"
        assert get_style_display_name("anime") == "Аниме"
        assert get_style_display_name("unknown") == "unknown"


class TestHardwareFunctionsSimple:
    """Test hardware detection functions - simple tests"""

    def test_get_vram_gb_import_error(self):
        from services.common.hardware import get_vram_gb

        result = get_vram_gb()
        assert result == 0

    def test_get_available_models_fallback(self):
        from services.common.hardware import get_available_models

        result = get_available_models()
        assert "sd15" in result

    def test_is_model_available(self):
        from services.common.hardware import is_model_available

        assert is_model_available("sd15") is True
        assert is_model_available("sdxl") is False
        assert is_model_available("flux") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
