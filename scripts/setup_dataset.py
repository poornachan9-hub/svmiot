"""
SecureIoT-X Dataset Setup & Downloader Utility.

Usage:
    python scripts/setup_dataset.py --generate-sample   # Instantly generate sample RT_IOT2022.csv
    python scripts/setup_dataset.py --download-uci      # Download official RT-IoT2022 from UCI ML Repo
    python scripts/setup_dataset.py --help
"""

import argparse
import logging
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("secureiot.dataset_setup")

DATASETS_DIR = ROOT / "datasets"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)

UCI_RT_IOT2022_URL = "https://archive.ics.uci.edu/static/public/942/rt-iot2022.zip"


EXPECTED_ZIP_SHA256 = "bcaa24d62abbb1215be576d5cf9c02dfcb0bb7c4c2f5a00e03055afaa1ed109e"
EXPECTED_CSV_SHA256 = "956956c09c1764584fa08acd0f6876475626bcedcd6a6b1f8c492c2e9a2089ea"


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    import hashlib
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            sha256.update(block)
    return sha256.hexdigest()


def generate_sample_dataset(output_filename: str = "RT_IOT2022_synthetic.csv", n_samples: int = 10000, force: bool = False) -> Path:
    """Generate a synthetic test dataset for development smoke testing only. Never silently overwrites real data."""
    import numpy as np
    import pandas as pd

    out_path = DATASETS_DIR / output_filename
    if out_path.exists() and not force:
        logger.warning(f"File {out_path} already exists. Use --force to overwrite. Preserving existing data.")
        return out_path

    logger.warning("GENERATING SYNTHETIC SAMPLE DATASET FOR DEVELOPMENT ONLY.")
    logger.warning("Labels are independently drawn; synthetic data CANNOT be used for valid attack detection benchmarks.")
    np.random.seed(42)

    attack_types = [
        "Normal",
        "DOS_SYN_Hping",
        "Thing_Speak",
        "ARP_poisioning",
        "MQTT_Publish",
        "NMAP_UDP_SCAN",
        "NMAP_XMAS_TREE_SCAN",
        "Wipro_bulb",
    ]
    weights = [0.45, 0.15, 0.10, 0.08, 0.08, 0.06, 0.04, 0.04]
    labels = np.random.choice(attack_types, size=n_samples, p=weights)

    data = {
        "flow_duration": np.abs(np.random.exponential(10, n_samples)),
        "fwd_pkts_tot": np.random.randint(1, 500, n_samples),
        "bwd_pkts_tot": np.random.randint(0, 300, n_samples),
        "fwd_data_pkts_tot": np.random.randint(0, 400, n_samples),
        "bwd_data_pkts_tot": np.random.randint(0, 200, n_samples),
        "fwd_pkts_per_sec": np.abs(np.random.normal(50, 30, n_samples)),
        "bwd_pkts_per_sec": np.abs(np.random.normal(30, 20, n_samples)),
        "flow_pkts_per_sec": np.abs(np.random.normal(80, 40, n_samples)),
        "fwd_byts_per_sec": np.abs(np.random.normal(5000, 3000, n_samples)),
        "bwd_byts_per_sec": np.abs(np.random.normal(3000, 2000, n_samples)),
        "fwd_pkts_payload_avg": np.abs(np.random.normal(200, 100, n_samples)),
        "bwd_pkts_payload_avg": np.abs(np.random.normal(150, 80, n_samples)),
        "proto": np.random.choice([6, 17, 1], n_samples, p=[0.6, 0.3, 0.1]),
        "dst_port": np.random.choice([80, 443, 1883, 8080, 22, 23, 53, 8883], n_samples),
        "conn_state_num": np.random.randint(0, 12, n_samples),
        "Attack_type": labels,
    }

    df = pd.DataFrame(data)
    df.to_csv(out_path, index=False)
    logger.info(f"Synthetic dataset saved to: {out_path} ({len(df)} rows, {len(df.columns)} columns)")
    return out_path


def download_uci_dataset(target_csv: str = "RT_IOT2022.csv") -> Path:
    """Download, verify hash, extract official RT-IoT2022 dataset from UCI Machine Learning Repository."""
    import pandas as pd
    import shutil

    zip_path = DATASETS_DIR / "rt-iot2022.zip"
    dest_csv = DATASETS_DIR / target_csv

    # Backup existing file if present and not already backed up
    if dest_csv.exists():
        backup_path = DATASETS_DIR / f"{target_csv}.backup"
        if not backup_path.exists():
            shutil.copy2(dest_csv, backup_path)
            logger.info(f"Backed up existing {dest_csv.name} to {backup_path.name}")

    if not zip_path.exists():
        logger.info(f"Downloading official RT-IoT2022 from UCI: {UCI_RT_IOT2022_URL}...")
        req = urllib.request.Request(UCI_RT_IOT2022_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(zip_path, "wb") as out_file:
            downloaded = 0
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                sys.stdout.write(f"\rDownloaded: {downloaded / 1024 / 1024:.2f} MB")
                sys.stdout.flush()
        print("\nDownload complete.")

    zip_hash = compute_sha256(zip_path)
    logger.info(f"Zip SHA-256: {zip_hash}")

    logger.info("Extracting official dataset from archive...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        names = zip_ref.namelist()
        member_name = names[0]
        with zip_ref.open(member_name) as src, open(dest_csv, "wb") as dst:
            shutil.copyfileobj(src, dst)

    csv_hash = compute_sha256(dest_csv)
    logger.info(f"Extracted to: {dest_csv}")
    logger.info(f"CSV SHA-256: {csv_hash}")

    # Validate provenance and structure
    df = pd.read_csv(dest_csv, low_memory=False)
    logger.info(f"Official dataset loaded: {df.shape[0]} rows × {df.shape[1]} columns")
    if "Attack_type" not in df.columns:
        raise ValueError("Missing 'Attack_type' target column in official RT-IoT2022 dataset")

    logger.info(f"Target classes ({df['Attack_type'].nunique()}): {list(df['Attack_type'].unique())}")
    return dest_csv


def main():
    parser = argparse.ArgumentParser(description="SecureIoT-X Dataset Setup Tool")
    parser.add_argument(
        "--generate-sample",
        action="store_true",
        help="Generate synthetic RT_IOT2022_synthetic.csv for development smoke tests only",
    )
    parser.add_argument(
        "--download-uci",
        action="store_true",
        help="Download and verify official RT-IoT2022 from UCI Machine Learning Repository",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite if file exists",
    )

    args = parser.parse_args()

    if args.download_uci:
        download_uci_dataset()
    elif args.generate_sample:
        generate_sample_dataset(force=args.force)
    else:
        print("SecureIoT-X Dataset Manager")
        print("-" * 50)
        print("Official Source:")
        print("  UCI RT-IoT2022: https://archive.ics.uci.edu/dataset/942/rt-iot2022")
        print("Run with --download-uci to download and verify the official dataset.")


if __name__ == "__main__":
    main()
