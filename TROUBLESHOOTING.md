# Troubleshooting

## spaCy: "DLL load failed ... An Application Control policy has blocked this file"

**What it means.** Windows refused to load one of spaCy's compiled files (for example `vocab...pyd`). This is an
operating-system security policy, not a bug in the project or in spaCy. spaCy is needed for lemmatisation and named
entity recognition, so those features are unavailable until the block is resolved.

**What still works meanwhile.** The application starts, and `/api/health` shows `spacy_problem` with the reason.
Uploading and text extraction work. Analysis endpoints answer with a clear "spaCy is installed but cannot be loaded"
message (HTTP 503) instead of crashing. The tests that need spaCy are skipped; all others run.

### 1. Find out which policy is blocking it

* Windows Security, App & browser control, Smart App Control settings. If it says **On** or **Evaluation**, that is the
  most likely cause: it blocks unsigned programs and libraries it does not recognise, and "Evaluation" mode can switch
  itself to On after a few weeks, which would explain why spaCy worked earlier and then stopped.
* Or ask Windows directly (PowerShell):

  ```powershell
  Get-WinEvent -LogName "Microsoft-Windows-CodeIntegrity/Operational" -MaxEvents 30 |
    Where-Object { $_.Message -match "vocab|spacy" } | Format-List TimeCreated, Id, Message
  ```

  The message names the file and the policy that blocked it.
* Check whether other compiled packages load: `python -c "import numpy, sklearn, nltk; print('ok')"`.
  If only spaCy fails, the block is specific to spaCy's files.
* If the computer belongs to a college or employer, the policy is probably managed (AppLocker / WDAC). You cannot
  change it yourself; use option B or ask the administrator.

### 2. Ways forward (try in this order)

**A. Reinstall spaCy and its compiled dependencies.** Smart App Control judges each file by reputation, so a fresh
download sometimes passes. It is not guaranteed.

```powershell
pip install --force-reinstall --no-cache-dir spacy
python -c "import spacy; print(spacy.__version__)"
```

A virtual environment on Python 3.12 (from python.org) uses different compiled files from Python 3.13 and may behave
differently.

**B. Run the backend in WSL 2 (works on managed and personal laptops).** Linux programs inside WSL are not subject to
Windows code-integrity rules.

```powershell
wsl --install -d Ubuntu          # once, then restart and create the Linux user
```

Then, inside the Ubuntu terminal (keep the project in the Linux file system, e.g. `~/smart-academic-analyzer`, not
under `/mnt/d`, which is slow):

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip
cd ~/smart-academic-analyzer/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.setup_nlp
python -m app.ml.train
uvicorn app.main:app --reload --host 0.0.0.0
```

The frontend can keep running on Windows (`npm run dev`); open http://localhost:5173 as usual, because WSL forwards
port 8000 to Windows.

**C. Turn Smart App Control off (personal computers only).** Windows Security, App & browser control, Smart App Control
settings, Off. This lowers Windows' protection against unknown programs, and on some Windows versions it cannot be
turned back on without resetting Windows. Prefer A or B unless you accept that trade-off.

### 3. For the viva

Decide which machine you will present on **before** the day and run the whole project on it once (`pytest`,
`python -m app.ml.train`, both servers). If your own laptop blocks spaCy, present from WSL or from another computer.
