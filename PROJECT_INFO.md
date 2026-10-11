# SecureIoT-X — Project Information & System Architecture

> **AI-Driven Decentralized Intrusion Detection & Response System for IoT Networks**

---

## 1. PROJECT PURPOSE

**SecureIoT-X** is an AI-driven, decentralized cybersecurity platform designed to protect Internet of Things (IoT) ecosystems. It integrates machine learning anomaly/attack classification, automated risk evaluation, active device containment/isolation, and immutable audit logging on an Ethereum blockchain (Ganache).

### Core Pipeline
1. **IoT Telemetry & Traffic Ingestion**: Ingests flow features and sensor telemetry from IoT edge devices (simulated or real hardware).
2. **Real-time Machine Learning (SVM)**: Evaluates incoming traffic flow features against a trained Support Vector Machine (RBF kernel) to detect attacks (DDoS, DoS, Reconnaissance, Brute Force, Spoofing, MITM).
3. **Multi-Factor Risk Assessment Engine**: Computes risk scores (0–100) and assigns severity levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) using AI confidence, attack severity weights, frequency, and device criticality.
4. **Automated Response & Device Containment**: Executes automated mitigations (`ALLOW`, `MONITOR`, `ISOLATE`, `BLOCK`). Devices exhibiting high/critical risk are immediately isolated to halt attack propagation.
5. **MongoDB Primary Datastore**: Stores device states, telemetry histories, attack logs, AI predictions, risk scores, and isolation events.
6. **Ganache Blockchain Notarization**: Records immutable security events and cryptographic SHA-256 integrity hashes on a real Ethereum testnet (Ganache) via Web3 transactions.
7. **Real-Time SOC Dashboard**: Delivers dynamic live telemetry, visual analytics, model comparisons, blockchain explorer, and an interactive Simulation Lab with WebSocket broadcasts.

---

## 2. COMPLETE FILE/FOLDER STRUCTURE

