"""Uploads the two trained model checkpoints to your Hugging Face Hub account, so a
deployed server (which can't have 250MB+ files committed to git) can load them by repo id
instead of a local folder - see clause_extractor._load_model / document_classifier._load_model
and render.yaml's CLAUSE_MODEL_DIR / DOCUMENT_CLASSIFICATION_MODEL_DIR env vars.

One-time setup:
    pip install huggingface_hub  (already installed as a transformers dependency)
    huggingface-cli login        (paste a token from https://huggingface.co/settings/tokens
                                   with "write" access)

Usage:
    python -m scripts.upload_models_to_hub --username yourname
    python -m scripts.upload_models_to_hub --username yourname --private
"""

import argparse
from pathlib import Path

from huggingface_hub import HfApi

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS = [
    ("clause-extraction-baseline", REPO_ROOT / "models" / "clause-extraction-baseline"),
    (
        "document-classification-baseline",
        REPO_ROOT / "models" / "document-classification-baseline",
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--username", required=True, help="Your Hugging Face username or organization")
    parser.add_argument(
        "--private", action="store_true", help="Create the repos as private (default: public)"
    )
    args = parser.parse_args()

    api = HfApi()

    for repo_name, local_dir in MODELS:
        if not local_dir.exists():
            print(f"Skipping {repo_name}: {local_dir} not found locally.")
            continue

        repo_id = f"{args.username}/{repo_name}"
        print(f"Creating (if needed) and uploading to {repo_id} ...")
        api.create_repo(repo_id, repo_type="model", private=args.private, exist_ok=True)
        api.upload_folder(repo_id=repo_id, folder_path=str(local_dir), repo_type="model")
        print(f"Done: https://huggingface.co/{repo_id}")
        print(f"  -> set the corresponding env var to: {repo_id}")

    print("\nSet CLAUSE_MODEL_DIR and DOCUMENT_CLASSIFICATION_MODEL_DIR to the repo ids "
          "printed above in your deployment platform's environment variables.")


if __name__ == "__main__":
    main()
