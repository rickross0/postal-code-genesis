#!/bin/bash
# Setup script to ensure PostGIS .so files are accessible by PostgreSQL
# Run this after system reboot if /tmp/pg-ext is cleared

PGIS_LIB="/home/blueman007/.pgsql-ext/lib"
PGIS_EXT="/home/blueman007/.pgsql-ext/extension"

# Create /tmp/pg-ext symlink for compatibility
mkdir -p /tmp/pg-ext/lib
if [ ! -f /tmp/pg-ext/lib/postgis-3.so ]; then
    cp "$PGIS_LIB"/postgis-3.so /tmp/pg-ext/lib/ 2>/dev/null
    cp "$PGIS_LIB"/postgis_raster-3.so /tmp/pg-ext/lib/ 2>/dev/null
    cp "$PGIS_LIB"/postgis_topology-3.so /tmp/pg-ext/lib/ 2>/dev/null
    cp "$PGIS_LIB"/postgis_sfcgal-3.so /tmp/pg-ext/lib/ 2>/dev/null
fi

echo "PostGIS .so files ensured in /tmp/pg-ext/lib/"
echo "Run 'PGPASSWORD=postgres123 psql -U postgres -h localhost -d postal_genesis -c \"SELECT PostGIS_Version();\"' to verify."
