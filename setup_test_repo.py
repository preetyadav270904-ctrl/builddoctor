import os
import subprocess

REPO_DIR = os.path.abspath("test_target_repo")

def run(cmd):
    subprocess.run(cmd, cwd=REPO_DIR, shell=True, check=True, stdout=subprocess.DEVNULL)

def create_sample_git_history():
    if os.path.exists(REPO_DIR):
        import shutil
        shutil.rmtree(REPO_DIR, ignore_errors=True)

    os.makedirs(REPO_DIR, exist_ok=True)

    # Initialize Git
    run("git init")
    run("git config user.name 'Builder'")
    run("git config user.email 'builder@example.com'")

    # Commit 1: Passing baseline
    with open(os.path.join(REPO_DIR, "math_utils.py"), "w") as f:
        f.write("def multiply(a, b):\n    return a * b\n")
    with open(os.path.join(REPO_DIR, "test_math.py"), "w") as f:
        f.write("from math_utils import multiply\ndef test_multiply():\n    assert multiply(2, 4) == 8\n")
    run("git add .")
    run('git commit -m "Commit 1: baseline passing tests"')
    res = subprocess.run("git rev-parse HEAD", cwd=REPO_DIR, shell=True, capture_output=True, text=True)
    c1 = res.stdout.strip()

    # Commit 2: Harmless change (still passes)
    with open(os.path.join(REPO_DIR, "README.md"), "w") as f:
        f.write("# Math Repo\n")
    run("git add .")
    run('git commit -m "Commit 2: added documentation"')
    res = subprocess.run("git rev-parse HEAD", cwd=REPO_DIR, shell=True, capture_output=True, text=True)
    c2 = res.stdout.strip()

    # Commit 3: Introduce breaking bug
    with open(os.path.join(REPO_DIR, "math_utils.py"), "w") as f:
        f.write("def multiply(a, b):\n    return a + b\n")  # Broken logic!
    run("git add .")
    run('git commit -m "Commit 3: refactored multiply with bug"')
    res = subprocess.run("git rev-parse HEAD", cwd=REPO_DIR, shell=True, capture_output=True, text=True)
    c3 = res.stdout.strip()

    print("\nSample Git Repository Created!")
    print(f"Repo Location: {REPO_DIR}")
    print(f"Good Commit (Commit 1): {c1}")
    print(f"Neutral Commit (Commit 2): {c2}")
    print(f"Bad Commit  (Commit 3): {c3}")
    print(f"\nRun bisect with:\npython bisect.py --repo {REPO_DIR} --good {c1} --bad {c3}\n")

if __name__ == "__main__":
    create_sample_git_history()