```
SecureIoT-X/
├── .dockerignore                                # Docker build context exclusion rules
├── .env                                         # Local environment configuration
├── .env.docker                                  # Docker container environment configuration
├── .env.example                                 # Template environment configuration
├── .gitignore                                   # Git tracking exclusion rules
├── DEBUG_REPORT.md                              # Historical diagnostic trace report
├── DOCKER.md                                    # Docker quick start and deployment guide
├── Dockerfile                                   # FastAPI backend container image definition
├── NEXT_TASK.md                                 # Historical task milestone tracker
├── PROJECT_INFO.md                              # Complete repository documentation & setup guide
├── PROJECT_STATE.md                             # AI engine integration and status record
├── TEST_STATUS.md                               # Test suite verification summary
├── blockchain_ledger.json                       # Educational demo JSON ledger for tamper tests
├── dataset_validation.py                        # Dataset verification script
├── demo.py                                      # Standalone interactive CLI demonstration
├── docker-compose.yml                           # 5-service orchestration definition
├── mosquitto.conf                               # Mosquitto MQTT broker configuration
├── pyproject.toml                               # Python project packaging metadata
├── requirements.txt                             # Python dependencies with pinned versions
├── secureiot.db                                 # SQLite database (admin authentication)
├── verify_project.py                            # End-to-end automated project verifier
│
├── ai_engine/                                   # Machine Learning & AI Subsystem
│   ├── __init__.py
│   ├── __main__.py                              # Model training CLI entrypoint
│   ├── anomaly_detection.py                     # IsolationForest / OneClassSVM detectors
│   ├── data_loader.py                           # Dataset ingestion & synthetic adapters
│   ├── evaluate.py                              # Classification metrics (F1, ROC-AUC, PR-AUC)
│   ├── explainability.py                        # Feature contribution & inference explainers
│   ├── feature_engineering.py                   # Network flow feature derivations
│   ├── feature_selection.py                     # Feature selection algorithms
│   ├── model_registry.py                        # Model metadata registry & validation
│   ├── predict.py                               # Production PredictionEngine (SVM inference)
│   ├── preprocessing.py                         # PreprocessingPipeline (scaling, encoding, imputation)
│   └── train.py                                 # Multi-model training (SVM, RF, GB, DT, LR)
│
├── backend/                                     # FastAPI Application Server
│   ├── __init__.py
│   ├── __main__.py                              # Backend startup: uvicorn backend.app:app
│   ├── app.py                                   # FastAPI app factory, CORS, lifespan, WebSocket
│   ├── api/                                     # REST API Routers
│   │   ├── __init__.py
│   │   ├── analytics.py                         # SOC stats & AI model metrics
│   │   ├── auth.py                              # JWT authentication (login, register, me)
│   │   ├── blockchain_api.py                    # Ganache status, verification, demo blocks
│   │   ├── devices.py                           # Device CRUD, approval, isolation, release
│   │   ├── health.py                            # Health check for all services
│   │   ├── models_api.py                        # Model registry, report, activation
│   │   ├── predictions.py                       # AI prediction history & live inference
│   │   ├── simulation_api.py                    # Attack simulation, pipeline, device isolation
│   │   ├── system.py                            # System logs, audit trail, configuration
│   │   └── threats.py                           # Threat intelligence network endpoints
│   ├── core/                                    # Infrastructure & Core Services
│   │   ├── __init__.py
│   │   ├── config.py                            # Pydantic Settings & YAML loader
│   │   ├── database.py                          # SQLAlchemy async/sync SQLite engine
│   │   ├── mongodb.py                           # Motor (async) & PyMongo (sync) client
│   │   ├── security.py                          # Bcrypt hashing & JWT token management
│   │   └── websocket.py                         # Real-time WebSocket connection manager
│   ├── models/                                  # SQLAlchemy ORM Models
│   │   ├── __init__.py
│   │   ├── audit.py                             # AuditLog & SystemLog entities
│   │   ├── device.py                            # Device entity
│   │   ├── event.py                             # SecurityEvent entity
│   │   ├── prediction.py                        # Prediction entity
│   │   ├── response.py                          # ResponseAction entity
│   │   ├── threat.py                            # Threat entity
│   │   └── user.py                              # User entity (auth)
│   └── services/
│       └── __init__.py
│
├── blockchain/                                  # Blockchain & Ledger Implementations
│   ├── __init__.py
│   ├── block.py                                 # Educational demo Block structure
│   ├── chain.py                                 # Educational demo SecurityBlockchain (JSON)
│   ├── ethereum_client.py                       # Low-level JSON-RPC Ethereum client
│   ├── ganache_client.py                        # Real Web3 Ganache client (SHA-256 on-chain tx)
│   └── threat_intel.py                          # Distributed Threat Intelligence Network
│
├── config/                                      # Configuration Specifications
│   ├── app.yaml                                 # Server, logging, mode, websocket configuration
│   ├── feature_schema.json                      # 15 raw features & 4 engineered flow features
│   ├── ml.yaml                                  # Hyperparameters, datasets, metrics config
│   ├── mqtt.yaml                                # Broker, topics, QoS, timeout settings
│   └── security.yaml                            # Severity weights, risk thresholds, response rules
│
├── contracts/                                   # Smart Contracts
│   ├── SecurityLedger.sol                       # Solidity contract for threat notarization
│   └── build/
│       ├── contracts_SecurityLedger_sol_SecurityLedger.abi
│       └── contracts_SecurityLedger_sol_SecurityLedger.bin
│
├── dashboard/                                   # Frontend Application (React + Vite)
│   ├── .gitignore
│   ├── .oxlintrc.json
│   ├── Dockerfile                               # Multi-stage Node build + Nginx runtime
│   ├── README.md                                # Dashboard documentation
│   ├── index.html                               # HTML5 entrypoint
│   ├── nginx.conf                               # Nginx reverse proxy (/api/ & /ws -> backend)
│   ├── package.json                             # Dependencies & scripts
│   ├── package-lock.json                        # Locked npm dependency tree
│   ├── vite.config.js                           # Vite bundler configuration
│   └── src/
│       ├── App.css
│       ├── App.jsx                              # Routing & global WebSocket lifecycle
│       ├── index.css                            # Complete design system & custom CSS
│       ├── main.jsx                             # React DOM render entrypoint
│       ├── components/
│       │   ├── Header.jsx                       # Topbar with dynamic titles & status
│       │   └── Sidebar.jsx                      # Navigation sidebar with live threat count
│       ├── pages/
│       │   ├── AIModels.jsx                     # Model registry, metrics, activation
│       │   ├── Analytics.jsx                    # SOC overview & threat charts
│       │   ├── Blockchain.jsx                   # Ledger status & tamper verification
│       │   ├── Dashboard.jsx                    # Security Operations Center home
│       │   ├── Devices.jsx                      # Connected device fleet inventory
│       │   ├── Settings.jsx                     # Microservice policies & configurations
│       │   ├── Simulation.jsx                   # Simulation Lab & Red Team attack sandbox
│       │   ├── SystemLogs.jsx                   # Audit logs & operational events
│       │   └── Threats.jsx                      # Incident monitor & mitigation logs
│       └── services/
│           └── api.js                           # Axios/Fetch API layer & WebSocket client
│
├── database/                                    # Database Tools & Seeders
│   ├── __init__.py
│   ├── migrations.py                            # Table generation & default admin creator
│   └── seed.py                                  # Test data generator
│
├── datasets/                                    # Network Traffic Datasets
│   └── RT_IOT2022.csv                           # RT-IoT2022 traffic feature dataset
│
├── firmware/
│   └── esp32_secureiot/                         # Reserved for physical ESP32 firmware
│
├── models/                                      # Trained Model Artifacts
│   ├── registry.json                            # Model registry metadata & performance logs
│   ├── preprocessing/
│   │   └── preprocessing_pipeline.joblib        # Fitted scaler and feature transformers
│   ├── svm/
│   │   └── SVM_v1_20260907.joblib               # Trained Support Vector Machine artifact
│   ├── anomaly/
│   ├── decisiontree/
│   ├── gradientboosting/
│   ├── logisticregression/
│   ├── random_forest/
│   └── randomforest/
│
├── reports/                                     # Evaluation Reports
│   ├── full_training_report.json
│   ├── model_report.json
│   └── verification_report.json
│
├── scripts/                                     # Utility Scripts
│   ├── __init__.py
│   ├── final_attack_test.py
│   └── setup_dataset.py
│
├── sdn/                                         # Software-Defined Networking
│   ├── __init__.py
│   └── mock_controller.py                       # Simulated OpenFlow flow rule enforcer
│
├── security/                                    # Threat & Risk Engines
│   ├── __init__.py
│   ├── event_lifecycle.py                       # State machine for incident tracking
│   ├── notification_service.py                  # Alert dispatcher
│   ├── response_engine.py                       # Mitigation decision & execution engine
│   └── risk_engine.py                           # Multi-factor risk calculation engine
│
├── simulation/                                  # Traffic Simulation Subsystem
│   ├── __init__.py
│   ├── __main__.py                              # Traffic generator CLI runner
│   └── traffic_generator.py                     # Synthetic traffic generator (10 devices)
│
└── tests/                                       # Automated Test Suite (124 tests)
    ├── __init__.py
    ├── conftest.py                              # Pytest fixtures & async test runner
    ├── api/
    ├── blockchain/
    ├── e2e/
    ├── integration/
    ├── iot/
    ├── ml/
    ├── security/
    └── unit/
```

---

## 3. TECHNOLOGY STACK

| Component | Technology | Version | Key Details |
|---|---|---|---|
| **Backend** | Python / FastAPI / Uvicorn | Python 3.10, FastAPI 0.115.6, Uvicorn 0.34.0 | Async REST API, WebSockets, Lifespan hooks |
| **Frontend** | React / Vite / Nginx | React 19.2.8, Vite 8.2.2, Nginx 1.25+ | Modern SPA, Recharts 3.10.1, Lucide React, Nginx proxy |
| **SVM / ML** | Scikit-Learn | Scikit-Learn 1.6.1, NumPy 1.26.4, Pandas 2.2.3 | `sklearn.svm.SVC` with RBF kernel, `probability=True` |
| **MongoDB** | MongoDB / Motor / PyMongo | Mongo 7.0, Motor 3.5.1, PyMongo 4.18.1 | Primary datastore for devices, telemetry, attacks, logs |
| **Ganache** | Truffle Ganache / Web3.py | Ganache latest (CLI), Web3.py 7.6.0 | Real Ethereum testnet, Chain ID 1337, Port 7545/8545 |
| **MQTT** | Eclipse Mosquitto / Paho-MQTT | Mosquitto 2.0, Paho-MQTT 2.1.0 | IoT publish/subscribe message broker on port 1883 |
| **Docker** | Docker / Docker Compose | Compose file v2/v3 syntax | 5-service isolated stack with volume persistence |

