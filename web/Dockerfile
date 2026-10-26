# GraphLens web image (development build of the Next.js app).
FROM node:22-alpine

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci --include=dev
COPY . .
RUN npm run build

# Run as a normal user, not root.
USER node
EXPOSE 3000
CMD ["npm", "start"]
