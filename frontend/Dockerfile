# Build from the frontend/ directory (docker build -f frontend/Dockerfile frontend/).
# NEXT_PUBLIC_* vars are inlined into the JS bundle at build time by Next.js,
# so they must be passed as build args here, not as Cloud Run runtime env vars.
FROM node:20-slim AS builder
WORKDIR /app

ARG NEXT_PUBLIC_API_GATEWAY_URL
ARG NEXT_PUBLIC_FIREBASE_API_KEY
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID
ENV NEXT_PUBLIC_API_GATEWAY_URL=$NEXT_PUBLIC_API_GATEWAY_URL
ENV NEXT_PUBLIC_FIREBASE_API_KEY=$NEXT_PUBLIC_FIREBASE_API_KEY
ENV NEXT_PUBLIC_FIREBASE_PROJECT_ID=$NEXT_PUBLIC_FIREBASE_PROJECT_ID

COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Next.js standalone server reads PORT from the environment -- Cloud Run
# sets PORT=8080 automatically, no explicit --port flag needed.
CMD ["node", "server.js"]
