import subprocess
import time

import pytest


def wait_for_postgres(host, port, timeout=30):
    """Wait for PostgreSQL to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def wait_for_kafka(host, port, timeout=60):
    """Wait for Kafka to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            from kafka import KafkaProducer

            producer = KafkaProducer(
                bootstrap_servers=f"{host}:{port}",
                request_timeout_ms=5000,
                api_version_auto_timeout_ms=5000,
            )
            producer.close()
            return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for integration tests."""
    container_id = None
    try:
        # Pull image first
        subprocess.run(["docker", "pull", "postgres:15-alpine"], check=True, capture_output=True)

        # Run container
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "-e",
                "POSTGRES_DB=test_db",
                "-e",
                "POSTGRES_USER=test_user",
                "-e",
                "POSTGRES_PASSWORD=test_pass",
                "-p",
                "5433:5432",
                "--network=host",
                "postgres:15-alpine",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        container_id = result.stdout.strip()

        # Wait for PostgreSQL to be ready
        if not wait_for_postgres("localhost", 5433):
            raise RuntimeError("PostgreSQL did not start in time")

        # Initialize database
        subprocess.run(
            [
                "docker",
                "exec",
                container_id,
                "psql",
                "-U",
                "test_user",
                "-d",
                "test_db",
                "-c",
                "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, data TEXT);",
            ],
            check=True,
            capture_output=True,
        )

        yield {
            "host": "localhost",
            "port": 5433,
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass",
        }

    finally:
        if container_id:
            subprocess.run(["docker", "stop", container_id], capture_output=True)


@pytest.fixture(scope="session")
def kafka_container():
    """Start Kafka container for integration tests."""
    zookeeper_container = None
    kafka_container_id = None

    try:
        # Pull images
        subprocess.run(
            ["docker", "pull", "confluentinc/cp-zookeeper:7.5.0"], check=True, capture_output=True
        )
        subprocess.run(
            ["docker", "pull", "confluentinc/cp-kafka:7.5.0"], check=True, capture_output=True
        )

        # Start Zookeeper
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "-e",
                "ZOOKEEPER_CLIENT_PORT=2181",
                "-e",
                "ZOOKEEPER_TICK_TIME=2000",
                "-p",
                "2181:2181",
                "--network=host",
                "confluentinc/cp-zookeeper:7.5.0",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        zookeeper_container = result.stdout.strip()
        time.sleep(5)  # Wait for Zookeeper to start

        # Start Kafka
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "-e",
                "KAFKA_BROKER_ID=1",
                "-e",
                "KAFKA_ZOOKEEPER_CONNECT=localhost:2181",
                "-e",
                "KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092",
                "-e",
                "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT",
                "-e",
                "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1",
                "-p",
                "9092:9092",
                "--network=host",
                "confluentinc/cp-kafka:7.5.0",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        kafka_container_id = result.stdout.strip()

        # Wait for Kafka to be ready
        if not wait_for_kafka("localhost", 9092):
            raise RuntimeError("Kafka did not start in time")

        yield {
            "bootstrap_servers": "localhost:9092",
            "topics": {
                "tasks_ocr": "tasks.ocr.test",
                "tasks_transcribe": "tasks.transcribe.test",
                "tasks_image_gen": "tasks.image_gen.test",
                "results_ocr": "results.ocr.test",
                "results_transcribe": "results.transcribe.test",
                "results_image_gen": "results.image_gen.test",
                "notifications": "notifications.test",
            },
        }

    finally:
        if kafka_container_id:
            subprocess.run(["docker", "stop", kafka_container_id], capture_output=True)
        if zookeeper_container:
            subprocess.run(["docker", "stop", zookeeper_container], capture_output=True)
