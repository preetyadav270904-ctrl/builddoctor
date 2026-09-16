import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from git_utils import clone_repo, get_commits_in_range, checkout_commit, get_commit_diff
from runner import build_runner_image, run_tests
from patcher import generate_patch
from verify import verify_patch

def run_pipeline(repo_source, good_hash, bad_hash, model="qwen/qwen3.8-27b"):
    print("=" * 55)
    print(" BuildDoctor - Automated CI Triage & Repair")
    print("=" * 55)

    build_runner_image()

    bisect_dir = tempfile.mkdtemp(prefix=".tmp_bisect_", dir=os.path.abspath("."))
    culprit = None
    fail_log = None

    try:
        print(f"[*] Cloning {repo_source} into scratch workspace...")
        clone_repo(repo_source, bisect_dir)

        commits = get_commits_in_range(bisect_dir, good_hash, bad_hash)
        print(f"[*] Bisecting {len(commits)} commits...")

        for i, commit in enumerate(commits, 1):
            short = commit[:7]
            checkout_commit(bisect_dir, commit)
            code, out = run_tests(bisect_dir)

            if code == 0:
                print(f"    [{i}/{len(commits)}] {short} -> PASS")
            else:
                print(f"    [{i}/{len(commits)}] {short} -> FAIL (Exit code {code})")
                culprit = commit
                fail_log = out
                break

        if not culprit:
            print("[!] No failing commit discovered in specified range.")
            sys.exit(0)

        print(f"[+] Culprit identified: {culprit}")
        diff_content = get_commit_diff(bisect_dir, culprit)

        # Cache artifacts for debugging
        Path("culprit_commit.txt").write_text(culprit, encoding="utf-8")
        Path("culprit_diff.diff").write_text(diff_content, encoding="utf-8")
        Path("failing_test.log").write_text(fail_log, encoding="utf-8")

    finally:
        shutil.rmtree(bisect_dir, ignore_errors=True)

    print("\n[*] Requesting LLM patch...")
    generate_patch(
        diff_file="culprit_diff.diff",
        log_file="failing_test.log",
        repo_dir=repo_source if os.path.isdir(repo_source) else ".",
        output_patch_file="fix.patch",
        model=model
    )

    print("\n[*] Running isolated verification container...")
    ok = verify_patch(
        repo_source=repo_source,
        culprit_commit=culprit,
        patch_file="fix.patch"
    )

    print("\n" + "=" * 55)
    print(" PIPELINE SUMMARY")
    print("=" * 55)
    print(f" Target Repo:   {repo_source}")
    print(f" Culprit Hash:  {culprit}")
    print(f" Patch Status:  {'RESOLVED' if ok else 'FAILED'}")
    if ok:
        print(" -> Patch verified green. Run 'git apply fix.patch' to adopt.")
    print("=" * 55)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-end CI triage runner.")
    parser.add_argument("--repo", required=True, help="Local repo path or remote URL")
    parser.add_argument("--good", required=True, help="Known passing commit")
    parser.add_argument("--bad", required=True, help="Known broken commit")
    parser.add_argument("--model", default="qwen/qwen3.8-27b", help="Groq model ID")

    args = parser.parse_args()
    run_pipeline(args.repo, args.good, args.bad, args.model)
