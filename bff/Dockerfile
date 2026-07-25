FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:24-alpine
ENV NODE_ENV=production
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist
# Keep the runtime identity numeric so Kubernetes can enforce runAsNonRoot
# without relying on image metadata name resolution.
USER 1000
EXPOSE 3000
CMD ["node", "dist/src/server.js"]
