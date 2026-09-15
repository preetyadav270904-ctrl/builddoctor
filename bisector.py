import argparse
import os
import shutil
import tempfile
from git_utils import clone_repo, get_commits_in_range, checkout_commit, get_commit_diff
from runner import run_tests

def run_linear_bisect(repo_source, good_hash, bad_hash):
    work_dir = tempfile.mkdtemp(prefix="builddoctor_repo_")
    print(f"[Bisect] Working in temp directory: {work_dir}")

    try:
        print(f"[Bisect] Cloning source: {repo_source}...")
        clone_repo(repo_source, work_dir)

        commits = get_commits_in_range(work_dir, good_hash, bad_hash)
        print(f"[Bisect] Found {len(commits)} commits to test in range.")

        first_failure = None
        failure_log = None

        for idx, commit in enumerate(commits, 1):
            short_hash = commit[:7]
            print(f"[{idx}/{len(commits)}] Checking out {short_hash}...")
            checkout_commit(work_dir, commit)

            print(f"[{idx}/{len(commits)}] Running pytest inside Docker...")
            exit_code, log_output = run_tests(work_dir)

            if exit_code == 0:
                print(f"  -> {short_hash}: PASSED")
            else:
                print(f"  -> {short_hash}: FAILED (exit code {exit_code})")
                first_failure = commit
                failure_log = log_output
                break

        if not first_failure:
            print("[Bisect] All commits passed. No breaking commit detected.")
            return

        print(f"\n[Bisect] Culprit identified: {first_failure}")
        diff_text = get_commit_diff(work_dir, first_failure)

        # Save artifacts locally for Phase 3
        with open("culprit_commit.txt", "w", encoding="utf-8") as f:
            f.write(first_failure)
        with open("culprit_diff.diff", "w", encoding="utf-8") as f:
            f.write(diff_text)
        with open("failing_test.log", "w", encoding="utf-8") as f:
            f.write(failure_log)

        print("[Bisect] Saved artifacts:")
        print("  - culprit_commit.txt")
        print("  - culprit_diff.diff")
        print("  - failing_test.log")

    finally:
        # Clean up temporary clone directory
        shutil.rmtree(work_dir, ignore_errors=True)
        print("[Bisect] Cleaned up temporary directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Linear commit bisection using Docker test runner.")
    parser.add_argument("--repo", required=True, help="Path to local git repo or git clone URL")
    parser.add_argument("--good", required=True, help="Known good commit hash")
    parser.add_argument("--bad", required=True, help="Known bad commit hash")

    args = parser.parse_args()
    run_linear_bisect(args.repo, args.good, args.bad)
