#!/usr/bin/env python3
"""
server.py - Servidor HTTP para nmap-scanner con logging detallado
"""

import os
import json
import glob
import subprocess
import http.server
import socketserver
from datetime import datetime
from urllib.parse import parse_qs
import logging

# Configurar logging detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class NmapScannerHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """Log personalizado con timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"HTTP: {format % args}")
    
    def do_GET(self):
        """Maneja peticiones GET"""
        logging.info(f"🌐 GET request: {self.path} from {self.client_address[0]}")
        
        if self.path == "/":
            self._serve_interface()
        elif self.path == "/health":
            self._handle_health()
        elif self.path == "/status":
            self._handle_status()
        else:
            logging.warning(f"❌ 404 - Path not found: {self.path}")
            self._send_404()
    
    def do_POST(self):
        """Maneja peticiones POST"""
        logging.info(f"📤 POST request: {self.path} from {self.client_address[0]}")
        
        if self.path == "/scan":
            self._handle_scan()
        elif self.path == "/topology":
            self._handle_topology()
        else:
            logging.warning(f"❌ 404 - POST path not found: {self.path}")
            self._send_404()
    
    def do_OPTIONS(self):
        """Maneja peticiones OPTIONS para CORS"""
        logging.info(f"🔄 OPTIONS request: {self.path}")
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _serve_interface(self):
        """Sirve la interfaz web"""
        logging.info("📄 Sirviendo interfaz principal")
        try:
            interface_path = "/opt/nmap-scanner/static/index.html"
            with open(interface_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            logging.info("✅ Interfaz servida correctamente")
            
        except FileNotFoundError:
            logging.error("❌ Archivo index.html no encontrado, sirviendo fallback")
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            
            fallback_html = """
            <!DOCTYPE html>
            <html>
            <head><title>Nmap Scanner</title></head>
            <body>
                <h1>Nmap Scanner API</h1>
                <p>Servidor funcionando correctamente</p>
                <h2>Endpoints:</h2>
                <ul>
                    <li>POST /scan - Iniciar escaneo</li>
                    <li>POST /topology - Mapeo topológico</li>
                    <li>GET /status - Estado del sistema</li>
                    <li>GET /health - Health check</li>
                </ul>
                <h2>Test rápido:</h2>
                <button onclick="fetch('/health').then(r=>r.json()).then(d=>alert(JSON.stringify(d)))">Test Health</button>
            </body>
            </html>
            """
            self.wfile.write(fallback_html.encode())
    
    def _handle_health(self):
        """Health check endpoint"""
        logging.info("💚 Health check solicitado")
        response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": ["nmap-scanner", "topology-mapper"],
            "server": "running"
        }
        self._send_json_response(200, response)
    
    def _handle_status(self):
        """Endpoint de estado del sistema"""
        logging.info("📊 Status check solicitado")
        scan_files = glob.glob("/results/nmap_*.xml")
        topology_file = "/results/topology.json"
        
        response = {
            "last_scan_count": len(scan_files),
            "topology_available": os.path.exists(topology_file),
            "target_network": os.getenv("TARGET_NETWORK"),
            "scan_schedule": os.getenv("SCAN_SCHEDULE"),
            "topology_schedule": os.getenv("TOPOLOGY_SCHEDULE"),
            "server_status": "running"
        }
        
        if scan_files:
            latest_scan = max(scan_files, key=os.path.getctime)
            response["last_scan_file"] = os.path.basename(latest_scan)
            response["last_scan_time"] = datetime.fromtimestamp(
                os.path.getctime(latest_scan)
            ).isoformat()
        
        logging.info(f"📈 Status response: {response}")
        self._send_json_response(200, response)
    
    def _handle_scan(self):
        """Endpoint para iniciar escaneo de puertos"""
        logging.info("🔍 Scan solicitado")
        try:
            # Leer datos JSON si están presentes
            network = None
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    network = data.get('network')
                    logging.info(f"📡 Red especificada en request: {network}")
                except json.JSONDecodeError as e:
                    logging.warning(f"⚠️ Error parsing JSON: {e}")
            
            # Configurar variable de entorno si se especificó red
            if network:
                os.environ["TARGET_NETWORK"] = network
                logging.info(f"🎯 Configurada red objetivo: {network}")
            
            # Ejecutar escaneo
            logging.info("🚀 Iniciando proceso de escaneo...")
            subprocess.Popen([
                "/usr/local/bin/python", 
                "/opt/nmap-scanner/src/scan.py"
            ])
            
            response = {
                "status": "scan_started",
                "network": network or os.getenv("TARGET_NETWORK"),
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Escaneo de puertos iniciado"
            }
            logging.info(f"✅ Scan iniciado: {response}")
            self._send_json_response(202, response)
            
        except Exception as e:
            logging.error(f"❌ Error en scan: {e}")
            self._send_json_response(500, {"error": str(e)})
    
    def _handle_topology(self):
        """Endpoint para iniciar mapeo topológico"""
        logging.info("🗺️ Topology mapping solicitado")
        try:
            # Leer datos JSON si están presentes
            network = None
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    network = data.get('network')
                    logging.info(f"🌐 Red especificada para topología: {network}")
                except json.JSONDecodeError as e:
                    logging.warning(f"⚠️ Error parsing JSON para topología: {e}")
            
            # Configurar variable de entorno si se especificó red
            if network:
                os.environ["TARGET_NETWORK"] = network
                logging.info(f"🎯 Configurada red para topología: {network}")
            
            # Ejecutar mapeo topológico
            logging.info("🚀 Iniciando proceso de mapeo topológico...")
            subprocess.Popen([
                "/usr/local/bin/python",
                "/opt/nmap-scanner/src/topology_mapper.py"
            ])
            
            response = {
                "status": "topology_scan_started",
                "network": network or os.getenv("TARGET_NETWORK"),
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Mapeo topológico iniciado"
            }
            logging.info(f"✅ Topology mapping iniciado: {response}")
            self._send_json_response(202, response)
            
        except Exception as e:
            logging.error(f"❌ Error en topology mapping: {e}")
            self._send_json_response(500, {"error": str(e)})
    
    def _send_json_response(self, status_code, data):
        """Envía respuesta JSON"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        response_json = json.dumps(data, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
        logging.info(f"📤 JSON response sent: {status_code}")
    
    def _send_404(self):
        """Envía respuesta 404"""
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {"error": "Endpoint no encontrado"}
        self.wfile.write(json.dumps(response).encode('utf-8'))

def start_server():
    """Inicia el servidor HTTP"""
    port = int(os.getenv("HTTP_PORT", "8080"))
    
    logging.info("=" * 50)
    logging.info("🚀 INICIANDO NMAP SCANNER HTTP SERVER")
    logging.info("=" * 50)
    logging.info(f"📡 Puerto: {port}")
    logging.info(f"🌐 Red objetivo: {os.getenv('TARGET_NETWORK', 'No configurada')}")
    logging.info("=" * 50)
    
    with socketserver.TCPServer(("", port), NmapScannerHandler) as httpd:
        try:
            logging.info(f"✅ Servidor HTTP activo en puerto {port}")
            logging.info("🔗 Endpoints disponibles:")
            logging.info("   GET  / - Interfaz web")
            logging.info("   POST /scan - Iniciar escaneo")
            logging.info("   POST /topology - Mapeo topológico")
            logging.info("   GET  /status - Estado del sistema")
            logging.info("   GET  /health - Health check")
            logging.info("=" * 50)
            logging.info("⏳ Esperando peticiones...")
            
            httpd.serve_forever()
            
        except KeyboardInterrupt:
            logging.info("\n🛑 Deteniendo servidor HTTP...")
            httpd.shutdown()

if __name__ == "__main__":
    start_server()