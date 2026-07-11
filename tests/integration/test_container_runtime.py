from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.request

import pytest


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _skip_on_docker_access_error(result: subprocess.CompletedProcess[str]) -> None:
    message = f"{result.stdout}\n{result.stderr}".lower()
    if "permission denied while trying to connect to the docker api" in message:
        pytest.skip("docker daemon access is not available in this environment")
    if "cannot connect to the docker daemon" in message:
        pytest.skip("docker daemon access is not available in this environment")


def test_container_builds_and_serves_health_endpoint():
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("docker is not available")

    image = "devops-career-agent:container-test"
    container_name = "devops-career-agent-container-test"
    port = 18080

    build = _run_command([docker, "build", "-t", image, "."])
    _skip_on_docker_access_error(build)
    assert build.returncode == 0, f"docker build failed\nstdout:\n{build.stdout}\nstderr:\n{build.stderr}"

    run = _run_command(
        [
            docker,
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"127.0.0.1:{port}:8000",
            "--env-file",
            ".env.example",
            image,
        ]
    )
    _skip_on_docker_access_error(run)
    assert run.returncode == 0, f"docker run failed\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"

    try:
        health_url = f"http://127.0.0.1:{port}/health"
        deadline = time.time() + 90
        response_payload = None

        while time.time() < deadline:
            try:
                with urllib.request.urlopen(health_url, timeout=2) as response:
                    response_payload = json.loads(response.read().decode("utf-8"))
                    if response.status == 200 and response_payload.get("status") == "ok":
                        break
            except Exception:
                time.sleep(1)
        else:
            logs = _run_command([docker, "logs", container_name])
            raise AssertionError(
                "container did not become healthy\n"
                f"stdout:\n{logs.stdout}\n"
                f"stderr:\n{logs.stderr}\n"
                f"last_response:\n{response_payload}"
            )

        assert response_payload == {"status": "ok"}
    finally:
        _run_command([docker, "rm", "-f", container_name])
