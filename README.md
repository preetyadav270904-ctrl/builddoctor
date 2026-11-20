# 🩺 BuildDoctor

**A command-line tool that finds the commit that broke your build, suggests a fix using an LLM, and checks that the fix actually works.**

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Sandboxed%20Runs-2496ED?logo=docker&logoColor=white)
![Groq](https://img.shields.io/badge/LLM-Groq%20API-F55036)
![Pytest](https://img.shields.io/badge/Tests-Pytest-0A9EDC?logo=pytest&logoColor=white)

---

## 📖 About

When a CI build fails, the usual routine is: find which commit broke it, read the error, write a fix, and re-run the tests. BuildDoctor automates that loop for small Python projects.

You give it a **known-good commit** and a **failing commit**. It then:

1. **Finds the culprit commit** by running the tests on each commit inside a Docker container
2. **Collects context**: the breaking `git diff` and the failing `pytest` log
3. **Asks an LLM (via Groq)** to write a minimal unified diff patch
4. **Verifies the patch** in a fresh sandbox: confirms the test fails first, applies the patch, and checks that `pytest` now passes

The main idea: an LLM's patch is only a *suggestion* until the tests prove it works. I built this to learn about Docker, Git internals, LLM APIs, and how to wire several tools into one CLI.

---

## ✨ Features

- Finds the regression commit between a good and a bad commit
- Runs tests in Docker, so nothing runs directly on your machine
- Generates a patch using the Groq API (temperature `0.0` for consistent output)
- Fixes the wrong line counts LLMs often put in diff headers
- Verifies the patch in a clean sandbox before recommending it
- Each stage can be run on its own (bisect only, patch only, verify only)
- Includes a script that generates a small demo repo with a planted bug

---

## 🏗️ How It Works

```
[ Good commit ..... Bad commit ]
            │
            ▼
1. Bisection ───────► Runs tests per commit in Docker ──► finds culprit commit
            │
            ▼
2. Context ─────────► Collects the breaking git diff + pytest failure log
            │
            ▼
3. Patch generation ► Sends context to Groq LLM ──► cleans diff ──► fix.patch
            │
            ▼
4. Verification ────► Fresh sandbox: confirm failure ──► apply patch ──► pytest passes?
```

### Components

| File | What it does |
|---|---|
| `runner.py` + `Dockerfile` | Builds a small Python image and runs `pytest` on a repo mounted into the container |
| `git_utils.py` | Helper functions for cloning, checking out commits and getting diffs |
| `bisector.py` | Goes through the commits between good and bad and finds the first failing one |
| `patcher.py` + `prompts/` | Builds the prompt, calls Groq, cleans the response and fixes diff hunk headers |
| `verify.py` | Re-creates the failure in a clean copy, applies `fix.patch` and re-runs tests |
| `main.py` | Runs the whole pipeline from one command |
| `setup_test_repo.py` | Creates a demo repo with 3 commits and a planted bug |

---

## 📁 Project Structure

```
builddoctor/
├── prompts/
│   ├── patch_system.txt      # System prompt: asks for a raw unified diff only
│   └── patch_user.txt        # Template for diff, test log and source code
├── dummy_project/            # Sample project used to test the runner
├── Dockerfile                # Python 3.11 + pytest image
├── runner.py                 # Builds the image and runs tests in a container
├── git_utils.py              # Git helper functions
├── bisector.py               # Finds the culprit commit
├── setup_test_repo.py        # Generates the demo repo
├── patcher.py                # Groq API call + patch cleanup
├── verify.py                 # Sandbox verification
├── main.py                   # End-to-end CLI
└── requirements.txt          # groq, pytest
```

---

## 🧰 Prerequisites

- **Python** 3.10 or newer
- **Git**
- **Docker** running locally (Docker Desktop on Windows/macOS, or Colima on macOS)
- **Groq API key** from [console.groq.com](https://console.groq.com)

---

## 🚀 Installation

### 1. Clone the repo and set up a virtual environment

**macOS / Linux**

```bash
git clone https://github.com/<your-username>/builddoctor.git
cd builddoctor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/<your-username>/builddoctor.git
cd builddoctor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Set your Groq API key

**macOS / Linux**

```bash
export GROQ_API_KEY="your_api_key_here"
```

**Windows (PowerShell)**

```powershell
$env:GROQ_API_KEY="your_api_key_here"
```

---

## ▶️ Quickstart (Demo)

### Step 1: Generate the demo repository

```bash
python setup_test_repo.py
```

This creates a small Git repo (`test_target_repo`) with three commits: a working version, a harmless docs change, and a commit that breaks the logic. Copy the **good commit hash** (commit 1) and the **bad commit hash** (commit 3) from the terminal output.

### Step 2: Run the full pipeline

**macOS / Linux**

```bash
python main.py \
  --repo ./test_target_repo \
  --good <GOOD_COMMIT_HASH> \
  --bad <BAD_COMMIT_HASH>
```

**Windows (PowerShell)**

```powershell
python main.py `
  --repo "$((Get-Item test_target_repo).FullName)" `
  --good <GOOD_COMMIT_HASH> `
  --bad <BAD_COMMIT_HASH>
```

### Example output

```text
=======================================================
 BuildDoctor - Automated CI Triage & Repair
=======================================================
[Runner] Building base Docker image...
[Runner] Base image built successfully.

[*] Cloning ./test_target_repo into scratch workspace...
[*] Bisecting 3 commits...
    [1/3] 2d42a58 -> PASS
    [2/3] 4ac5eb3 -> PASS
    [3/3] a66e7ed -> FAIL (Exit code 1)
[+] Culprit identified: a66e7ed2bec2894a45fca206613b020321546826

[*] Requesting LLM patch...
[+] Saved clean patch to fix.patch

[*] Running isolated verification container...
 -> Baseline failure confirmed.
[*] Applying fix.patch...
 -> Patch applied cleanly.
[*] Running test suite inside container...

----------------------------------------
VERIFICATION: PASSED (Build Green)
----------------------------------------

=======================================================
 PIPELINE SUMMARY
=======================================================
 Target Repo:   ./test_target_repo
 Culprit Hash:  a66e7ed2bec2894a45fca206613b020321546826
 Patch Status:  RESOLVED
 -> Patch verified green. Run 'git apply fix.patch' to adopt.
=======================================================
```

---

## 🧩 Running Each Stage Separately

**Bisection only**

```bash
python bisector.py --repo ./test_target_repo --good <GOOD_HASH> --bad <BAD_HASH>
```

**Generate a patch from saved files**

```bash
python patcher.py --diff culprit_diff.diff --log failing_test.log --repo ./test_target_repo --out fix.patch
```

**Verify an existing patch**

```bash
python verify.py --repo ./test_target_repo --commit <CULPRIT_HASH> --patch fix.patch
```

---

## 🧠 Challenges I Ran Into (and What I Learned)

- **LLMs get diff headers wrong.** The model often miscounted lines in the `@@ -old,count +new,count @@` header, and `git apply` failed with a `corrupt patch` error. I wrote code to recalculate the counts and used `git apply --recount`.
- **Temporary folders and Docker mounts.** Docker on macOS (Colima) and Windows couldn't always mount temp folders from system paths. I created temp folders (`.tmp_verify_*`, `.tmp_bisect_*`) inside the project directory instead, and it worked on both.
- **Safer subprocess calls.** I pass Git and Docker commands as argument lists (`shell=False`) instead of strings, which avoids shell injection problems.
- **Don't trust the AI blindly.** Verifying the patch by running the tests taught me why LLM output should always be checked.

---

## ⚠️ Limitations

- **Linear search:** It checks commits one by one (`O(N)`), which is fine for small ranges (2 to 10 commits). A binary search like `git bisect` would be better for big histories.
- **One file only:** It patches the main file changed in the breaking commit, so bugs spread across several files aren't handled yet.
- **Fixed Docker image:** It uses one pre-built Python image, so projects that need extra system libraries or different dependencies per commit won't work yet.
- **Python projects only,** using `pytest`.

---

## 🔭 Future Improvements

- [ ] Use binary search for large commit ranges
- [ ] Support patches across multiple files
- [ ] Install each project's own `requirements.txt` inside the container
- [ ] Add retries that feed test failures back to the LLM
- [ ] Add a GitHub Actions workflow to run BuildDoctor on failing builds
- [ ] Add unit tests for the patch cleanup logic

---

## 🛠️ Tech Stack

Python · Docker · Git · Pytest · Groq API · Argparse

---

## 👤 Author

**Preet Yadav**
| Aspiring DevOps / MLOps Engineer

[LinkedIn](https://linkedin.com/in/preetyadav319) · [GitHub](https://github.com/preetyadav270904-ctrl)

---

⭐ If you found this useful, feel free to star the repo!
