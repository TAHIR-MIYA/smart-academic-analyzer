"""One-time download of NLP resources:  python -m scripts.setup_nlp"""
import subprocess
import sys

import nltk

from app.nlp.resources import NLTK_RESOURCES, SPACY_MODEL


def main() -> int:
    for name in NLTK_RESOURCES:
        print(f"Downloading NLTK resource: {name}")
        if not nltk.download(name, quiet=True):
            print(f"  FAILED to download {name}. Check your internet connection.")
            return 1
    print(f"Downloading spaCy model: {SPACY_MODEL}")
    code = subprocess.call([sys.executable, "-m", "spacy", "download", SPACY_MODEL])
    if code != 0:
        print("  FAILED to download the spaCy model.")
        return code
    print("All NLP resources installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
