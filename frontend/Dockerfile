FROM node:22-slim AS builder

WORKDIR /app

ARG NUXT_API_BASE=http://backend:8000
ENV NUXT_API_BASE=${NUXT_API_BASE}

COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:22-slim

WORKDIR /app

COPY --from=builder /app/.output .output

ENV HOST=0.0.0.0
ENV PORT=3000

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
