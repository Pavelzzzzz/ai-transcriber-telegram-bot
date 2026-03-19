import os
import tempfile
from unittest.mock import Mock, patch

import pytest


class TestAudioPreprocessor:
    """Tests for audio preprocessing functionality"""

    @pytest.fixture
    def temp_audio_file(self):
        fd, path = tempfile.mkstemp(suffix=".ogg")
        os.write(fd, b"fake audio data")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def temp_output_file(self):
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        os.remove(path)
        yield path
        if os.path.exists(path):
            os.remove(path)

    @pytest.mark.unit
    def test_preprocess_audio_raises_on_missing_file(self):
        from utils.audio_preprocessor import AudioPreprocessingError, preprocess_audio

        with pytest.raises(AudioPreprocessingError) as exc_info:
            preprocess_audio("/nonexistent/file.ogg")

        assert "Input file not found" in str(exc_info.value)

    @pytest.mark.unit
    def test_cleanup_audio_removes_file(self, temp_audio_file):
        from utils.audio_preprocessor import cleanup_audio

        assert os.path.exists(temp_audio_file)

        cleanup_audio(temp_audio_file)

        assert not os.path.exists(temp_audio_file)

    @pytest.mark.unit
    def test_cleanup_audio_handles_nonexistent_file(self):
        from utils.audio_preprocessor import cleanup_audio

        cleanup_audio("/nonexistent/file.wav")

    @pytest.mark.unit
    def test_cleanup_audio_handles_none(self):
        from utils.audio_preprocessor import cleanup_audio

        cleanup_audio(None)

    @pytest.mark.unit
    def test_preprocess_audio_with_ffmpeg_success(self, temp_audio_file):
        from utils.audio_preprocessor import preprocess_audio

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            with patch("tempfile.mkstemp") as mock_mkstemp:
                mock_mkstemp.return_value = (123, "/tmp/output.wav")

                with patch("os.close"):
                    with patch("os.path.exists", return_value=True):
                        with patch("os.path.getsize", return_value=1024):
                            with patch("os.remove"):
                                result = preprocess_audio(temp_audio_file, denoise=True)

        assert result == "/tmp/output.wav"
        mock_run.assert_called_once()

    @pytest.mark.unit
    def test_preprocess_audio_skip_denoise(self, temp_audio_file):
        from utils.audio_preprocessor import preprocess_audio

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            with patch("tempfile.mkstemp") as mock_mkstemp:
                mock_mkstemp.return_value = (123, "/tmp/output.wav")

                with patch("os.close"):
                    with patch("os.path.exists", return_value=True):
                        with patch("os.path.getsize", return_value=1024):
                            with patch("os.remove"):
                                result = preprocess_audio(
                                    temp_audio_file, denoise=False, normalize=False, remove_silence=False
                                )

        assert result == "/tmp/output.wav"
        call_args = mock_run.call_args[0][0]
        assert "-af" not in call_args

    @pytest.mark.unit
    def test_preprocess_audio_ffmpeg_error(self, temp_audio_file):
        import subprocess

        from utils.audio_preprocessor import AudioPreprocessingError, preprocess_audio

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "ffmpeg", stderr="File not found"
            )

            with patch("tempfile.mkstemp") as mock_mkstemp:
                mock_mkstemp.return_value = (123, "/tmp/output.wav")

                with patch("os.close"):
                    with patch("os.path.exists", return_value=True):
                        with patch("os.remove"):
                            with pytest.raises(AudioPreprocessingError) as exc_info:
                                preprocess_audio(temp_audio_file)

        assert "ffmpeg preprocessing failed" in str(exc_info.value)

    @pytest.mark.unit
    def test_preprocess_audio_empty_output(self, temp_audio_file):
        from utils.audio_preprocessor import AudioPreprocessingError, preprocess_audio

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            with patch("tempfile.mkstemp") as mock_mkstemp:
                mock_mkstemp.return_value = (123, "/tmp/output.wav")

                with patch("os.close"):
                    with patch("os.path.exists", return_value=True):
                        with patch("os.path.getsize", return_value=0):
                            with patch("os.remove"):
                                with pytest.raises(AudioPreprocessingError) as exc_info:
                                    preprocess_audio(temp_audio_file)

        assert "empty output" in str(exc_info.value)