---

## 4. BACKEND

- **Entry Point**: `python -m backend` (`backend/__main__.py`), which invokes `uvicorn.run("backend.app:app", host=settings.backend_host, port=settings.backend_port, reload=settings.debug)`.
- **Ports**: `8000` (FastAPI HTTP REST API & WebSocket endpoint `/ws`).
- **Application Factory**: `create_app()` in `backend/app.py`.
- **API Endpoints**:
  - `/api/health` — Comprehensive health check for SQLite, MongoDB, Ganache, AI models, and SDN.
  - `/api/auth/login`, `/api/auth/register`, `/api/auth/me` — JWT user authentication.
  - `/api/devices` — CRUD operations, device approval, manual isolation, and release.
  - `/api/predict`, `/api/predictions` — Direct AI inference and prediction history.
  - `/api/threats` — Threat intelligence creation, verification, and sharing.
  - `/api/blockchain/status`, `/api/blockchain/verify`, `/api/blockchain/record` — Ganache node status and event notarization.
  - `/api/blockchain/ganache/status`, `/api/blockchain/ganache/verify/{tx_hash}` — Ganache transaction status and payload decoders.
  - `/api/blockchain/demo/blocks`, `/api/blockchain/tamper-test` — Educational demo hash-chain.
  - `/api/models`, `/api/models/production`, `/api/models/{name}/activate`, `/api/models/report` — ML model registry and comparison.
  - `/api/analytics/overview`, `/api/analytics/metrics`, `/api/analytics/comparison` — SOC overview counters and ML evaluation metrics.
  - `/api/system/logs`, `/api/system/audit`, `/api/system/settings` — System logs and audit trail.
  - `/api/simulate/attack` — Full attack simulation pipeline (generates attack, runs SVM, computes risk, determines response, isolates device, saves to MongoDB, records to Ganache, broadcasts via WebSocket).
  - `/api/simulate/release` — Releases isolated device back to `NORMAL`.
  - `/api/simulate/devices` — Fetches current state of all simulation devices from MongoDB.
  - `/api/simulate/event`, `/api/simulate/scenario`, `/api/simulate/scenarios` — Predefined attack sequence generators.
  - `/ws` — Live WebSocket connection for SOC alerts (`attack_simulated`, `threat_detected`, `device_isolated`, `device_released`).
- **Important Services / Classes**:
  - `Settings` (`backend/core/config.py`): Pydantic BaseSettings loading `.env`, `.env.docker`, and YAML configs.
  - `ConnectionManager` (`backend/core/websocket.py`): Manages active WebSocket connections and client broadcasts.
  - `GanacheClient` (`blockchain/ganache_client.py`): Web3 client sending real Ethereum transactions.
  - `PredictionEngine` (`ai_engine/predict.py`): Production inference engine with preprocessing and calibration.
  - `RiskEngine` (`security/risk_engine.py`): Computes 0–100 risk score and severity from multiple factors.
  - `ResponseEngine` (`security/response_engine.py`): Determines mitigation actions and triggers containment.
  - `TrafficGenerator` (`simulation/traffic_generator.py`): Generates RFC-compliant network flow features.
- **Dependencies**: Listed in `requirements.txt` (`fastapi`, `uvicorn`, `motor`, `pymongo`, `web3`, `scikit-learn`, `pandas`, `numpy`, `joblib`, `paho-mqtt`, `python-jose`, `passlib`, `bcrypt`, `sqlalchemy`, `aiosqlite`).

---

## 5. FRONTEND

- **Architecture**: Single Page Application built with React 19 and Vite. Served via Nginx in Docker.
- **Pages** (`dashboard/src/pages/`):
  1. `Dashboard.jsx`: Security Operations Center with real-time incident counters, attack distribution charts, and device health cards.
  2. `Threats.jsx`: Real-time threat log with incident details and response action tracking.
  3. `Devices.jsx`: Connected IoT device inventory with manual isolation and release triggers.
  4. `AIModels.jsx`: Model registry cards, radar chart comparisons, and interactive live benchmark inference tester.
  5. `Blockchain.jsx`: Real-time blockchain ledger explorer, Ganache verification, and cryptographic tamper detection demo.
  6. `Analytics.jsx`: Risk intelligence metrics, attack breakdown charts, and historical threat statistics.
  7. `Simulation.jsx`: Simulation Lab & Red Team sandbox for injecting attacks against simulation devices.
  8. `SystemLogs.jsx`: Filterable system event logs and security audit trail.
  9. `Settings.jsx`: System microservice policies, risk thresholds, and active environment status.
- **Components** (`dashboard/src/components/`):
  - `Header.jsx`: Top navigation header displaying dynamic page titles and system health badge.
  - `Sidebar.jsx`: Navigation menu with active route highlighting and live threat count badge.
- **API Configuration** (`dashboard/src/services/api.js`):
  - In Docker, builds with `VITE_API_BASE=/api`. Nginx (`dashboard/nginx.conf`) proxies `/api/` to `http://backend:8000/api/` and `/ws` to `http://backend:8000/ws`.
  - In local development, falls back to `http://localhost:8000/api` and `ws://localhost:8000/ws`.
- **Simulation Lab Implementation**:
  - Dynamically queries `/api/simulate/devices` to populate the device selection dropdown with all 10 MongoDB simulation devices.
  - Allows selecting specific attack vectors (DDoS, DoS, Reconnaissance, Brute Force, Spoofing, MITM).
  - Dispatches `api.simulateAttack(selectedDevice, attackType)`.
  - Receives real structured pipeline execution steps from the backend and renders them in real time.
  - Displays real Ganache transaction hash and block number directly on screen.
  - Shows containment warnings when a device is isolated and allows one-click recovery via `api.releaseSimDevice(deviceId)`.

