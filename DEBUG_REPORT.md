# SecureIoT-X — DEBUG REPORT (Checkpoint 1)

## Date: 2026-09-09
## Objective: Trace attack E2E and find all broken links

---

## PIPELINE TRACE RESULTS

| # | STEP | STATUS | ROOT CAUSE |
|---|------|--------|------------|
| 1 | Attack event generated (TrafficGenerator) | **PASS** | `generate_attack()` produces valid features including SVM-compatible fields |
| 2 | Attack features compatible with SVM | **PASS** | `fwd_pkts_tot`, `bwd_pkts_tot`, `proto`, `dst_port`, etc. all present |
| 3 | SVM model file exists | **PASS** | `models/svm/SVM_v1_20260907.joblib` (1.8 MB) |
| 4 | SVM prediction via PredictionEngine | **FAIL** | SVM predicts `SUSPICIOUS_UNKNOWN` (conf=0.46) for DDoS attack — too low to trigger HIGH/CRITICAL. Rule-based fallback cheats by reading `label` field directly |
| 5 | simulation_api.py calls TelemetryHandler | **FAIL** | `/simulate/event` hardcodes `ai_confidence=0.85` or `0.3`, never calls `TelemetryHandler.process_message()` or `PredictionEngine` |
| 6 | simulation_api.py calls DeviceManager | **FAIL** | No `DeviceManager` import or usage in simulation_api.py — device state never changes |
| 7 | simulation_api.py writes to database | **FAIL** | No DB session, no ORM insert — events exist only in HTTP response |
| 8 | simulation_api.py calls ResponseEngine.execute_response | **FAIL** | `/simulate/event` never calls `execute_response()`, only `/simulate/scenario` calls `decide_response()` but not `execute_response()` |
| 9 | Device isolation via DeviceManager | **FAIL** | `DeviceManager.isolate_device()` never called from simulation_api. Only called inside `TelemetryHandler.process_message()` which simulation_api bypasses |
| 10 | Blockchain records to Ganache | **FAIL** | `TelemetryHandler` uses `SecurityBlockchain` (JSON file). `ethereum_client.py` exists but is never wired in. No `GANACHE_*` env vars in `.env` |
| 11 | Blockchain records to JSON ledger | **FAIL** | simulation_api doesn't call blockchain at all. TelemetryHandler does call `SecurityBlockchain` but simulation_api bypasses TelemetryHandler |
| 12 | DB security event persisted | **FAIL** | The `final_attack_test.py` creates its own temp SQLite table manually — no ORM integration from pipeline |
| 13 | Dashboard receives real events | **FAIL** | `Simulation.jsx` uses `setTimeout` to display hardcoded fake terminal logs. Does not listen for real WebSocket events |
| 14 | Notification dispatched | **FAIL** | `NotificationService.dispatch_alert()` never called from simulation_api or TelemetryHandler |
| 15 | Per-device independent isolation | **FAIL** | simulation_api doesn't track any per-device state. No isolation = no independence to test |

---

## ROOT CAUSES (RANKED BY PRIORITY)

### RC-1: Simulation API is a dead-end (CRITICAL)
**File**: `backend/api/simulation_api.py`
- `/simulate/event` generates traffic but hardcodes `ai_confidence=0.85`/`0.3`
- Never calls `TelemetryHandler.process_message()`, `PredictionEngine`, `DeviceManager`, DB, or blockchain
- The entire pipeline from SVM onward is bypassed

### RC-2: SVM predictions don't reliably detect attacks (HIGH)
**File**: `ai_engine/predict.py`, SVM model
- SVM predicts `SUSPICIOUS_UNKNOWN` (conf=0.46) for DDoS traffic
- The `_rule_based_prediction` fallback cheats by reading the `label` field from the event (which the attacker sets)
- When SVM IS loaded, real attacks get low confidence → classified as `SUSPICIOUS_UNKNOWN` → risk score drops below HIGH threshold → no isolation triggered
- The E2E test passes only because it does NOT call `h.load_ai_engine()`, so it uses rule-based fallback

### RC-3: No Ganache integration (HIGH)
**File**: `.env`, `blockchain/ethereum_client.py`, `iot/telemetry_handler.py`
- `.env` has no `GANACHE_*` variables
- `TelemetryHandler` imports `SecurityBlockchain` (JSON file), not `EthereumClient`
- `ethereum_client.py` exists and works but is never wired into the pipeline
- `blockchain_api.py` uses `SecurityBlockchain` singleton

### RC-4: No DB persistence from pipeline (MEDIUM)
- `TelemetryHandler.process_message()` does lifecycle tracking in-memory but never writes to SQLAlchemy ORM
- `final_attack_test.py` manually creates a temp SQLite table and inserts — this is test scaffolding, not real integration

### RC-5: Dashboard simulation is fake (MEDIUM)
**File**: `dashboard/src/pages/Simulation.jsx`
- Uses `setTimeout` to print hardcoded terminal logs
- Does not display real backend response data from API calls
- API response data (`result`) is caught but only `risk_score` is used in the fake log

---

## SUMMARY

```
CHECKPOINT: 1 (Diagnosis)
ROOT CAUSE: simulation_api bypasses TelemetryHandler/SVM/DeviceManager/DB/Blockchain. SVM confidence too low to trigger isolation. No Ganache wiring.
FILES CHANGED: DEBUG_REPORT.md
TESTS: Ran final_attack_test.py (39/39 PASS but uses rule-based fallback, not SVM)
RESULT: 5 root causes identified. 12/15 pipeline steps FAIL in web integration.
NEXT TASK: CHECKPOINT 2 — Wire simulation_api through TelemetryHandler with SVM + fix SVM detection threshold.
```
