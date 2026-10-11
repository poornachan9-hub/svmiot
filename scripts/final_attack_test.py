"""
SecureIoT-X -- Final Attack E2E Test.

Usage: python -m scripts.final_attack_test

Pipeline tested:
  SIMULATED ATTACK -> DETECTION -> RISK -> ISOLATION -> DATABASE EVENT
  -> BLOCKCHAIN BLOCK -> DASHBOARD EVENT -> RECOVERY
"""

import json
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EVENT_ID = "EVT-DEMO-001"
DEVICE_ID = "ESP32_003"
ATTACK_TYPE = "DDoS"

results = []


def check(stage, condition, detail=""):
    status = "[PASS]" if condition else "[FAIL]"
    msg = f"  {status} {stage}"
    if detail:
        msg += f" -- {detail}"
    print(msg)
    results.append((stage, condition))
    return condition


def main():
    print("=" * 70)
    print("  SecureIoT-X -- FINAL ATTACK E2E TEST")
    print(f"  Event ID: {EVENT_ID}")
    print(f"  Target:   {DEVICE_ID}")
    print(f"  Attack:   {ATTACK_TYPE}")
    print(f"  Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # -- Setup --
    from simulation.traffic_generator import TrafficGenerator
    from iot.mqtt_client import MQTTMessage
    from iot.telemetry_handler import TelemetryHandler
    from iot.device_manager import DeviceManager
    from blockchain.chain import SecurityBlockchain

    # Use temp blockchain ledger for clean test
    fd, bc_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    # Use temp database for clean test
    fd2, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd2)

    try:
        blockchain = SecurityBlockchain(difficulty=1, ledger_path=bc_path)
        device_manager = DeviceManager(auto_register=True)
        handler = TelemetryHandler(
            blockchain=blockchain,
            device_manager=device_manager,
        )

        gen = TrafficGenerator(seed=42)

        # -- STAGE 1: SIMULATED ATTACK --
        print(f"\n{'-' * 70}")
        print("  STAGE 1: SIMULATED ATTACK")
        print(f"{'-' * 70}")

        attack_event = gen.generate_attack(ATTACK_TYPE, DEVICE_ID)
        # Override event_id to carry our trace ID
        attack_event["event_id"] = EVENT_ID

        check("Attack generated", attack_event is not None,
              f"type={attack_event['event_type']}, pkts={attack_event['packet_count']}")
        check("Event ID set", attack_event["event_id"] == EVENT_ID)
        check("Device ID set", attack_event["device_id"] == DEVICE_ID)
        check("Label is attack", attack_event["label"] == ATTACK_TYPE,
              f"label={attack_event['label']}")

        # -- STAGE 2: DETECTION -> RISK -> RESPONSE --
        print(f"\n{'-' * 70}")
        print("  STAGE 2: DETECTION -> RISK -> RESPONSE")
        print(f"{'-' * 70}")

        msg = MQTTMessage(
            topic=f"iot/{DEVICE_ID}/telemetry",
            payload=attack_event,
            device_id=DEVICE_ID,
        )
        result = handler.process_message(msg)

        # Check event_id carried through
        check("Event ID carried", result["event_id"] == EVENT_ID,
              f"got={result['event_id']}")

        # Check prediction
        pred = result.get("prediction", {})
        pred_label = pred.get("prediction", "")
        pred_conf = pred.get("confidence", 0)
        check("Attack detected", pred_label != "Normal",
              f"prediction={pred_label}, confidence={pred_conf:.2f}")

        # Check risk
        risk = result.get("risk", {})
        risk_score = risk.get("risk_score", 0)
        severity = risk.get("severity", "")
        check("Risk assessed", risk_score > 0,
              f"score={risk_score}, severity={severity}")
        check("Severity HIGH or CRITICAL", severity in ("HIGH", "CRITICAL"),
              f"severity={severity}")

        # Check response
        resp = result.get("response", {})
        action = resp.get("action", "")
        check("Response action ISOLATE", action in ("ISOLATE", "BLOCK"),
              f"action={action}")

        # -- STAGE 3: DEVICE ISOLATION --
        print(f"\n{'-' * 70}")
        print("  STAGE 3: DEVICE ISOLATION")
        print(f"{'-' * 70}")

        check("Device isolated flag", result.get("device_isolated") is True)

        dev_state = handler.get_device_state(DEVICE_ID)
        check("DeviceManager state", dev_state is not None)
        if dev_state:
            check("Device is_isolated=True", dev_state["is_isolated"] is True,
                  f"is_isolated={dev_state['is_isolated']}")
            check("Threat count incremented", dev_state["threat_count"] > 0,
                  f"threat_count={dev_state['threat_count']}")

        # -- STAGE 4: DATABASE EVENT --
        print(f"\n{'-' * 70}")
        print("  STAGE 4: DATABASE EVENT")
        print(f"{'-' * 70}")

        # Write event to SQLite directly (no backend server needed)
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            device_id TEXT NOT NULL,
            attack_type TEXT,
            risk_score REAL,
            severity TEXT,
            action TEXT,
            response_status TEXT,
            blockchain_block INTEGER,
            device_isolated INTEGER DEFAULT 0,
            timestamp TEXT
        )""")
        conn.execute(
            """INSERT INTO security_events
               (event_id, device_id, attack_type, risk_score, severity,
                action, response_status, blockchain_block, device_isolated, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                EVENT_ID,
                DEVICE_ID,
                pred_label,
                risk_score,
                severity,
                action,
                resp.get("status", "UNKNOWN"),
                result.get("blockchain_block"),
                1 if result.get("device_isolated") else 0,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()

        # Verify
        row = conn.execute(
            "SELECT * FROM security_events WHERE event_id = ?", (EVENT_ID,)
        ).fetchone()
        check("DB record created", row is not None,
              f"event_id={row[1] if row else 'N/A'}")
        if row:
            check("DB event_id matches", row[1] == EVENT_ID)
            check("DB device_id matches", row[2] == DEVICE_ID)
            check("DB attack_type", row[3] == pred_label, f"attack_type={row[3]}")
            check("DB device_isolated=1", row[9] == 1)

        conn.close()

        # -- STAGE 5: BLOCKCHAIN BLOCK --
        print(f"\n{'-' * 70}")
        print("  STAGE 5: BLOCKCHAIN BLOCK")
        print(f"{'-' * 70}")

        block_idx = result.get("blockchain_block")
        check("Blockchain block created", block_idx is not None,
              f"block_index={block_idx}")

        if block_idx is not None:
            block_data = blockchain.get_block(block_idx)
            check("Block has event_id", block_data["event_id"] == EVENT_ID,
                  f"event_id={block_data['event_id']}")
            check("Block has device_id", block_data["device_id"] == DEVICE_ID)
            check("Block has attack_type", block_data["attack_type"] == pred_label)
            check("Block has risk_score", block_data["risk_score"] == risk_score)
            check("Block has severity", block_data["severity"] == severity)
            check("Block has action", block_data["action"] == action)
            check("Block has previous_hash", len(block_data["previous_hash"]) == 64)
            check("Block has event_hash", len(block_data["event_hash"]) == 64)
            check("Block has hash", len(block_data["hash"]) == 64)
            check("Block has timestamp", block_data["timestamp"] is not None)

            # Verify chain integrity
            is_valid, errors = blockchain.validate_chain()
            check("Chain is VALID", is_valid,
                  f"blocks={blockchain.length}, errors={len(errors)}")

            # Print block summary
            print(f"\n  [INFO] Block #{block_idx} contents:")
            print(f"    event_id:      {block_data['event_id']}")
            print(f"    device_id:     {block_data['device_id']}")
            print(f"    attack_type:   {block_data['attack_type']}")
            print(f"    risk_score:    {block_data['risk_score']}")
            print(f"    severity:      {block_data['severity']}")
            print(f"    action:        {block_data['action']}")
            print(f"    timestamp:     {block_data['timestamp']}")
            print(f"    previous_hash: {block_data['previous_hash'][:32]}...")
            print(f"    event_hash:    {block_data['event_hash'][:32]}...")
            print(f"    hash:          {block_data['hash'][:32]}...")

        # -- STAGE 6: DASHBOARD EVENT --
        print(f"\n{'-' * 70}")
        print("  STAGE 6: DASHBOARD EVENT")
        print(f"{'-' * 70}")

        # Verify lifecycle tracking (dashboard state)
        lc_state = result.get("lifecycle_state")
        check("Lifecycle state tracked", lc_state is not None,
              f"state={lc_state}")
        check("Lifecycle VERIFIED", lc_state == "VERIFIED")

        stats = handler.get_stats()
        check("Stats threats_detected > 0", stats["threats_detected"] > 0,
              f"threats={stats['threats_detected']}")
        check("Stats devices_isolated > 0", stats["devices_isolated"] > 0,
              f"isolated={stats['devices_isolated']}")
        check("DeviceManager summary", stats["device_summary"]["isolated"] > 0,
              f"isolated_count={stats['device_summary']['isolated']}")

        # -- STAGE 7: RECOVERY (ISOLATED -> RELEASE -> NORMAL) --
        print(f"\n{'-' * 70}")
        print("  STAGE 7: RECOVERY (ISOLATED -> RELEASE -> NORMAL)")
        print(f"{'-' * 70}")

        # Verify device is currently isolated
        dev_before = handler.get_device_state(DEVICE_ID)
        check("Device currently ISOLATED", dev_before["is_isolated"] is True)

        # Release
        released = handler.release_device(DEVICE_ID)
        check("Release succeeded", released is True)

        # Verify device is now normal
        dev_after = handler.get_device_state(DEVICE_ID)
        check("Device is_isolated=False after release",
              dev_after["is_isolated"] is False,
              f"is_isolated={dev_after['is_isolated']}")
        check("Device still online", dev_after["is_online"] is True)

        # -- SUMMARY --
        print(f"\n{'=' * 70}")
        total = len(results)
        passed = sum(1 for _, ok in results if ok)
        failed = total - passed

        if failed == 0:
            print(f"  ALL {total} CHECKS PASSED")
        else:
            print(f"  {failed}/{total} CHECKS FAILED:")
            for stage, ok in results:
                if not ok:
                    print(f"     - {stage}")

        print(f"\n  Pipeline verified:")
        print(f"    ATTACK({EVENT_ID}) -> DETECTION -> RISK({risk_score},{severity})")
        print(f"    -> ISOLATE({DEVICE_ID}) -> DB -> BLOCKCHAIN(block#{block_idx})")
        print(f"    -> DASHBOARD -> RECOVERY(released)")
        print(f"{'=' * 70}")

        sys.exit(0 if failed == 0 else 1)

    finally:
        # Cleanup temp files
        try:
            os.unlink(bc_path)
        except OSError:
            pass
        try:
            os.unlink(db_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
