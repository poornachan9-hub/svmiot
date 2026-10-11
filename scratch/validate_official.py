import zipfile
import pandas as pd
from pathlib import Path
import hashlib

zip_path = Path("datasets/rt-iot2022.zip")
extracted_csv = Path("datasets/RT_IOT2022_official.csv")

print("Extracting official RT_IOT2022...")
with zipfile.ZipFile(zip_path, "r") as zf:
    name = zf.namelist()[0]
    with zf.open(name) as src, open(extracted_csv, "wb") as dst:
        dst.write(src.read())

print(f"Extracted to: {extracted_csv}")
print(f"File size: {extracted_csv.stat().st_size / 1024 / 1024:.2f} MB")

# SHA-256
sha256 = hashlib.sha256()
with open(extracted_csv, "rb") as f:
    for block in iter(lambda: f.read(65536), b""):
        sha256.update(block)
print(f"CSV SHA-256: {sha256.hexdigest()}")

# Load and validate
df = pd.read_csv(extracted_csv, low_memory=False)
print("Shape:", df.shape)
print("Columns count:", len(df.columns))
print("First 10 columns:", list(df.columns[:10]))
print("Last 10 columns:", list(df.columns[-10:]))
print("\nTarget column candidates:")
for col in ["Attack_type", "label", "Label"]:
    if col in df.columns:
        print(f"\nValue counts for '{col}':")
        print(df[col].value_counts())

print("\nMissing values sum:", df.isnull().sum().sum())
missing_per_col = df.isnull().sum()
if missing_per_col.sum() > 0:
    print("Columns with missing values:", missing_per_col[missing_per_col > 0].to_dict())

print("\nDuplicates:", df.duplicated().sum())
