# 1. Base image
FROM node:18-alpine AS builder

# 2. Set working directory
WORKDIR /app

# 3. Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

# 4. Pass build arguments for Next.js env variables
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID
ARG NEXT_PUBLIC_GOOGLE_CLIENT_SECRET

# 5. Set environment variables inside image
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV NEXT_PUBLIC_GOOGLE_CLIENT_SECRET=$NEXT_PUBLIC_GOOGLE_CLIENT_SECRET

# 6. Copy rest of the source code
COPY . .

# 7. Build the Next.js app
RUN npm run build

# 8. Production image
FROM node:18-alpine AS runner
WORKDIR /app

# Re-declare ARG variables for this stage
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID
ARG NEXT_PUBLIC_GOOGLE_CLIENT_SECRET

# Install only production dependencies
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Copy build output from builder stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Set environment variables for runtime (though not needed for NEXT_PUBLIC_ vars)
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV NEXT_PUBLIC_GOOGLE_CLIENT_SECRET=$NEXT_PUBLIC_GOOGLE_CLIENT_SECRET

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
USER nextjs

# 9. Expose port and run
EXPOSE 3000
CMD ["npm", "start"]
