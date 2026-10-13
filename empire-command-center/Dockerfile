FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_BACKEND_UPSTREAM=http://backend:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_BACKEND_UPSTREAM=$NEXT_PUBLIC_BACKEND_UPSTREAM \
    NEXT_OUTPUT=standalone \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3005 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 10001 empire && adduser -D -G empire -u 10001 empire

COPY --from=builder /app/public ./public
COPY --from=builder --chown=empire:empire /app/.next/standalone ./
COPY --from=builder --chown=empire:empire /app/.next/static ./.next/static

USER empire
EXPOSE 3005
CMD ["node", "server.js"]
