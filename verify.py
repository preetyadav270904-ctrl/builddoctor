import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from git_utils import clone_repo, checkout_commit
from runner import run_tests

def apply_patch(repo_dir, patch_abs_path):
    cmd = ["git", "-C", repo_dir, "apply", "--recount", patch_abs_path]
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res.returncode == 0, res.stdout.strip()

def verify_patch(repo_source, culprit_commit, patch_file):
    abs_patch = Path(patch_file).resolve()
    if not abs_patch.exists():
        print(f"[!] Patch file not found: {abs_patch}")
        sys.exit(1)

    scratch_dir = tempfile.mkdtemp(prefix=".tmp_verify_", dir=os.path.abspath("."))
    print(f"[*] Isolated sandbox: {scratch_dir}")

    try:
        print(f"[*] Checking out culprit commit {culprit_commit[:7]}...")
        clone_repo(repo_source, scratch_dir)
        checkout_commit(scratch_dir, culprit_commit)

        base_code, _ = run_tests(scratch_dir)
        if base_code == 0:
            print("[?] Warning: Culprit commit passed tests without patch.")
        else:
            print(" -> Baseline failure confirmed.")

        print(f"[*] Applying {abs_patch.name}...")
        ok, err_msg = apply_patch(scratch_dir, str(abs_patch))
        if not ok:
            print(f"[!] Git apply rejected patch:\n{err_msg}")
            return False

        print(" -> Patch applied cleanly.")
        print("[*] Running test suite inside container...")
        test_code, test_output = run_tests(scratch_dir)

        print("\n" + "-" * 40)
        if test_code == 0:
            print("VERIFICATION: PASSED (Build Green)")
            print("-" * 40)
            return True
        else:
            print(f"VERIFICATION: FAILED (Exit Code {test_code})")
            print(test_output.strip())
            print("-" * 40)
            return False

    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test candidate patch in clean container environment.")
    parser.add_argument("--repo", default="test_target_repo")
    parser.add_argument("--commit-file", default="culprit_commit.txt")
    parser.add_argument("--commit", default=None)
    parser.add_argument("--patch", default="fix.patch")

    args = parser.parse_args()

    commit = args.commit
    if not commit:
        commit_file_path = Path(args.commit_file)
        if commit_file_path.exists():
            commit = commit_file_path.read_text(encoding="utf-8").strip()
        else:
            print(f"[!] Missing commit reference. Provide --commit or ensure {args.commit_file} exists.")
            sys.exit(1)

    verify_patch(args.repo, commit, args.patch)
