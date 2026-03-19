import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


class AudioPreprocessingError(Exception):
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


def preprocess_audio(
    input_path: str,
    denoise: bool = True,
    normalize: bool = True,
    remove_silence: bool = True,
) -> str:
    if not os.path.exists(input_path):
        raise AudioPreprocessingError(f"Input file not found: {input_path}")

    output_fd, output_path = tempfile.mkstemp(suffix=".wav")
    os.close(output_fd)

    filters = []

    if normalize:
        filters.append("loudnorm=I=-16:LRA=11:TP=-1.5")

    if denoise:
        filters.extend([
            "highpass=f=200",
            "lowpass=f=8000",
        ])

    if remove_silence:
        filters.append(
            "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-40dB:detection=peak"
        )

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
        ]

        if filters:
            cmd.extend(["-af", ",".join(filters)])

        cmd.append(output_path)

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise AudioPreprocessingError("ffmpeg produced empty output file")

        logger.info(f"Audio preprocessed successfully: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg error: {e.stderr}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise AudioPreprocessingError(
            f"ffmpeg preprocessing failed: {e.stderr}",
            details=e.stderr,
        )
    except Exception as e:
        logger.error(f"Audio preprocessing error: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise AudioPreprocessingError(f"Audio preprocessing failed: {e}")


def cleanup_audio(path: str) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
            logger.debug(f"Cleaned up temporary audio file: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup audio file {path}: {e}")
