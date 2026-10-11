# SecureIoT-X — Project Run & Execution Guide

This document provides the complete, step-by-step procedure and commands to run the **SecureIoT-X** system.

---

## 1. System Architecture & Running Components

SecureIoT-X runs four interconnected services:

| Component | Technology | Default URL / Port | Role |
| :--- | :--- | :--- | :--- |
| **Blockchain** | Ganache CLI | `http://127.0.0.1:7545` | Immutable security audit ledger |
| **Database** | MongoDB | `mongodb://127.0.0.1:27017` | Threat logs, devices, and metrics store |
| **Backend API** | FastAPI / Python | `http://localhost:8000` | AI inference, SDN, alert dispatchers |
| **Frontend UI** | Vite + React | `http://localhost:3000` | Real-time security operations dashboard |

---

## 2. Environment Configuration (`.env`)

Ensure the `.env` file in the project root has your credentials set:

```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=secureiot_x

# Blockchain (Ganache)
GANACHE_URL=http://127.0.0.1:7545
BLOCKCHAIN_DIFFICULTY=2

# Email Notifications (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=mjgowdru929@gmail.com
SMTP_PASSWORD=kwhgdektldtrqtfo
SMTP_FROM=mjgowdru929@gmail.com
SMTP_TO=sinchana1916@gmail.com

# Telegram Bot Notifications
TELEGRAM_BOT_TOKEN=8988690783:AAHgQ3v8VSKcTeNI3R6os5k0K_P6GHUH32c
TELEGRAM_CHAT_ID=8900239405
```

> **Note on Gmail:** Gmail requires a 16-character **Google App Password** (e.g. `kwhgdektldtrqtfo`) when 2-Factor Authentication is enabled on the sending Google account. Regular passwords will be rejected by Google's SMTP servers.

---

## 3. Step-by-Step Procedure to Run the Project

Open separate terminals (Command Prompt or PowerShell) for each component.

### Terminal 1: Start Ganache Blockchain
```powershell
npx ganache -p 7545 -d
```
*Leave this terminal running. It hosts the local blockchain at `http://127.0.0.1:7545`.*

---

### Terminal 2: Start MongoDB
If MongoDB is installed as a Windows service, it runs automatically in the background.  
To start it manually if needed:
```powershell
mongod --dbpath "C:\data\db"
```

---

### Terminal 3: Start the Backend (FastAPI API)
Navigate to the root folder:
```powershell
cd "c:\Users\megha\Desktop\huz p\iot defense\SecureIoT-X"
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```
*The API is now live at `http://localhost:8000`.*  
*Interactive Swagger documentation is available at `http://localhost:8000/docs`.*

---

### Terminal 4: Start the Dashboard (React Frontend)
Navigate to the `dashboard` directory:
```powershell
cd "c:\Users\megha\Desktop\huz p\iot defense\SecureIoT-X\dashboard"
npm run dev -- --host 0.0.0.0 --port 3000
```
*Open your browser and navigate to `http://localhost:3000` to view the dashboard.*

---

### Terminal 5: Start Mosquitto MQTT Broker (required for physical ESP32 hardware)
```powershell
# Uses the mosquitto.conf in the project root (allows anonymous connections)
mosquitto -c "c:\Users\megha\Desktop\huz p\iot defense\SecureIoT-X\mosquitto.conf" -v
```
*Mosquitto listens on `0.0.0.0:1883` so physical devices on the same Wi-Fi can connect.*

Also allow the port through Windows Firewall (run once, as Administrator):
```powershell
New-NetFirewallRule -DisplayName "Mosquitto MQTT" -Direction Inbound `
  -Protocol TCP -LocalPort 1883 -Action Allow -Profile Any