---

## 6. SVM / MACHINE LEARNING SUBSYSTEM

- **Model Files**:
  - `models/svm/SVM_v1_20260907.joblib` (1.87 MB serialized `sklearn.svm.SVC` model).
  - `models/preprocessing/preprocessing_pipeline.joblib` (serialized `PreprocessingPipeline` containing fitted scaler and encoders).
  - `models/registry.json` (metadata, parameters, and validation logs for all models).
- **Features** (`config/feature_schema.json`):
  - **15 Raw Network Flow Features**: `flow_duration`, `fwd_pkts_tot`, `bwd_pkts_tot`, `fwd_data_pkts_tot`, `bwd_data_pkts_tot`, `fwd_pkts_per_sec`, `bwd_pkts_per_sec`, `flow_pkts_per_sec`, `fwd_byts_per_sec`, `bwd_byts_per_sec`, `fwd_pkts_payload_avg`, `bwd_pkts_payload_avg`, `proto`, `dst_port`, `conn_state_num`.
  - **4 Engineered Features**:
    - `packet_rate`: `fwd_pkts_tot / max(flow_duration, 1e-6)`
    - `fwd_bwd_ratio`: `fwd_pkts_tot / (bwd_pkts_tot + 1)`
    - `total_pkts`: `fwd_pkts_tot + bwd_pkts_tot`
    - `traffic_asymmetry`: `(fwd_pkts_per_sec - bwd_pkts_per_sec) / (fwd_pkts_per_sec + bwd_pkts_per_sec + 1e-6)`
- **Preprocessing Pipeline** (`ai_engine/preprocessing.py`):
  - Preprocessing class: `PreprocessingPipeline`.
  - Missing value imputation via `SimpleImputer(strategy='median')`.
  - Feature normalization via `StandardScaler`.
  - Infinite and NaN value sanitization with `np.nan_to_num`.
  - Categorical encoding with `LabelEncoder`.
  - Strict zero-leakage enforcement verified: train/test split precedes fitting; transformers are fitted strictly on training data.
- **Training** (`ai_engine/train.py`):
  - Model constructor: `build_svm_model(params)` instantiating `sklearn.svm.SVC(probability=True, random_state=42, kernel='rbf', class_weight='balanced', max_iter=5000)`.
  - Primary training dataset: `datasets/RT_IOT2022.csv`.
- **Inference** (`ai_engine/predict.py`):
  - Handled by `PredictionEngine`.
  - Accepts raw feature dictionary, applies `PreprocessingPipeline.transform()`, executes `model.predict()` and `model.predict_proba()`.
  - Calculates confidence score: `float(np.max(proba))`.
  - If confidence < `min_confident` (0.60), classifies as `SUSPICIOUS_UNKNOWN`.
  - Returns: `prediction_id`, `prediction`, `confidence`, `model`, `model_version`, `device_id`, `inference_time_ms`, `timestamp`.
- **Dependencies**: `scikit-learn==1.6.1`, `pandas==2.2.3`, `numpy==1.26.4`, `joblib==1.4.2`, `xgboost==2.1.4`.

---

## 7. SIMULATION LAB

- **Registered Simulation Devices**:
  - `ESP32_001` (Temperature Sensor, `192.168.1.101`, Zone-A)
  - `ESP32_002` (Motion Sensor, `192.168.1.102`, Zone-A)
  - `ESP32_003` (Camera Gateway, `192.168.1.103`, Zone-B)
  - `ESP32_004` (Smart Lock, `192.168.1.104`, Zone-B)
  - `ESP32_005` (HVAC Controller, `192.168.1.105`, Zone-C)
  - `ESP32_006` (Light Controller, `192.168.1.106`, Zone-C)
  - `ESP32_007` (Air Quality Monitor, `192.168.1.107`, Zone-D)
  - `ESP32_008` (Water Meter, `192.168.1.108`, Zone-D)
  - `ESP32_009` (Power Monitor, `192.168.1.109`, Zone-E)
  - `ESP32_010` (Industrial Pump Gateway, `192.168.1.110`, Zone-E)
- **Supported Attack Vectors**:
  - `DDoS` (Volumetric UDP/TCP flood, Critical severity)
  - `DoS` (Connection table exhaustion flood, Critical severity)
  - `Reconnaissance` (Port scan recon on ports 22, 80, 502, 1883, High severity)
  - `Brute_Force` (Authentication dictionary attack against broker, High severity)
  - `Spoofing` (ARP spoofing / cache poisoning, High severity)
  - `MITM` (Man-in-the-middle MQTT packet interception, Critical severity)
- **Simulation REST API**:
  - `POST /api/simulate/attack`: Triggers full end-to-end detection and response pipeline.
  - `POST /api/simulate/release`: Releases an isolated device back to normal status.
  - `GET /api/simulate/devices`: Lists all simulation devices and current containment states.
  - `POST /api/simulate/event`: Generates single event.
  - `POST /api/simulate/scenario`: Runs predefined multi-stage attack scenarios.
- **End-to-End Pipeline Execution**:
  1. **Containment Check**: Verifies if target device is currently marked `is_isolated: True` in MongoDB. If isolated, execution halts and returns a `BLOCKED` status.
  2. **Traffic Generation**: `TrafficGenerator.generate_attack()` produces realistic network flow metrics.
  3. **SVM Inference**: `PredictionEngine.predict()` classifies features using the trained SVM model.
  4. **Risk Calculation**: `RiskEngine.calculate_risk()` computes composite score (0–100) and severity (`HIGH` or `CRITICAL`).
  5. **Response Decision**: `ResponseEngine.decide_response()` assigns `ISOLATE` or `BLOCK`.
  6. **MongoDB Persistence**: Injects records into `attack_events`, `predictions`, `risk_scores`, `response_actions`, and `isolation_events`. Updates device status in `devices`.
  7. **Ganache Notarization**: `GanacheClient.record_security_event()` submits an Ethereum transaction embedding SHA-256 event integrity hash.
  8. **WebSocket Broadcast**: Emits `attack_simulated`, `threat_detected`, and `device_isolated` to connected frontend clients.
