# SecureIoT-X — Docker Setup Guide

## Prerequisites

- **Docker Desktop** installed and running
- No other services on ports: 3000, 7545, 8000, 27017, 1883

## Quick Start

```bash
# 1. Clone/copy the project
cd SecureIoT-X

# 2. Start everything
docker compose up --build
```

Wait for all services to be healthy (first build takes 3-5 minutes).

## Access

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:3000 | React UI (Simulation Lab) |
| Backend API | http://localhost:8000/api/health | FastAPI health check |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI docs |
| MongoDB | localhost:27017 | Connect via `mongosh` |
| Ganache | http://localhost:7545 | Ethereum RPC |
| MQTT | localhost:1883 | MQTT Broker |

## Architecture

```
Browser → localhost:3000 (nginx)
              ├── Static React app
              ├── /api/* → backend:8000
              └── /ws   → backend:8000 (WebSocket)

Backend (FastAPI) → mongodb:27017    (MongoDB)
                  → ganache:8545     (Ganache Ethereum)
                  → mqtt:1883        (MQTT Broker)
```

## Verify Setup

```bash
# Health check (should show MongoDB: CONNECTED, Ganache: CONNECTED)
curl http://localhost:8000/api/health

# List simulation devices (should return 10 devices)
curl http://localhost:8000/api/simulate/devices

# Simulate an attack
curl -X POST http://localhost:8000/api/simulate/attack \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": \"ESP32_003\", \"attack_type\": \"DDoS\"}"
```

## Common Commands

```bash
# Start (background)
docker compose up -d --build

# View logs
docker compose logs -f backend
docker compose logs -f ganache

# Stop
docker compose down

# Stop and remove volumes (reset all data)
docker compose down -v

# Rebuild specific service
docker compose build backend
docker compose up -d backend
```

## Environment Configuration

Docker uses `.env.docker` (automatically loaded by docker-compose.yml).

Key variables:
- `MONGODB_URI=mongodb://mongodb:27017/secureiot_x` (Docker hostname)
- `GANACHE_RPC_URL=http://ganache:8545` (Docker hostname)
- `MQTT_HOST=mqtt` (Docker hostname)

For local development (without Docker), use the existing `.env` file:
- `MONGODB_URI=mongodb://localhost:27017/secureiot_x`
- `GANACHE_RPC_URL=http://127.0.0.1:7545`
- `MQTT_HOST=localhost`

## Local Development (Without Docker)

```bash
# Start MongoDB
net start MongoDB          # Windows
sudo systemctl start mongod  # Linux

# Start Ganache
# Open Ganache app → Start workspace on port 7545

# Start Backend
python -m backend

# Start Dashboard
cd dashboard
npm run dev
```

## Troubleshooting

### MongoDB won't connect
```bash
docker compose logs mongodb
# Ensure port 27017 is not used by local MongoDB
net stop MongoDB    # Windows: stop local MongoDB first
```

### Ganache won't start
```bash
docker compose logs ganache
# Ensure port 7545 is not used by local Ganache
```

### Backend shows "Event loop is closed"
```bash
# Restart backend container
docker compose restart backend
```

### Dashboard shows blank page
```bash
# Rebuild dashboard
docker compose build dashboard
docker compose up -d dashboard
```
