# SecureIoT-X — Step-by-Step Terminal Execution Guide

This document lists the exact, step-by-step commands to run each component of **SecureIoT-X** across separate terminal windows.

---

## Prerequisites Check (Run Once Before Starting)

Ensure all dependencies are installed:
```powershell
# Python Dependencies
python -m pip install -r requirements.txt
python -m pip install motor bcrypt passlib "python-jose[cryptography]" paho-mqtt web3 uuid6 structlog

# Frontend Dependencies
cd dashboard
npm install
cd ..
```

---

## Running the System (Terminal by Terminal)

Open separate PowerShell or Command Prompt terminals from the project root:  
`c:\Users\POORNA CHANDRA D N\Downloads\SecureIoT-X-main\SecureIoT-X-main`

---

### Terminal 1: MongoDB (Required Database)
MongoDB is the primary application database for threat logs, registered devices, and security metrics.

*If MongoDB runs as a Windows Service automatically, you do not need to run this command manually.*  
Otherwise, start the daemon:
```powershell
mongod --dbpath "C:\data\db"
```
- **Listening Port**: `27017`
- **URI**: `mongodb://127.0.0.1:27017/secureiot_x`

---

### Terminal 2: Ganache Blockchain (Security Audit Ledger)
Hosts the local private Ethereum ledger for recording immutable device isolation events and security blocks.
```powershell
npx ganache -p 7545 -d
```
- **Listening Port**: `7545`
- **RPC URL**: `http://127.0.0.1:7545`

---

### Terminal 3: FastAPI Backend (API & AI Inference Engine)
Runs the core backend providing REST endpoints, AI classification models, WebSocket telemetry, and automated SDN mitigation.
```powershell
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
- **Listening URL**: `http://localhost:8000` (or `http://127.0.0.1:8000`)
- **API Swagger Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

---

### Terminal 4: React Dashboard (Vite Frontend)
Runs the Security Operations Center dashboard.
```powershell
cd dashboard
npm run dev
```
*(Port 3000 and reverse proxy to `127.0.0.1:8000` are pre-configured in `vite.config.js`).*

- **Dashboard URL**: `http://localhost:3000`
- **AI Models & Governance Page**: `http://localhost:3000/ai-models`
- **Model Analytics Page**: `http://localhost:3000/model-analytics`

---

### Terminal 5 (Optional): Mosquitto MQTT Broker
*Only required if connecting physical IoT hardware (e.g., ESP32 boards) sending real sensor packets over Wi-Fi.*
```powershell
mosquitto -c mosquitto.conf -v
```
- **Listening Port**: `1883`

---

## Verification & Testing Commands

To test the system while the backend is running:

### 1. Run Automated Attack Simulation & Pipeline Check (E2E)
```powershell
python scripts/final_attack_test.py
```
*Executes all 39 checks across Attack Simulation $\to$ AI Detection $\to$ Risk Assessment $\to$ Device Isolation $\to$ Blockchain Ledger $\to$ Recovery.*

### 2. Run Test Suite
```powershell
python -m pytest tests/
```

### 3. Check Live Backend Endpoints Directly
```powershell
python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/models').json())"
```

### 4. Build Frontend for Production
```powershell
cd dashboard
npm run build
```

---

## Troubleshooting Common Errors

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `[WinError 10048] address already in use: 8000` | Another process is already running on port 8000 | Find and terminate the process: <br>`Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess \| Stop-Process` |
| `Failed to fetch` on frontend | Backend not running or port blocked | Ensure Terminal 3 (`uvicorn backend.app:app`) is running and listening on port 8000. |
| `CACError: Unused args: 3000` | Passed `-- --port 3000` to `npm run dev` | Run simply `npm run dev`. Port 3000 and proxy are set in `vite.config.js`. |
| `WinError 10061 (MQTT broker)` | Mosquitto broker not running | Normal if running in simulation mode; starts automatically when Mosquitto runs. |