```

---

## 4. How to Test & Verify

### A. Run the End-to-End Demo Script
To see the full pipeline in a console demo (IoT generation -> AI classification -> Risk analysis -> Automated mitigation -> Blockchain recording):
```powershell
cd "c:\Users\megha\Desktop\huz p\iot defense\SecureIoT-X"
python demo.py
```

---

### B. Test Email & Telegram Notifications Directly
To verify that both alert channels are functioning and reaching `sinchana1916@gmail.com` and Telegram:
```powershell
python -c "import asyncio; from dotenv import load_dotenv; load_dotenv(); from security.email_service import send_email_alert; from security.telegram_service import send_security_alert; asyncio.run(send_email_alert('EVT-001','ESP32_001','DDoS','Malicious',0.95,'CRITICAL','ISOLATE',True)); asyncio.run(send_security_alert('EVT-001','ESP32_001','DDoS','Malicious',0.95,'CRITICAL','ISOLATE',True))"
```

---

### C. Trigger an Attack Simulation via API
You can simulate a cyber-attack via the dashboard's Simulation page or with a `curl` / Python call:
```powershell
python -c "import urllib.request, json; data = json.dumps({'device_id': 'smart_camera_01', 'attack_type': 'DDoS'}).encode('utf-8'); req = urllib.request.Request('http://127.0.0.1:8000/api/simulate/attack', data=data, headers={'Content-Type': 'application/json'}); resp = urllib.request.urlopen(req); print(resp.read().decode())"
```
When this runs:
1. The AI engine classifies the attack.
2. The SDN mitigation policy isolates the device.
3. The event is permanently committed to Ganache blockchain.
4. **An instant Telegram alert is sent.**
5. **An alert email with HTML report is sent to `sinchana1916@gmail.com`.**

---

### D. Run the Test Suite
To verify all unit, integration, and hybrid hardware enforcement tests:
```powershell
pytest tests/ -v
```

---

### E. Test Category A: Production Model Inference and Response
Exercises the currently validated RT_IOT2022 production artifact, risk engine, and configured response integrations:
```powershell
# Via REST API:
curl -X POST http://localhost:8000/api/devices/ESP32_011/test/detection
```
**Verification Evidence Returned:**
- `prediction`: Decoded RT_IOT2022 label, or `SUSPICIOUS_UNKNOWN` when confidence is below the configured threshold
- `model_prediction`: The artifact's decoded class before the confidence threshold is applied
- `confidence`: Probability returned by the loaded serving model
- `risk_score`: Computed by risk matrix (severity: `HIGH` or `CRITICAL`)
- `tx_hash`: On-chain Ganache transaction hash
- `enforcement`: Multi-tier isolation record (`ISOLATION_APPLIED` / `ISOLATION_VERIFIED`)

This integration test is not a model-accuracy claim. The AI Models page reports metrics computed from the untouched, versioned RT_IOT2022 test split; consult those metrics before using predictions for operational decisions.

---

### F. Test Category B: Explicit Response Enforcement & Physical Verification
Tests physical network isolation independently of ML inference accuracy (ensuring no ML predictions are fabricated):
```powershell
# Via REST API:
curl -X POST http://localhost:8000/api/devices/ESP32_011/test/enforcement
```
**What happens under the hood:**
1. **Tier 1 (Host OS Firewall):** Windows Advanced Firewall inbound blocking rule is generated (`SecureIoT_Quarantine_ESP32_011`).
2. **Tier 2 (Transport Filter):** Active socket & packet filter immediately drops all TCP/MQTT traffic from the physical device's IP and ID.
3. **Tier 3 (Hardware Radio Lock):** Quarantining command (`QUARANTINE_RADIO_LOCK`) dispatched over MQTT control topic `iot/{device_id}/control` — ESP32 immediately turns on the GPIO 2 quarantine LED and locks Wi-Fi radio (`WiFi.disconnect(true)`).
4. **Tier 4 (Independent Verification Probe):** Probe verifies the blocked network path.

---

### G. Active Verification Probe Check
To independently verify the quarantine state of any device:
```powershell
# Query device enforcement status & evidence
curl http://localhost:8000/api/devices/ESP32_011/enforcement

