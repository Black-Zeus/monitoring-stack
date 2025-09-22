#!/usr/bin/env bash
set -e

CRON_FILE="/etc/cron.d/nmap_scanner"

# Configurar tareas programadas
echo "# Escaneo de puertos y servicios" > $CRON_FILE
echo "$SCAN_SCHEDULE root /usr/local/bin/python /opt/nmap-scanner/scan.py >> /var/log/nmap_scanner.log 2>&1" >> $CRON_FILE

# Agregar mapeo topológico si está definido
if [ ! -z "$TOPOLOGY_SCHEDULE" ]; then
    echo "# Mapeo topológico de red" >> $CRON_FILE
    echo "$TOPOLOGY_SCHEDULE root /usr/local/bin/python /opt/nmap-scanner/topology_mapper.py >> /var/log/topology.log 2>&1" >> $CRON_FILE
fi

# Configurar permisos y iniciar cron
chmod 0644 $CRON_FILE
crontab $CRON_FILE
service cron start

echo "✅ Cron configurado:"
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
    /usr/local/bin/python /opt/nmap-scanner/scan.py &
    
    if [ ! -z "$TOPOLOGY_SCHEDULE" ]; then
        echo "🗺️  Ejecutando mapeo topológico inicial..."
        /usr/local/bin/python /opt/nmap-scanner/topology_mapper.py &
    fi
fi

echo "🚀 Iniciando servidor HTTP en puerto $HTTP_PORT..."

# Servidor HTTP mejorado para triggers manuales
python3 - <<'PY'
import os, subprocess, http.server, socketserver, json, threading
from datetime import datetime

PORT = int(os.getenv("HTTP_PORT", "8080"))

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/scan":
            try:
                subprocess.Popen([
                    "/usr/local/bin/python", 
                    "/opt/nmap-scanner/scan.py"
                ])
                self.send_response(202)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {
                    "status": "scan_started",
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": "Port scan iniciado"
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                
        elif self.path == "/topology":
            try:
                subprocess.Popen([
                    "/usr/local/bin/python",
                    "/opt/nmap-scanner/topology_mapper.py"
                ])
                self.send_response(202)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {
                    "status": "topology_scan_started", 
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": "Mapeo topológico iniciado"
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "services": ["nmap-scanner", "topology-mapper"]
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == "/status":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            # Verificar archivos de resultados
            import glob
            scan_files = glob.glob("/results/nmap_*.xml")
            topology_file = "/results/topology.json"
            
            response = {
                "last_scan_count": len(scan_files),
                "topology_available": os.path.exists(topology_file),
                "target_network": os.getenv("TARGET_NETWORK"),
                "scan_schedule": os.getenv("SCAN_SCHEDULE"),
                "topology_schedule": os.getenv("TOPOLOGY_SCHEDULE")
            }
            
            if scan_files:
                latest_scan = max(scan_files, key=os.path.getctime)
                response["last_scan_file"] = os.path.basename(latest_scan)
                response["last_scan_time"] = datetime.fromtimestamp(
                    os.path.getctime(latest_scan)
                ).isoformat()
            
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Log personalizado
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")

print(f"🌐 Servidor HTTP iniciado en puerto {PORT}")
print("📋 Endpoints disponibles:")
print("   POST /scan      - Ejecutar escaneo manual")
print("   POST /topology  - Ejecutar mapeo topológico")
print("   GET  /health    - Estado del servicio") 
print("   GET  /status    - Información detallada")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor HTTP...")
        httpd.shutdown()
PY