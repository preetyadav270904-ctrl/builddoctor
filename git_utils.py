import subprocess
import os

def run_git(args, cwd):
    """Runs a git command in the target directory and returns (exit_code, stdout)."""
    cmd = ["git"] + args
    result = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return result.returncode, result.stdout.strip()

def clone_repo(repo_path_or_url, target_dir):
    """Clones a remote URL or a local git repo directory."""
    os.makedirs(target_dir, exist_ok=True)
    code, out = run_git(["clone", repo_path_or_url, target_dir], cwd=None)
    if code != 0:
        raise RuntimeError(f"Failed to clone repository: {out}")

def get_commits_in_range(repo_dir, good_hash, bad_hash):
    """
    Returns a chronological list of commits from good_hash to bad_hash (inclusive).
    Uses git rev-list --ancestry-path with --reverse.
    """
    # git rev-list good..bad returns commits after good up to bad
    # We include good_hash explicitly at the start
    args = ["rev-list", "--reverse", f"{good_hash}..{bad_hash}"]
    code, out = run_git(args, cwd=repo_dir)
    if code != 0:
        raise RuntimeError(f"Failed to retrieve commit list: {out}")

    intermediate_commits = [c for c in out.splitlines() if c]
    return [good_hash] + intermediate_commits

def checkout_commit(repo_dir, commit_hash):
    """Checks out a specific commit in detached HEAD state."""
    code, out = run_git(["checkout", commit_hash], cwd=repo_dir)
    if code != 0:
        raise RuntimeError(f"Failed to checkout {commit_hash}: {out}")

def get_commit_diff(repo_dir, commit_hash):
    """Extracts the git diff introduced by commit_hash compared to its parent."""
    # commit_hash^! shows the diff for that specific commit
    code, out = run_git(["show", "--format=", commit_hash], cwd=repo_dir)
    if code != 0:
        # Fallback to parent diff if ^! syntax fails
        code, out = run_git(["diff", f"{commit_hash}~1", commit_hash], cwd=repo_dir)
    return out
