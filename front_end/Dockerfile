FROM node:22-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY public ./public
COPY src ./src

# Baked into the bundle at build time. It is a URL, not a secret: the
# browser never holds an API key.
ARG REACT_APP_API_URL=http://localhost:7241
ENV REACT_APP_API_URL=$REACT_APP_API_URL
RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/build /usr/share/nginx/html

# nginx:alpine ships an unprivileged "nginx" user; the stock config wants
# root only for the pid file and cache, so both are moved into /tmp.
RUN sed -i 's#/var/run/nginx.pid#/tmp/nginx.pid#' /etc/nginx/nginx.conf \
    && sed -i '/user  nginx;/d' /etc/nginx/nginx.conf \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx
USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/ > /dev/null

CMD ["nginx", "-g", "daemon off;"]
