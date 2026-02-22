#!/usr/bin/with-contenv bashio

# Set up database path for persistent storage
export DATABASE_URL="file:/data/food-manager.db"
export NODE_ENV=production
export PORT=3000

# Get Home Assistant token for API access
if bashio::supervisor.ping 2>/dev/null; then
    export HA_BASE_URL="http://supervisor/core"
    export HA_TOKEN="$(bashio::config 'ha_token' '')"
fi

bashio::log.info "Starting Home Food Manager..."

# Run database migrations
cd /app
npx prisma db push --skip-generate 2>/dev/null || true

bashio::log.info "Database ready."
bashio::log.info "Starting web server on port ${PORT}..."

# Start the Next.js server
exec node server.js
