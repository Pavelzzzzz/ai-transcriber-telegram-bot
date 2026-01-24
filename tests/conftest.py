# Моки для AI зависимостей в тестовой среде
import sys
from unittest.mock import MagicMock

# Mock AI зависимости
sys.modules['whisper'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['pytesseract'] = MagicMock()
sys.modules['scipy'] = MagicMock()
sys.modules['scipy.io'] = MagicMock()
sys.modules['scipy.io.wavfile'] = MagicMock()
sys.modules['numpy'] = MagicMock()

# Настройка моков
sys.modules['whisper'].load_model = MagicMock(return_value=MagicMock())
sys.modules['torch'].cuda = MagicMock()
sys.modules['torch'].cuda.is_available = MagicMock(return_value=False)
sys.modules['PIL'].Image = MagicMock()
sys.modules['pytesseract'].image_to_string = MagicMock(return_value="Test text")
sys.modules['scipy'].io = MagicMock()
sys.modules['scipy'].io.wavfile = MagicMock()
sys.modules['scipy'].io.wavfile.write = MagicMock()
sys.modules['numpy'].array = MagicMock(return_value=[0.1, 0.2, 0.3])