- **Release / Recovery Flow**:
  - User triggers release in UI or calls `POST /api/simulate/release`.
  - MongoDB updates `is_isolated: False`, `security_status: "NORMAL"`.
  - Event logged in `isolation_events`.
  - WebSocket broadcasts `device_released`. Traffic flow resumes.

---

## 8. MONGODB

- **Connection Setup**:
  - Managed in `backend/core/mongodb.py`.
  - Connection string configured via `MONGODB_URI` environment variable.
  - Local default: `mongodb://localhost:27017/secureiot_x`
  - Docker container default: `mongodb://mongodb:27017/secureiot_x`
  - Uses `AsyncIOMotorClient` for asynchronous FastAPI endpoints and `MongoClient` for synchronous CLI tools.
- **Database Name**:
  - Derived from URI or defaults to `secureiot_x`.
- **Collections & Indexes**:
  - `devices` (indexed on `device_id` unique)
  - `telemetry` (compound index on `device_id: 1, timestamp: -1`)
  - `attack_events` (compound index on `device_id: 1, timestamp: -1`)
  - `predictions` (compound index on `device_id: 1, timestamp: -1`)
  - `risk_scores` (compound index on `device_id: 1, timestamp: -1`)
  - `isolation_events` (compound index on `device_id: 1, timestamp: -1`)
  - `response_actions` (compound index on `device_id: 1, timestamp: -1`)
  - `blockchain_records` (indexed on `tx_hash` unique sparse)
- **Key Document Fields**:
  - `devices`: `device_id`, `device_type`, `ip_address`, `location`, `is_online`, `is_isolated`, `security_status`, `threat_count`, `total_events`, `last_seen`
  - `attack_events`: `event_id`, `device_id`, `attack_type`, `predicted_attack`, `confidence`, `model`, `risk_score`, `severity`, `action`, `packet_count`, `protocol`, `timestamp`
  - `predictions`: `prediction_id`, `event_id`, `device_id`, `prediction`, `confidence`, `model`, `risk_score`, `severity`, `recommended_action`, `timestamp`
  - `isolation_events`: `event_id`, `device_id`, `action`, `attack_type`, `risk_score`, `severity`, `timestamp`
  - `blockchain_records`: `event_id`, `device_id`, `tx_hash`, `block_number`, `block_hash`, `event_hash`, `status`, `gas_used`, `chain_id`, `timestamp`
- **Read / Write Code Locations**:
  - Initial seed: `backend/core/mongodb.py` (`init_mongodb()` seeds 10 default simulation devices).
  - Health check: `backend/core/mongodb.py` (`check_mongodb_health()` calls `db.command("ping")` and counts documents).
  - Simulation read/write: `backend/api/simulation_api.py` (reads device isolation state; writes to all 8 collections).

---

## 9. GANACHE (ETHEREUM BLOCKCHAIN)

- **Configuration**:
  - Runs in Docker via `trufflesuite/ganache:latest` or standalone Ganache instance.
  - Network Chain ID: `1337`
  - Gas limit: `10000000`
  - Host binding: `0.0.0.0`
  - Deterministic wallet enabled (`--wallet.deterministic` generates 10 pre-funded accounts with 100 ETH each).
- **RPC Endpoints**:
  - Docker container-to-container: `http://ganache:8545`
  - Local host access: `http://127.0.0.1:7545`
- **Smart Contract**:
  - `contracts/SecurityLedger.sol`: Implements `recordEvent(eventId, deviceId, attackType, severity, eventHash)` and emits `SecurityEventRecorded`.
  - Compiled bytecode and ABI located in `contracts/build/`.
- **Direct Ledger Transaction Model**:
  - `GanacheClient` operates using a direct on-chain notarization model. It compiles event metadata and the calculated SHA-256 event hash into a UTF-8 JSON transaction payload (`data_bytes`).
  - Sends a real Ethereum transaction from the unlocked default account (`accounts[0]`) or signed via `GANACHE_PRIVATE_KEY`.
  - Waits for on-chain mining receipt (`w3.eth.wait_for_transaction_receipt(tx_hash, timeout=15)`).
  - Extracts real transaction hash, block number, gas used, and block hash.
  - A pre-deployed contract address is therefore **optional**; on-chain notarization functions out-of-the-box using native transactions.
- **GanacheClient Implementation** (`blockchain/ganache_client.py`):
  - `is_connected()`: Verifies RPC reachability.
  - `get_status()`: Returns chain ID, latest block number, account balances, and account count.
  - `record_security_event(event_data)`: Submits real transaction and returns receipt metadata.
  - `verify_transaction(tx_hash)`: Fetches transaction from chain and decodes original payload data.
- **Files That Call Blockchain**:
  - `blockchain/ganache_client.py`: Core Web3 client.
  - `backend/api/simulation_api.py`: Dispatches real Ganache transactions during attack simulations.
  - `backend/api/blockchain_api.py`: Serves Ganache status (`/ganache/status`), verification (`/ganache/verify/{tx_hash}`), and event recording.
  - `backend/api/health.py`: Verifies Ganache connectivity for system health reporting.
  - `tests/e2e/test_simulation_e2e.py`: Automated E2E verification of Ganache transaction generation.
- **Confirmation of Simulation Lab Blockchain**:
  - **CONFIRMED: The Simulation Lab uses REAL Ganache exclusively.** `backend/api/simulation_api.py` imports and invokes `blockchain.ganache_client.get_ganache_client()`. Real Ethereum transactions are mined into Ganache blocks with verifiable `0x...` 66-character hashes. The legacy JSON-based hash-chain (`SecurityBlockchain` / `blockchain_ledger.json`) is restricted strictly to educational tamper demonstration endpoints (`/tamper-test`).

---

## 10. MQTT

- **Broker**: Eclipse Mosquitto (Docker image `eclipse-mosquitto:2` or local Mosquitto service).
- **Port**: `1883`
- **Configuration** (`mosquitto.conf`):
  ```conf
  listener 1883
  allow_anonymous true
  ```
