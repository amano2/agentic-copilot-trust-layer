FROM node:20-alpine

WORKDIR /app

# Copy package descriptors
COPY package*.json ./

# Install packages
RUN npm install

# Copy frontend source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run dev server with host binding so it's accessible externally
CMD ["npm", "run", "dev", "--", "--host"]
