FROM node:20-slim

LABEL maintainer="NeuroHub <admin@neurohub.com>"
LABEL description="Sleep Apnea Hypoxic Burden analysis — Node.js hb-calculator"

WORKDIR /app
COPY package.json hb-calculator.js entrypoint.mjs ./

RUN npm install --production

VOLUME ["/input", "/output"]

ENTRYPOINT ["node", "/app/entrypoint.mjs"]
