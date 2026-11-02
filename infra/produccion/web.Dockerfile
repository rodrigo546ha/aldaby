# Imagen de la web (ADR-0040). Contexto: la raíz del repositorio. En el servidor Caddy envía /api a
# la API; la reescritura de next.config.mjs queda para lo que no pase por Caddy.
FROM node:24-bookworm-slim AS build
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web ./
# Las reescrituras de Next se fijan al construir
ENV API_URL=http://api:8000 NEXT_TELEMETRY_DISABLED=1
RUN npm run build && npm prune --omit=dev

FROM node:24-bookworm-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/package.json /app/next.config.mjs ./
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
USER node
EXPOSE 3000
CMD ["node_modules/.bin/next", "start"]
