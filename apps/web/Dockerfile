# RevPilot AI — Web Client Multi-Stage Build (apps/web)
# Stage 1: Build static assets with Node & Vite
FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/web/package.json ./
RUN npm install

COPY apps/web/ ./
RUN npx vite build

# Stage 2: Serve compiled assets with minimal Nginx Alpine runtime
FROM nginx:1.25-alpine

WORKDIR /usr/share/nginx/html

RUN rm -rf ./*
COPY --from=builder /app/dist/ ./
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget -q --spider http://localhost:80/health/live || exit 1

CMD ["nginx", "-g", "daemon off;"]
