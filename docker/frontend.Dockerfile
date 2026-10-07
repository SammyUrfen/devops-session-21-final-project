# Build context: application/frontend
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY . .
RUN npm run build

# nginx-unprivileged runs as uid 101 and listens on 8080, so the pod needs no root and no low port.
FROM nginxinc/nginx-unprivileged:1.29-alpine
ENV BACKEND_HOST=backend:8000
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
EXPOSE 8080
