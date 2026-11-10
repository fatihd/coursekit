#!/usr/bin/env python3
"""Verify a released course is served by Docker as a read-only static site (progress lives in the browser)."""

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def run(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def wait_for(url, attempts=50):
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return response.read()
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"course did not become available at {url}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("course", help="course name, e.g. biblical-hebrew-davidson")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    base = Path(tempfile.mkdtemp(prefix="docker-course-"))
    released = base / "released"
    image = "lang-research-docker-test"
    container = None
    failures = []

    try:
        release = run([sys.executable, "scripts/release-course", args.course, "--out", str(released)])
        if release.returncode != 0:
            raise RuntimeError(release.stdout + release.stderr)

        build = run(["docker", "build", "--tag", image, str(released)])
        if build.returncode != 0:
            raise RuntimeError(build.stdout + build.stderr)

        def start():
            started = run(
                [
                    "docker", "run", "--rm", "--detach",
                    "--publish", f"127.0.0.1:{args.port}:8000",
                    "--volume", f"{released}:/course:ro",
                    image,
                ]
            )
            if started.returncode != 0:
                raise RuntimeError(started.stdout + started.stderr)
            return started.stdout.strip()

        url = f"http://127.0.0.1:{args.port}"
        container = start()
        shell = wait_for(url + "/app/index.html").decode("utf-8")
        if "id=\"app\"" not in shell:
            failures.append("Docker-served app shell was not returned")

        if (released / "progress").exists():
            failures.append("release still ships a progress/ folder")
        engine = wait_for(url + "/engine/store.js").decode("utf-8")
        if "exportProgress" not in engine or "__api" in engine:
            failures.append("served engine is not the browser-only progress version")

        run(["docker", "stop", container])
        container = None
        container = start()
        wait_for(url + "/app/index.html")
        print(f"Docker course URL: {url}/app/index.html")
    except Exception as exc:
        failures.append(str(exc))
    finally:
        if container:
            run(["docker", "stop", container])
        run(["docker", "rmi", image])
        shutil.rmtree(base, ignore_errors=True)

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("E2E-DOCKER PASS — fresh release served read-only by Docker (restart OK)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
