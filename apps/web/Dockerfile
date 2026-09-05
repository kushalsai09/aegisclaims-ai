FROM node:24.4.1-alpine AS build
ARG VITE_AUTH_MODE=local
ENV VITE_AUTH_MODE=$VITE_AUTH_MODE
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
RUN npm ci --workspace @insurance-ops/web
COPY apps/web ./apps/web
RUN npm run build --workspace @insurance-ops/web

FROM nginxinc/nginx-unprivileged:1.29.0-alpine AS runtime
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