- **Topic Hierarchy** (`config/mqtt.yaml`):
  - `iot/{device_id}/telemetry` — Periodic sensor readings (QoS 0)
  - `iot/{device_id}/heartbeat` — Keep-alive pings (QoS 0)
  - `iot/{device_id}/status` — Online / offline status transitions (QoS 0)
  - `iot/{device_id}/security` — Threat and alert notifications (QoS 1)
  - `iot/{device_id}/response` — Actuation and containment commands (QoS 1)
  - Wildcard subscriptions: `iot/+/telemetry`, `iot/+/heartbeat`, `iot/+/status`
- **Publishers & Subscribers**:
  - `RealMQTTClient` (`iot/mqtt_client.py`): Wraps `paho-mqtt` with auto-reconnect and topic dispatching.
  - `SimulatedMQTTClient` (`iot/mqtt_client.py`): In-memory fallback for environments without an active broker.
  - `TelemetryHandler` (`iot/telemetry_handler.py`): Subscribes to telemetry topics and pipes packets through the AI engine.

---

## 11. DOCKER ARCHITECTURE

### Dockerfiles
1. **Backend** (`./Dockerfile`):
   - Base image: `python:3.10-slim`
   - Builds system dependencies (`gcc`, `g++`)
   - Installs `requirements.txt`
   - Copies application modules (`backend`, `ai_engine`, `blockchain`, `security`, `simulation`, `iot`, `config`, `database`, `sdn`, `contracts`, `models`, `datasets`)
   - Healthcheck: `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"`
   - Command: `python -m backend`
2. **Dashboard** (`./dashboard/Dockerfile`):
   - Multi-stage build
   - Stage 1 (Builder): `node:20-alpine`, runs `npm ci` and `npm run build` with `VITE_API_BASE=/api`
   - Stage 2 (Server): `nginx:alpine`, copies built assets and `nginx.conf`
   - Port: `3000`

### Docker Compose Services (`docker-compose.yml`)
- **`mongodb`**:
  - Image: `mongo:7`
  - Ports: `27017:27017`
  - Volumes: `secureiot_mongo_data:/data/db`
  - Health check: `mongosh --eval "db.adminCommand('ping')"`
- **`ganache`**:
  - Image: `trufflesuite/ganache:latest`
  - Ports: `7545:8545`
  - Volumes: `secureiot_ganache_data:/ganache_data`
  - Command: `--chain.chainId 1337 --database.dbPath /ganache_data --wallet.deterministic --wallet.totalAccounts 10 --miner.blockGasLimit 10000000 --server.host 0.0.0.0`
- **`mqtt`**:
  - Image: `eclipse-mosquitto:2`
  - Ports: `1883:1883`
  - Volumes: `./mosquitto.conf:/mosquitto/config/mosquitto.conf:ro`
- **`backend`**:
  - Context: `.`, Dockerfile: `Dockerfile`
  - Ports: `8000:8000`
  - Environment file: `.env.docker`
  - Depends on: `mongodb` (condition: service_healthy), `ganache` (started), `mqtt` (started)
- **`dashboard`**:
  - Context: `./dashboard`, Dockerfile: `Dockerfile`
  - Ports: `3000:3000`
  - Depends on: `backend`

---

## 12. ENVIRONMENT VARIABLES

| Name | Purpose | Used By | Example / Safe Value |
|---|---|---|---|
| `APP_NAME` | Application identifier | `backend/core/config.py` | `SecureIoT-X` |
| `APP_ENV` | Runtime environment mode | `backend/core/config.py` | `development` |
| `DEBUG` | Verbose logging & hot reloading | `backend/core/config.py` | `true` |
| `LOG_LEVEL` | Logging verbosity | `backend/core/config.py` | `INFO` |
| `BACKEND_HOST` | Backend server bind IP | `backend/core/config.py` | `0.0.0.0` |
| `BACKEND_PORT` | Backend server port | `backend/core/config.py` | `8000` |
| `FRONTEND_PORT` | Dashboard port | `backend/core/config.py` | `3000` |
| `DATABASE_URL` | SQLite database connection string | `backend/core/database.py` | `sqlite:///./secureiot.db` |
| `MONGODB_URI` | Primary MongoDB connection URI | `backend/core/mongodb.py` | `mongodb://mongodb:27017/secureiot_x` (Docker) / `mongodb://localhost:27017/secureiot_x` (Local) |
| `GANACHE_RPC_URL` | Ganache Ethereum JSON-RPC endpoint | `blockchain/ganache_client.py` | `http://ganache:8545` (Docker) / `http://127.0.0.1:7545` (Local) |
| `GANACHE_CHAIN_ID` | Ethereum network chain ID | `blockchain/ganache_client.py` | `1337` |
| `GANACHE_PRIVATE_KEY` | Optional transaction signing key | `blockchain/ganache_client.py` | `[REDACTED]` (Leave blank for default Ganache unlocked account) |
| `CONTRACT_ADDRESS` | Address of deployed contract | `blockchain/ethereum_client.py`| `[REDACTED]` (Leave blank to use direct transaction ledger) |
| `JWT_SECRET_KEY` | Secret key for JWT signing | `backend/core/security.py` | `[REDACTED]` |
| `JWT_ALGORITHM` | JWT signing algorithm | `backend/core/security.py` | `HS256` |
| `JWT_EXPIRY_MINUTES` | JWT token lifetime | `backend/core/security.py` | `60` |
| `MQTT_HOST` | Hostname of MQTT broker | `iot/mqtt_client.py` | `mqtt` (Docker) / `localhost` (Local) |
| `MQTT_PORT` | Port of MQTT broker | `iot/mqtt_client.py` | `1883` |
| `MQTT_USERNAME` | Username for MQTT authentication | `iot/mqtt_client.py` | `""` |
| `MQTT_PASSWORD` | Password for MQTT authentication | `iot/mqtt_client.py` | `[REDACTED]` |
| `MQTT_KEEPALIVE` | MQTT heartbeat interval in seconds | `iot/mqtt_client.py` | `60` |
| `DEFAULT_ADMIN_USERNAME` | Initial administrator username | `database/migrations.py` | `admin` |
| `DEFAULT_ADMIN_PASSWORD` | Initial administrator password | `database/migrations.py` | `[REDACTED]` |
| `DEFAULT_ADMIN_EMAIL` | Initial administrator email | `database/migrations.py` | `admin@secureiot.local` |
| `ML_MODELS_DIR` | Directory storing model weights | `ai_engine/model_registry.py` | `models` |
| `ML_DATASET_PATH` | Path to training dataset | `backend/core/config.py` | `datasets/RT_IOT2022.csv` |
| `ML_RANDOM_SEED` | Pseudo-random seed for ML | `ai_engine/train.py` | `42` |
| `ML_TEST_SIZE` | Test split ratio | `ai_engine/train.py` | `0.2` |
| `ML_VALIDATION_SIZE` | Validation split ratio | `ai_engine/train.py` | `0.1` |
| `BLOCKCHAIN_DIFFICULTY` | Difficulty for demo JSON chain | `blockchain/chain.py` | `2` |
| `BLOCKCHAIN_DB_PATH` | File path for demo JSON ledger | `blockchain/chain.py` | `blockchain_ledger.json` |
| `SDN_MODE` | SDN controller driver mode | `sdn/mock_controller.py` | `mock` |
| `RYU_HOST` | Hostname for Ryu controller | `backend/core/config.py` | `localhost` |
| `RYU_PORT` | Port for Ryu controller | `backend/core/config.py` | `6633` |
| `VITE_API_BASE` | Frontend API base URL prefix | `dashboard/src/services/api.js`| `/api` (Docker) / `http://localhost:8000/api` (Local) |

