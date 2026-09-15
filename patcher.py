import argparse
import os
import re
import sys
from pathlib import Path
from groq import Groq

PROMPTS_DIR = Path(__file__).parent / "prompts"

def _recalc_hunk(lines):
    old_c = sum(1 for line in lines if line.startswith("-") or (not line.startswith("+") and not line.startswith("\\")))
    new_c = sum(1 for line in lines if line.startswith("+") or (not line.startswith("-") and not line.startswith("\\")))
    return f"@@ -1,{old_c} +1,{new_c} @@"

def clean_patch(raw_text: str) -> str:
    cleaned = raw_text.strip()

    cleaned = re.sub(r"^```(?:diff|patch)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)

    start_idx = cleaned.find("--- a/")
    if start_idx != -1:
        cleaned = cleaned[start_idx:]

    output = []
    hunk = []
    in_hunk = False

    for line in cleaned.splitlines():
        if line.startswith("@@"):
            if in_hunk and hunk:
                output.append(_recalc_hunk(hunk))
                output.extend(hunk)
                hunk = []
            in_hunk = True
        elif in_hunk:
            hunk.append(line)
        else:
            output.append(line)

    if in_hunk and hunk:
        output.append(_recalc_hunk(hunk))
        output.extend(hunk)

    return "\n".join(output).strip() + "\n"

def _get_target_file(diff_text: str):
    m = re.search(r"\+\+\+ b/(.+)", diff_text)
    return m.group(1).strip() if m else None

def generate_patch(diff_file, log_file, repo_dir="test_target_repo", output_patch_file="fix.patch", model="qwen/qwen3.8-27b"):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[!] Error: GROQ_API_KEY environment variable missing.")
        sys.exit(1)

    diff_path = Path(diff_file)
    log_path = Path(log_file)
    if not diff_path.exists() or not log_path.exists():
        print(f"[!] Required context files missing: {diff_file} or {log_file}")
        sys.exit(1)

    diff_content = diff_path.read_text(encoding="utf-8")
    log_content = log_path.read_text(encoding="utf-8")

    target_file = _get_target_file(diff_content) or "source file"
    file_snippet = ""

    target_path = Path(repo_dir) / target_file
    if target_path.exists():
        file_snippet = f"\nCURRENT CODE ({target_file}):\n{target_path.read_text(encoding='utf-8')}"

    # Load prompt templates
    sys_prompt = (PROMPTS_DIR / "patch_system.txt").read_text(encoding="utf-8")
    user_tpl = (PROMPTS_DIR / "patch_user.txt").read_text(encoding="utf-8")
    user_prompt = user_tpl.format(
        target_file=target_file,
        log_content=log_content,
        file_content_snippet=file_snippet
    )

    print(f"[*] Querying Groq ({model})...")
    client = Groq(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
    except Exception as e:
        print(f"[!] Groq request failed: {e}")
        sys.exit(1)

    raw_patch = completion.choices[0].message.content
    final_patch = clean_patch(raw_patch)

    Path(output_patch_file).write_text(final_patch, encoding="utf-8")
    print(f"[+] Saved clean patch to {output_patch_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate fix patch using Groq LLM.")
    parser.add_argument("--diff", default="culprit_diff.diff")
    parser.add_argument("--log", default="failing_test.log")
    parser.add_argument("--repo", default="test_target_repo")
    parser.add_argument("--out", default="fix.patch")
    parser.add_argument("--model", default="qwen/qwen3.8-27b")

    args = parser.parse_args()
    generate_patch(args.diff, args.log, args.repo, args.out, args.model)
