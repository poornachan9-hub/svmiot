# Next Task

## Current: CHECKPOINT 2 — Wire simulation_api through TelemetryHandler + fix SVM detection

## Completed This Iteration (Checkpoint 1):
- Diagnosed 15-step pipeline: 12/15 FAIL in web integration layer
- Ran final_attack_test.py: 39/39 PASS but uses rule-based fallback (cheats via `label` field)
- Identified 5 root causes (see DEBUG_REPORT.md)
- Confirmed SVM model loads but predicts SUSPICIOUS_UNKNOWN (conf=0.46) for DDoS → below isolation threshold

## Checkpoint 2 Plan:
1. Rewrite `simulation_api.py` to route events through `TelemetryHandler.process_message()`
2. Load SVM AI engine in TelemetryHandler at startup
3. Fix SVM/risk threshold so real attacks reliably trigger HIGH/CRITICAL
4. Return full pipeline result (prediction, risk, isolation, blockchain) to frontend
5. Store security events in ORM database

## Remaining Checkpoints:
- CP3: Fix per-device isolation (independent state tracking)
- CP4: Wire Ganache blockchain (ethereum_client.py + env vars)
- CP5: E2E test across all devices