# Test access to designated probe endpoint:
# Returns HTTP 200 (ONLINE_ACCESSIBLE) when device is clean
# Returns HTTP 403 (QUARANTINED_BLOCKED) when device is isolated
curl http://localhost:8000/api/devices/probe/test?device_id=ESP32_011
```

---

### H. Manual Release & Recovery
Authorized manual release can be triggered via the Dashboard **"Release"** button or via API:
```powershell
curl -X POST http://localhost:8000/api/devices/ESP32_011/release
```
- Removes Windows Firewall rule
- Flushes transport socket filter blocklist
- Dispatches `RELEASE` payload over MQTT — ESP32 turns off LED and resumes normal telemetry
- Persists recovery state into MongoDB and restores device to `NORMAL`

## 5. Physical ESP32 Hardware Integration

### Quick Start
1. **Find your PC's Wi-Fi IP** (must be on same LAN as ESP32):
   ```powershell
   ipconfig   # Look for: Wireless LAN adapter Wi-Fi → IPv4 Address
   ```

2. **Add the Device in the Dashboard UI (Recommended)**:
   - Open your browser to `http://localhost:3000/devices` (or click **Devices** in the sidebar).
   - In the top-right of the table, click the **`+ Add Device`** button.
   - Select **Physical ESP32 Board** (or Simulation Node if creating a test device).
   - Enter your **Device ID** (e.g. `ESP32_011`, `ESP32_013`, or any ID starting from `ESP32_011` onwards).
   - Provide a Name, Type (e.g. `ESP32 DHT22 Sensor`), and optional IP / MAC address.
   - Click **`Register Hardware Device`**. The new device immediately appears in the fleet table with the **`PHYSICAL (ESP32)`** badge.

   *(Alternative via CLI curl)*:
   ```powershell
   curl -X POST http://localhost:8000/api/devices `
     -H "Content-Type: application/json" `
     -d '{"device_id":"ESP32_013","name":"Physical Sensor #1","device_type":"ESP32-WROOM-32","is_simulation":false}'
   ```

3. **Flash the firmware**: Open `firmware/esp32_secureiot/esp32_secureiot.ino` in Arduino IDE,  
   set your Wi-Fi credentials, broker IP (your PC's LAN IP from Step 1), and Device ID (matching what you registered above), then click **Upload**.

4. **Verify in the Dashboard**: On `http://localhost:3000/devices`, the physical device will show `ONLINE` with live temperature, humidity, and RSSI metrics streaming in real-time.

### Supported Topics
| Topic | Direction | Description |
|---|---|---|
| `iot/{device_id}/telemetry` | ESP32 → Backend | Sensor data (temp/humidity/RSSI/uptime) every 10s |
| `iot/{device_id}/heartbeat` | ESP32 → Backend | Keepalive ping every 30s |
| `iot/{device_id}/status` | ESP32 → Backend | Online/offline LWT retained message |
| `iot/{device_id}/security` | ESP32 → Backend | Attack/anomaly event → full ML/risk/isolation pipeline |

### Full hardware guide: [firmware/esp32_secureiot/HARDWARE_SETUP.md](firmware/esp32_secureiot/HARDWARE_SETUP.md)

---

## 6. Modified Files Summary (Physical Hardware Integration)

| File | Phase | Change |
|---|---|---|
| `backend/core/mongodb.py` | Ph 2 | `is_simulation: True` added to default 10 simulation devices |
| `backend/api/devices.py` | Ph 2–3 | Anti-spoofing, physical device registration, telemetry endpoints |
| `backend/services/mqtt_service.py` | Ph 2–4 | Full `MQTTIngestionService` with anti-spoofing, quarantine, security pipeline |
| `backend/app.py` | Ph 2 | MQTT service start/stop in FastAPI lifespan |
| `backend/api/health.py` | Ph 2 | MQTT service status in health endpoint |
| `backend/api/analytics.py` | Ph 3 | Physical vs simulation device counts |
| `dashboard/src/services/api.js` | Ph 3 | `registerDevice`, `getDeviceTelemetry`, `getRecentTelemetry` |
| `dashboard/src/pages/Devices.jsx` | Ph 3 | Physical/simulation badges, telemetry display, registration modal |
| `iot/telemetry_handler.py` | Ph 4 | Network-feature gating for ML, `attack_hint` fallback for risk scoring |
| `firmware/esp32_secureiot/esp32_secureiot.ino` | Ph 5 | Full ESP32 Arduino firmware |
| `firmware/esp32_secureiot/HARDWARE_SETUP.md` | Ph 5 | Hardware wiring, firewall, setup guide |
| `tests/iot/test_device_registration_and_mqtt.py` | Ph 2 | 8 new tests |
| `tests/iot/test_telemetry_persistence_and_dashboard.py` | Ph 3 | 3 new tests |
| `tests/iot/test_security_detection_and_response.py` | Ph 4 | 3 new tests |