---

# NEW DEVICE SETUP

Complete guide for setting up and running SecureIoT-X on a fresh machine.

### A. Required Software
- **Docker Desktop** (version 24.0+ recommended; includes Docker Compose v2)
- **Git** (version 2.30+)
- *(Optional for bare-metal non-Docker run)*: Python 3.10+, Node.js 20+, MongoDB 7.0+, Ganache GUI or CLI.

### B. Clone / Copy Command
```powershell
git clone <repository_url> SecureIoT-X
cd SecureIoT-X
```

### C. Required Files to Copy
If copying manually across machines, ensure the following core files and folders are included:
- Source code: `backend/`, `dashboard/`, `ai_engine/`, `blockchain/`, `security/`, `simulation/`, `iot/`, `config/`, `database/`, `sdn/`, `contracts/`
- Trained models: `models/svm/SVM_v1_20260907.joblib`, `models/preprocessing/preprocessing_pipeline.joblib`, `models/registry.json`
- Datasets: `datasets/RT_IOT2022.csv`
- Docker configs: `docker-compose.yml`, `Dockerfile`, `dashboard/Dockerfile`, `dashboard/nginx.conf`, `mosquitto.conf`, `.dockerignore`, `.env.docker`
- Environment files: `.env.example`, `.env`

### D. Environment Configuration (.env & .env.docker)
For Docker, `.env.docker` is already configured with container hostnames and safe default secrets.
Ensure the following hostnames are used for Docker inter-container communication:
- MongoDB URI: `mongodb://mongodb:27017/secureiot_x`
- Ganache RPC: `http://ganache:8545`
- MQTT Host: `mqtt`

For local non-Docker development, copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure local hostnames are set in `.env`:
- `MONGODB_URI=mongodb://localhost:27017/secureiot_x`
- `GANACHE_RPC_URL=http://127.0.0.1:7545`
- `MQTT_HOST=localhost`

### E. MongoDB Setup
- **Docker**: Runs automatically via `mongo:7` container with persistent volume `secureiot_mongo_data`.
- **Local**: Install MongoDB Community Server, then start the service:
  ```powershell
  net start MongoDB
  ```

### F. Ganache Setup
- **Docker vs Standalone**: Ganache runs automatically inside Docker via the `ganache` service (`trufflesuite/ganache:latest`).
- **Exact RPC Endpoint**:
  - Inside Docker network: `http://ganache:8545`
  - On host machine: `http://localhost:7545`
- **Account / Private Key Requirements**: Ganache initializes 10 pre-funded accounts with 100 ETH each using deterministic key derivation (`--wallet.deterministic`). No manual account funding or private key entry is required.
- **Contract Deployment**: Smart contract pre-deployment is **not required**. `GanacheClient` dispatches on-chain transactions directly embedding SHA-256 integrity payloads.

### G. MQTT Setup
- **Docker**: Mosquitto runs automatically via the `mqtt` container.
- **Local**: Run Mosquitto broker on port 1883 with `mosquitto.conf`.

### H. Backend Startup Command (Local Bare-Metal)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend
```

### I. Dashboard Startup Command (Local Bare-Metal)
```powershell
cd dashboard
npm install
npm run dev
```

### J. Docker Startup Command (Recommended)
```powershell
docker compose up --build
```
Or to run in the background:
```powershell
docker compose up -d --build
```

### K. Exact Order to Start Services
When running without Docker Compose, start services in this order:
1. **MongoDB** (`localhost:27017`)
2. **Ganache** (`localhost:7545`)
3. **MQTT Broker** (`localhost:1883`)
4. **FastAPI Backend** (`python -m backend`)
5. **React Dashboard** (`npm run dev`)
*(Note: `docker compose up` manages this dependency order automatically via `depends_on`.)*

### L. Health-Check Commands
```powershell
# Check backend health and all attached services:
curl http://localhost:8000/api/health
```

### M. Verify MongoDB Connection
```powershell
# Using mongosh (inside container):
docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Check seeded simulation devices in MongoDB:
curl http://localhost:8000/api/simulate/devices
```

### N. Verify Ganache Connection
```powershell
# Query Ganache status through backend:
curl http://localhost:8000/api/blockchain/ganache/status
```

### O. Verify Real Ganache Transaction
```powershell
# Run a single attack simulation to generate a transaction:
curl -X POST http://localhost:8000/api/simulate/attack `
  -H "Content-Type: application/json" `
  -d '{\"device_id\": \"ESP32_003\", \"attack_type\": \"DDoS\"}'

# Verify the resulting transaction hash (replace with returned tx_hash):
curl http://localhost:8000/api/blockchain/ganache/verify/<TX_HASH>
```

### P. Open Dashboard
Open your browser and navigate to:
```
http://localhost:3000
```

