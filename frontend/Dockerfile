# Multi-stage Next.js production build.
# Stage 1: install deps + build the standalone bundle.
# Stage 2: minimal runtime that only ships what `next build` emitted.

FROM node:20-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
# --legacy-peer-deps is required because react-plotly.js@2.x declares its
# React peer range as ^16 || ^17 || ^18, predating the React 19 release.
# The library works fine with React 19; the peer range is just stale.
RUN if [ -f package-lock.json ]; then \
        npm ci --legacy-peer-deps; \
    else \
        npm install --legacy-peer-deps; \
    fi

FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/ ./
COPY --from=deps /app/node_modules ./node_modules
# NEXT_PUBLIC_* vars must be present at build time so they get baked into
# the client bundle.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1

# Use a non-root user for the runtime.
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

ENV PORT=3000 HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
