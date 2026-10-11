# SecureIoT-X — ESP32 Hardware Setup Guide

## Prerequisites

### Arduino IDE Libraries (install via Sketch → Include Library → Manage Libraries)

| Library | Author | Min Version |
|---|---|---|
| `PubSubClient` | Nick O'Leary | 2.8.0 |
| `ArduinoJson` | Benoit Blanchon | 6.21.0 |
| `DHT sensor library` | Adafruit | 1.4.4 |
| `Adafruit Unified Sensor` | Adafruit | 1.1.9 |

### ESP32 Board Package
1. Arduino IDE → File → Preferences → Additional Board Manager URLs:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
2. Tools → Board → Boards Manager → search "esp32" → Install "esp32 by Espressif Systems"
3. Select board: **ESP32 Dev Module**

---

## Hardware Wiring (DHT22 optional)

```
ESP32 GPIO 4  ─── DHT22 Data pin
ESP32 3.3V    ─── DHT22 VCC
ESP32 GND     ─── DHT22 GND
(Add 10kΩ pull-up between Data and VCC)
```

---

## Step-by-Step: Connect Your First Physical Device

### Step 1 — Find your PC's Wi-Fi IP

```powershell
# In PowerShell or CMD:
ipconfig
# Look for: Wireless LAN adapter Wi-Fi → IPv4 Address
# Example output: 10.108.133.208
```

### Step 2 — Open `esp32_secureiot.ino` in Arduino IDE

Edit the `CONFIGURATION` section at the top:

```cpp
#define WIFI_SSID        "MyHomeWiFi"          // ← Your Wi-Fi name
#define WIFI_PASSWORD    "mypassword123"        // ← Your Wi-Fi password
#define MQTT_BROKER_HOST "10.108.133.208"       // ← Your PC's Wi-Fi IP
#define DEVICE_ID        "ESP32_011"            // ← Unique ID (not 001-010)
```

### Step 3 — Register the device in SecureIoT-X

**Option A — via the Dashboard UI:**
1. Open the SecureIoT-X dashboard at `http://localhost:3000`
2. Navigate to **Devices** → click **"+ Add Device"**
3. Select **Physical ESP32 Board**, enter Device ID (e.g. `ESP32_011`, `ESP32_013`), name, and location
4. Click **Register Hardware Device**

**Option B — via API:**
```powershell
curl -X POST http://localhost:8000/api/devices `
  -H "Content-Type: application/json" `
  -d '{
        "device_id": "ESP32_011",
        "name": "Physical ESP32 Sensor #1",
        "device_type": "ESP32-WROOM-32",
        "location": "Zone-External",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "firmware_version": "1.0.0",
        "is_simulation": false
      }'
```

### Step 4 — Allow Mosquitto through Windows Firewall

```powershell
# Run as Administrator:
New-NetFirewallRule -DisplayName "Mosquitto MQTT" -Direction Inbound `
  -Protocol TCP -LocalPort 1883 -Action Allow -Profile Any
```

Verify Mosquitto is running:
```powershell
netstat -an | Select-String "1883"
# Should show:   TCP    0.0.0.0:1883   LISTENING
```

### Step 5 — Flash and monitor

1. Connect ESP32 via USB
2. Arduino IDE → Tools → Port → select COM port
3. Click **Upload** (Ctrl+U)
4. Open Serial Monitor at **115200 baud**
5. Expected output:
   ```
   ===========================================
     SecureIoT-X ESP32 Firmware v1.0.0
     Device ID : ESP32_011
     Broker    : 10.108.133.208
   ===========================================
   [WIFI] Connecting to MyHomeWiFi...........
   [WIFI] Connected! IP: 192.168.1.42
   [MQTT] Connecting to broker 10.108.133.208:1883 … attempt 1
   [MQTT] Connected!
   [STATUS] Published: online
   [TELEMETRY] T=25.4°C H=58.2% RSSI=-65dBm uptime=12s
   [HEARTBEAT] Sent
   ```

### Step 6 — Verify in SecureIoT-X Dashboard

- **Devices page**: `ESP32_011` should appear with badge **"PHYSICAL (ESP32)"** and status **Online**
- **Live telemetry**: temperature, humidity, RSSI, uptime updates every 10s
- **Health API**: `GET http://localhost:8000/api/health` → shows `mqtt_service.connected: true`

---

## Testing Security Detection & Network Quarantine

### Physical Hardware Quarantine Behavior
When a physical ESP32 device triggers an isolation response or test:
1. **Host Firewall Block:** Inbound traffic from ESP32 IP is blocked at Windows Firewall.
2. **Active Socket Drop:** Any active or incoming TCP/MQTT sockets from the ESP32 IP/device ID are dropped immediately.
3. **Hardware Radio Lockdown:** Backend publishes `QUARANTINE_RADIO_LOCK` on MQTT topic `iot/{device_id}/control`.
4. **On-Board LED Indicator:** The ESP32 lights solid its onboard blue LED (GPIO 2) to physically indicate quarantine state.
5. **Radio Disengagement:** The firmware executes `WiFi.disconnect(true)` to terminate active radio communication.
6. **Active Probe Verification:** Designated probe endpoint `/api/devices/probe/test?device_id=ESP32_011` confirms HTTP 403 `QUARANTINED_BLOCKED`.

### Two Testing Methods (UI & API)

#### 1. Via Dashboard "Test & Verify" Modal
1. Go to `http://localhost:3000/devices`.
2. Locate your physical device (marked with `PHYSICAL (ESP32)`).
3. Click the **"Test & Verify"** button in the Actions column.
4. Choose either:
   - **Category A (Model Detection Test):** Sends genuine RT_IOT2022 network flow metrics, runs authentic SVM inference, logs real Ganache transaction, triggers multi-tier quarantine, and verifies.
   - **Category B (Response Enforcement Test):** Tests physical isolation independently without simulating ML predictions. Verifies firewall, transport drop, and radio lock.
5. Click **"Check Probe Endpoint"** to verify HTTP 403 status.
6. Click **"Release Device"** to restore Wi-Fi connectivity and resume telemetry.

#### 2. Via CLI Mosquitto / API
```powershell
# Category A: Model Detection Test
curl -X POST http://localhost:8000/api/devices/ESP32_011/test/detection

# Category B: Explicit Enforcement Test
curl -X POST http://localhost:8000/api/devices/ESP32_011/test/enforcement

# Check Probe status
curl http://localhost:8000/api/devices/probe/test?device_id=ESP32_011

# Release Quarantine
curl -X POST http://localhost:8000/api/devices/ESP32_011/release
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Serial shows `[MQTT] Failed, rc=-2` | Broker unreachable — check IP address and firewall rule |
| Serial shows `[MQTT] Failed, rc=5` | Authentication rejected — check MQTT_USERNAME/PASSWORD |
| Device appears "OFFLINE" in dashboard | Check device_id matches exactly what's registered |
| `Device not registered — rejected` in backend logs | Register via Step 3 first |
| Wi-Fi connects but MQTT fails | PC and ESP32 must be on the same LAN/subnet |
| DHT shows 0.0°C / 0.0% | Check wiring or set `#define DHT_PIN -1` to disable sensor |

---

## Multiple Physical Devices

Each device needs a **unique DEVICE_ID** and separate registration:

```
ESP32_011 — First physical sensor
ESP32_012 — Second physical sensor
ESP32_013 — Third physical sensor
...
ESP32_999 — Maximum supported (ESP32_001-010 are reserved for simulation)
```

Simply copy `esp32_secureiot.ino`, change `DEVICE_ID`, register, and flash.
