FROM node:20-alpine AS builder

RUN apk update && \
    apk add --no-cache \
    chromium \
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    git \
    bash

WORKDIR /app
COPY package.json yarn.lock* ./
RUN yarn install --frozen-lockfile
RUN yarn add --platform=linuxmusl --arch=x64 sharp --legacy-peer-deps

FROM node:20-alpine

RUN apk update && \
    apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .

CMD ["yarn", "start"]