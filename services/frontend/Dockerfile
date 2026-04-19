FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
# `npm ci` would be preferred but requires package-lock.json which is not
# generated here yet. Switch back to `npm ci` once a lockfile exists.
RUN npm install --no-audit --no-fund

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
