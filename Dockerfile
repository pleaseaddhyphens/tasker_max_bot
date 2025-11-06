# Placeholder backend image for future use
FROM node:20-alpine AS base

WORKDIR /app

# Install dependencies only when package files are present
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN if [ -f pnpm-lock.yaml ]; then npm i -g pnpm && pnpm i --frozen-lockfile; \
    elif [ -f yarn.lock ]; then corepack enable && yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; \
    else echo "No lockfile found; skipping install"; fi

# Copy source if present (safe for empty projects)
COPY . .

ENV NODE_ENV=production
EXPOSE 3000

CMD ["node", "server.js"]


