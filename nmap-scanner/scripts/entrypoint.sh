#!/usr/bin/env bash
set -e

CRON_FILE="/etc/cron.d/nmap_scanner"

# Configurar tareas programadas para nmap-scanner únicamente
echo "# Escaneo de puertos y servicios" > $CRON_FILE
echo "$SCAN_SCHEDULE root /usr/local/bin/python /opt/nmap-scanner/src/scan.py >> /var/log/nmap_scanner.log 2>&1" >> $CRON_FILE

# Agregar mapeo topológico si está definido
if [ ! -z "$TOPOLOGY_SCHEDULE" ]; then
    echo "# Mapeo topológico de red" >> $CRON_FILE
    echo "$TOPOLOGY_SCHEDULE root /usr/local/bin/python /opt/nmap-scanner/src/topology_mapper.py >> /var/log/topology.log 2>&1" >> $CRON_FILE
fi

# Configurar permisos y iniciar cron
chmod 0644 $CRON_FILE
crontab $CRON_FILE
service cron start

echo "✅ Cron configurado para nmap-scanner:"
echo "   - Scan: $SCAN_SCHEDULE"
if [ ! -z "$TOPOLOGY_SCHEDULE" ]; then
    echo "   - Topología: $TOPOLOGY_SCHEDULE"
fi

# Crear directorios necesarios
mkdir -p /results/topology_history
mkdir -p /var/log

# Ejecutar scan inicial (opcional)
if [ "$RUN_INITIAL_SCAN" = "true" ]; then
    echo "🔍 Ejecutando scan inicial..."
    /usr/local/bin/python /opt/nmap-scanner/src/scan.py &
    
    if [ ! -z "$TOPOLOGY_SCHEDULE" ]; then
        echo "🗺️  Ejecutando mapeo topológico inicial..."
        /usr/local/bin/python /opt/nmap-scanner/src/topology_mapper.py &
    fi
fi

echo "🚀 Iniciando servidor HTTP en puerto $HTTP_PORT..."

# Servidor HTTP para triggers manuales
# Iniciar servidor HTTP usando el módulo Python separado
exec /usr/local/bin/python /opt/nmap-scanner/src/server.py