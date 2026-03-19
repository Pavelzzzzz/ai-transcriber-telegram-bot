import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "asyncio: Async tests")
    config.addinivalue_line("markers", "network: Tests that require network access")


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires Kafka, database, etc.)",
    )


def pytest_collection_modifyitems(config, items):
    run_integration = config.getoption("--run-integration", default=False)
    excluded_services = ["transcription_service", "tts_service", "ocr_service", "image_gen_service"]

    for item in list(items):
        if not run_integration:
            for service in excluded_services:
                if service in str(item.fspath):
                    items.remove(item)
                    break
                    continue
            else:
                if "integration" in item.keywords or "network" in item.keywords:
                    item.add_marker(
                        pytest.mark.skip(
                            reason="Integration/network tests skipped. Use --run-integration to run."
                        )
                    )
