FROM node:20-alpine

RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    git \
    bash

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

WORKDIR /app

COPY package.json yarn.lock* ./

RUN yarn install --frozen-lockfile && \
    yarn add --platform=linuxmusl --arch=x64 sharp --legacy-peer-deps

COPY . .

CMD ["yarn", "start"]