import sys
from pathlib import Path
sys.path.insert(0, str(Path(".").resolve()))

import asyncio
from backend.api import models_api

models = asyncio.run(models_api.list_models())
print("==========================================================================================")
print("MODELS API RESPONSE (/api/models)")
print("==========================================================================================")
for m in models:
    print(f"{m['name']:20s} | Status: {m['status']:10s} | Prod: {str(m['is_production']):5s} | Ready: {str(m['production_ready']):5s} | Acc: {m['accuracy']:6.2f}% | F1: {m['f1_score']:6.2f}% | AUC: {m['metrics']['roc_auc']}")
