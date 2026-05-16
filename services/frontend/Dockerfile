FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
# Workaround for npm/cli#4828 — see BUG-008 / BUG-010 in docs/BUG_REGISTRY.md.
# A package-lock.json regenerated on Windows only locks the win32 rollup
# binary; npm ci would never resolve the Linux/macOS one and the build fails.
# Dropping the lockfile + node_modules lets npm pick the right platform binary
# (backed by optionalDependencies in package.json) on whichever host builds.
RUN rm -rf node_modules package-lock.json && npm install --no-audit --no-fund

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
