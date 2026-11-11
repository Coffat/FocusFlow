# ==========================================
# Stage 1: Build Angular 21 SPA
# ==========================================
FROM node:22-alpine AS builder

WORKDIR /app

# Enable pnpm 10
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate

# Copy dependency manifests
COPY package.json pnpm-lock.yaml ./

# Install dependencies strictly from lockfile
RUN pnpm install --frozen-lockfile

# Copy application source code
COPY . .

# Build production application bundle
RUN pnpm run build

# ==========================================
# Stage 2: Serve with lightweight Nginx Alpine
# ==========================================
FROM nginx:1.27-alpine AS runner

# Remove default nginx html
RUN rm -rf /usr/share/nginx/html/*

# Copy built Angular artifacts
COPY --from=builder /app/dist/focusflow-frontend/browser /usr/share/nginx/html

# Copy custom Nginx SPA configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

# Health check for docker-compose
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
