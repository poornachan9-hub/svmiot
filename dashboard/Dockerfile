


# ============================================================
# SecureIoT-X Dashboard — Multi-stage Docker Image
# ============================================================
# Stage 1: Build React app with Vite
# Stage 2: Serve with nginx (proxies /api to backend)
# ============================================================

# ── Stage 1: Build ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (cached unless package files change)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .

# Set Vite env vars: use relative /api URL (nginx proxies to backend)
ENV VITE_API_BASE=/api

RUN npm run build

# ── Stage 2: Serve ─────────────────────────────────────────────
FROM nginx:alpine

# Copy built React app
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config with API proxy rules
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
