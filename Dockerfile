# syntax=docker/dockerfile:1
# Optional build of the older editable source; not the recovered publication.
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:stable-alpine AS source-preview
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /app/dist /usr/share/nginx/html
EXPOSE 8080

# Default/Compose preview: recovered published frontend, including lazy modules.
FROM nginx:stable-alpine AS preview
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY recovered-publication/ /usr/share/nginx/html/
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
