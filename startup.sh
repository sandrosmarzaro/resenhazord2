#!/bin/sh

yarn install
yarn add --platform=linuxmusl --arch=x64 sharp --legacy-peer-deps
yarn start