### Q. Run Simulation Lab
1. In the sidebar, click **Simulation Lab** (`/simulation`).
2. Select target device from the dropdown (e.g., `ESP32_003 - Camera Gateway`).
3. Click any attack button (e.g., **Launch Attack** on DDoS SYN Flood).
4. Watch the real-time execution log display each pipeline phase.

### R. Verify Complete Pipeline Test
Check the UI or API response for:
- `TRAFFIC_GENERATION`: Features generated (`fwd_pkts_tot`, rates, ports).
- `SVM_INFERENCE`: Prediction made with confidence score.
- `RISK_ASSESSMENT`: Risk score calculated (`CRITICAL` / `HIGH`).
- `RESPONSE_ENGINE`: Action assigned (`ISOLATE`).
- `DEVICE_ISOLATION`: Device status updated to `ISOLATED` in MongoDB.
- `MONGODB_PERSIST`: Event saved to MongoDB collections.
- `GANACHE_BLOCKCHAIN`: Real transaction hash and block number generated.
- `DASHBOARD`: Live alerts received via WebSocket.

### S. Release / Recover Device
In the Simulation Lab UI, click **Release Device** next to the target device, or call:
```powershell
curl -X POST http://localhost:8000/api/simulate/release `
  -H "Content-Type: application/json" `
  -d '{\"device_id\": \"ESP32_003\"}'
```

### T. Stop / Shutdown Commands
```powershell
# Stop all Docker containers:
docker compose down

# Stop and wipe persistent database volumes (clean slate):
docker compose down -v
```

---

# PORTABILITY CHECK

### Portability Assessment
Can the project run on a fresh machine with `docker compose up --build`?

**Result**: **YES, the project is portable and container-ready.**

### Analysis & Verification
1. **Container Images**: All 5 services (`mongodb`, `ganache`, `mqtt`, `backend`, `dashboard`) have concrete image definitions and multi-stage Dockerfiles.
2. **Pre-packaged Artifacts**: The trained SVM model (`SVM_v1_20260907.joblib`), preprocessing pipeline, and dataset are copied directly into the backend Docker image.
3. **Internal Hostnames**: The backend connects to `mongodb:27017`, `ganache:8545`, and `mqtt:1883` via `.env.docker`.
4. **Volume Persistence**: MongoDB and Ganache utilize named Docker volumes (`secureiot_mongo_data`, `secureiot_ganache_data`).
5. **Reverse Proxy**: Nginx proxies `/api/` and `/ws` internally to `http://backend:8000`, eliminating CORS and cross-origin WebSocket barriers.
6. **Self-Seeding**: The backend automatically seeds 10 default simulation devices into MongoDB and creates the initial administrator user on startup.

### Missing Requirements / Prerequisites on Host
- **Host Port Availability**: Host machine must not have existing services listening on ports `3000`, `7545`, `8000`, `1883`, or `27017`.
- **Docker Desktop**: Docker Desktop (or Docker Engine + Compose plugin) must be installed and running.

---

# RUN COMMAND TABLE

| Step | PowerShell Command | Purpose |
|---|---|---|
| **1. Clone Repository** | `git clone <repo_url> SecureIoT-X; cd SecureIoT-X` | Obtain project files |
| **2. Verify Host Ports** | `Get-NetTCPConnection -LocalPort 3000,7545,8000,1883,27017 -ErrorAction SilentlyContinue` | Confirm ports are not currently in use |
| **3. Build & Run (Docker)** | `docker compose up --build` | Launch entire 5-service stack |
| **4. Check Container Status** | `docker compose ps` | Verify all 5 containers are running |
| **5. Health Check API** | `curl http://localhost:8000/api/health` | Verify backend, MongoDB, Ganache status |
| **6. Query Simulation Devices**| `curl http://localhost:8000/api/simulate/devices` | Confirm 10 devices are seeded in MongoDB |
| **7. Inject Attack (E2E Test)**| `curl -X POST http://localhost:8000/api/simulate/attack -H "Content-Type: application/json" -d '{\"device_id\":\"ESP32_003\",\"attack_type\":\"DDoS\"}'` | Run complete attack-to-blockchain pipeline |
| **8. Release Device** | `curl -X POST http://localhost:8000/api/simulate/release -H "Content-Type: application/json" -d '{\"device_id\":\"ESP32_003\"}'` | Restore device to NORMAL status |
| **9. View Live Logs** | `docker compose logs -f backend ganache` | Stream backend and blockchain activity |
| **10. Run Full Test Suite** | `python -m pytest tests -q` | Execute all 124 automated tests |
| **11. Stop All Services** | `docker compose down` | Safely terminate containers |
| **12. Reset All Data** | `docker compose down -v` | Terminate and clear persistent volumes |

---

## CURRENT STATUS

- **Backend**: **WORKING** (FastAPI app factory, router definitions, CORS, lifespan hooks, and WebSocket manager fully operational; health check verifies all subcomponents).
- **Dashboard**: **WORKING** (React 19 + Vite dashboard with 9 pages, responsive layout, dynamic Nginx proxy, live WebSocket alerts, and interactive Simulation Lab).
- **SVM**: **WORKING** (Trained model `SVM_v1_20260907.joblib` and `preprocessing_pipeline.joblib` loaded; 37/37 ML tests pass with zero-leakage guarantee).
- **Simulation**: **WORKING** (End-to-end simulation pipeline: feature synthesis → real SVM inference → risk scoring → response execution → containment).
- **Isolation**: **WORKING** (Independent per-device state tracking in MongoDB; isolated devices halt traffic propagation at boundary; single-device release verified).
- **MongoDB**: **WORKING** (Motor async and PyMongo sync drivers initialized; auto-seeds 10 simulation devices; compound indexes created).
- **Ganache**: **WORKING** (Web3.py client connected to Ganache RPC; real transactions mined with transaction hash, block number, and gas tracking).
- **MQTT**: **WORKING** (Dual-mode client supporting Eclipse Mosquitto broker and in-memory simulated event loop).
- **Docker**: **WORKING** (Multi-container orchestration via `docker-compose.yml`, multi-stage Dockerfiles, persistent volumes, and container networking).
