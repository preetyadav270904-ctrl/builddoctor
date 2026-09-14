import subprocess
import sys
import os

IMAGE_NAME = "builddoctor-runner"

def build_runner_image():
    print("[Runner] Building base Docker image...")
    cmd = ["docker", "build", "-t", IMAGE_NAME, "."]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if result.returncode != 0:
        print("[Runner] Failed to build base image:")
        print(result.stdout)
        sys.exit(1)
    print("[Runner] Base image built successfully.\n")

def run_tests(project_dir, test_target=None):
    """
    Mounts a project directory into /workspace in the runner container,
    executes pytest, and returns (exit_code, output_text).
    """
    abs_project_dir = os.path.abspath(project_dir)
    if not os.path.isdir(abs_project_dir):
        print(f"[Runner] Error: Directory '{abs_project_dir}' does not exist.")
        sys.exit(1)

    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{abs_project_dir}:/workspace",
        "-w", "/workspace",
        IMAGE_NAME,
        "pytest"
    ]

    if test_target:
        docker_cmd.append(test_target)

    # Subprocess execution capturing raw stdout and stderr together with safe UTF-8 decoding
    result = subprocess.run(
        docker_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    return result.returncode, result.stdout

if __name__ == "__main__":
    build_runner_image()

    dummy_dir = os.path.join(os.path.dirname(__file__), "dummy_project")

    # Run passing test target
    print("--- Running Passing Test Suite ---")
    code_pass, out_pass = run_tests(dummy_dir, test_target="test_pass.py")
    print(f"EXIT CODE: {code_pass}")
    print(out_pass.strip())
    print("\n" + "="*40 + "\n")

    # Run failing test target
    print("--- Running Failing Test Suite ---")
    code_fail, out_fail = run_tests(dummy_dir, test_target="test_fail.py")
    print(f"EXIT CODE: {code_fail}")
    print(out_fail.strip())
