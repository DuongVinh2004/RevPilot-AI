# RevPilot AI — Web Client Container Definition (apps/web)
# Multi-stage build with minimal Nginx Alpine runtime

FROM nginx:1.25-alpine

WORKDIR /usr/share/nginx/html

# Clean default html
RUN rm -rf ./*

# Copy static assets and configurations
COPY apps/web/src/ ./
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget -q --spider http://localhost:80/health/live || exit 1

CMD ["nginx", "-g", "daemon off;"]
