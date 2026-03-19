#!/usr/bin/env python3
"""
Validate that requirements.txt files match Dockerfile dependencies.

This script checks:
1. All services have a requirements.txt file
2. Required packages (sqlalchemy, etc.) are present in services that import them
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SERVICES_DIR = ROOT / "services"
DOCKERFILES = {
    "bot_service": SERVICES_DIR / "bot_service" / "Dockerfile",
    "ocr_service": SERVICES_DIR / "ocr_service" / "Dockerfile",
    "tts_service": SERVICES_DIR / "tts_service" / "Dockerfile",
    "transcription_service": SERVICES_DIR / "transcription_service" / "Dockerfile",
    "image_gen_service": SERVICES_DIR / "image_gen_service" / "Dockerfile",
}

REQUIREMENTS_FILES = {
    "bot_service": SERVICES_DIR / "bot_service" / "requirements.txt",
    "ocr_service": SERVICES_DIR / "ocr_service" / "requirements.txt",
    "tts_service": SERVICES_DIR / "tts_service" / "requirements.txt",
    "transcription_service": SERVICES_DIR / "transcription_service" / "requirements.txt",
    "image_gen_service": SERVICES_DIR / "image_gen_service" / "requirements.txt",
}

PACKAGE_IMPORTS = {
    "sqlalchemy": ["ocr_service", "tts_service", "image_gen_service"],
    "gtts": ["bot_service", "tts_service"],
    "kafka-python": [
        "bot_service",
        "ocr_service",
        "tts_service",
        "transcription_service",
        "image_gen_service",
    ],
    "torch": ["transcription_service", "image_gen_service"],
    "openai-whisper": ["transcription_service"],
    "diffusers": ["image_gen_service"],
    "transformers": ["image_gen_service"],
    "pytesseract": ["ocr_service"],
    "Pillow": ["ocr_service", "image_gen_service"],
}

CRITICAL_PACKAGES = {
    "sqlalchemy": "sqlalchemy>=2.0.0",
    "psycopg2-binary": "psycopg2-binary>=2.9.9",
    "gtts": "gtts>=2.5.0",
    "openai-whisper": "openai-whisper",
    "torch": "torch>=2.0.0",
    "torchvision": "torchvision>=0.15.0",
    "torchaudio": "torchaudio>=2.0.0",
}


def check_requirements_exists():
    """Check that all services have requirements.txt files."""
    errors = []

    for service, req_file in REQUIREMENTS_FILES.items():
        if not req_file.exists():
            errors.append(f"Missing requirements.txt: {req_file}")

    return errors


def get_installed_packages(req_file: Path) -> set:
    """Parse requirements.txt and return set of package names."""
    if not req_file.exists():
        return set()

    packages = set()
    with open(req_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                pkg_name = re.split(r"[>=<!]", line)[0].strip()
                packages.add(pkg_name.lower())
    return packages


def get_service_imports(service_dir: Path) -> set:
    """Parse all Python files in a service and extract imports."""
    imports = set()

    for py_file in service_dir.rglob("*.py"):
        if "test" in py_file.name or "__pycache__" in str(py_file):
            continue
        try:
            with open(py_file) as f:
                content = f.read()

            import_pattern = r"^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
            for match in re.finditer(import_pattern, content, re.MULTILINE):
                module = match.group(1)
                if module not in (
                    "os",
                    "sys",
                    "re",
                    "datetime",
                    "typing",
                    "logging",
                    "json",
                    "uuid",
                ):
                    imports.add(module)
        except Exception:
            pass

    return imports


def check_critical_packages():
    """Check that critical packages are in the right requirements.txt files."""
    errors = []

    for service, req_file in REQUIREMENTS_FILES.items():
        if not req_file.exists():
            continue

        packages = get_installed_packages(req_file)

        service_dir = SERVICES_DIR / service
        imports = get_service_imports(service_dir)

        service_common_dir = service_dir.parent / "common"
        if service_common_dir.exists():
            imports.update(get_service_imports(service_common_dir))

        package_mapping = {
            "sqlalchemy": "sqlalchemy",
            "gtts": "gtts",
            "kafka": "kafka-python",
            "torch": "torch",
            "whisper": "openai-whisper",
            "diffusers": "diffusers",
            "transformers": "transformers",
            "pytesseract": "pytesseract",
            "PIL": "Pillow",
            "pillow": "Pillow",
        }

        for imp in imports:
            normalized_imp = imp.lower()
            if normalized_imp in package_mapping:
                pkg = package_mapping[normalized_imp]
                pkg_name = pkg.replace("-", "_").lower()
                if pkg_name not in packages and pkg.lower() not in packages:
                    errors.append(f"{service}: missing '{pkg}' (imported as '{imp}')")

    return errors


def check_dockerfile_paths():
    """Check that Dockerfiles correctly reference their requirements.txt files."""
    errors = []

    for service, dockerfile in DOCKERFILES.items():
        if not dockerfile.exists():
            continue

        with open(dockerfile) as f:
            content = f.read()

        expected_path = f"services/{service}/requirements.txt"
        if expected_path not in content:
            errors.append(f"{service}: Dockerfile doesn't reference {expected_path}")

    return errors


def main():
    all_errors = []

    print("Checking requirements.txt files...")

    errors = check_requirements_exists()
    if errors:
        all_errors.extend(errors)
        print("  FAIL: Missing requirements.txt files")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  OK: All services have requirements.txt")

    print("\nChecking critical packages...")
    errors = check_critical_packages()
    if errors:
        all_errors.extend(errors)
        print("  FAIL: Missing critical packages")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  OK: All critical packages present")

    print("\nChecking Dockerfile paths...")
    errors = check_dockerfile_paths()
    if errors:
        all_errors.extend(errors)
        print("  FAIL: Incorrect Dockerfile paths")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  OK: Dockerfile paths correct")

    print()
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) found")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("SUCCESS: All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
