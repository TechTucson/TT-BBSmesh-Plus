FROM node:22-alpine AS maplibre
WORKDIR /build
RUN npm init -y >/dev/null 2>&1 \
    && npm install --no-save maplibre-gl@5.12.0

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY --from=maplibre /build/node_modules/maplibre-gl/dist/maplibre-gl.js /usr/share/nginx/html/vendor/maplibre-gl.js
COPY --from=maplibre /build/node_modules/maplibre-gl/dist/maplibre-gl.css /usr/share/nginx/html/vendor/maplibre-gl.css

EXPOSE 80
