# syntax=docker/dockerfile:1.9

FROM node:22-alpine AS deps
WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@11.3.0 --activate
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/schemas-ts/package.json ./packages/schemas-ts/
RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile || pnpm install

FROM node:22-alpine AS builder
WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@11.3.0 --activate
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules
COPY . .
WORKDIR /repo/apps/web
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000
RUN addgroup -g 10001 -S app && adduser -S -u 10001 -G app app
COPY --from=builder --chown=app:app /repo/apps/web/.next/standalone ./
COPY --from=builder --chown=app:app /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=app:app /repo/apps/web/public ./apps/web/public
USER app
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
