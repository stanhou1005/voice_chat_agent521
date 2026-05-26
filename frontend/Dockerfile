# Stage 1: Build frontend
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve with nginx + SSL
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY ssl /etc/nginx/ssl
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 443

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-check-certificate -qO- https://localhost:443/ || exit 1
