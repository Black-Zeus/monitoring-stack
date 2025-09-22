#!/usr/bin/env python3
"""
server.py - Servidor HTTP para nmap-scanner
Proporciona endpoints REST para controlar escaneos
"""

import os
import json
import glob
import subprocess
import http.server
import socketserver
from datetime import datetime
from urllib.parse import parse_qs

class NmapScannerHandler(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Maneja peticiones GET"""
        if self.path == "/":
            self._serve_interface()
        elif self.path == "/health":
            self._handle_health()
        elif self.path == "/status":
            self._handle_status()
        else:
            self._send_404()
    
    def do_POST(self):
        """Maneja peticiones POST"""
        if self.path == "/scan":
            self._handle_scan()
        elif self.path == "/topology":
            self._handle_topology()
        else:
            self._send_404()
    
    def _serve_interface(self):
        """Sirve la interfaz web"""
        try:
            interface_path = "/opt/nmap-scanner/static/index.html"
            with open(interface_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            
        except FileNotFoundError:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            
            fallback_html = """
            <!DOCTYPE html>
            <html>
            <head><title>Nmap Scanner</title></head>
            <body>
                <h1>Nmap Scanner API</h1>
                <p>Interfaz web no encontrada. Endpoints disponibles:</p>
                <ul>
                    <li>POST /scan - Iniciar escaneo de puertos</li>
                    <li>POST /topology - Iniciar mapeo topológico</li>
                    <li>GET /status - Ver estado del sistema</li>
                    <li>GET /health - Health check</li>
                </ul>
            </body>
            </html>
            """
            self.wfile.write(fallback_html.encode())
    
    def _handle_health(self):
        """Health check endpoint"""
        response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": ["nmap-scanner", "topology-mapper"]
        }
        self._send_json_response(200, response)
    
    def _handle_status(self):
        """Endpoint de estado del sistema"""
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
        
        self._send_json_response(200, response)
    
    def _handle_scan(self):
        """Endpoint para iniciar escaneo de puertos"""
        try:
            # Leer datos JSON si están presentes
            network = None
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    network = data.get('network')
                except json.JSONDecodeError:
                    pass
            
            # Configurar variable de entorno si se especificó red
            if network:
                os.environ["TARGET_NETWORK"] = network
                self.log_message(f"Escaneando red personalizada: {network}")
            
            # Ejecutar escaneo
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
            self._send_json_response(202, response)
            
        except Exception as e:
            self._send_json_response(500, {"error": str(e)})
    
    def _handle_topology(self):
        """Endpoint para iniciar mapeo topológico"""
        try:
            # Leer datos JSON si están presentes
            network = None
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    network = data.get('network')
                except json.JSONDecodeError:
                    pass
            
            # Configurar variable de entorno si se especificó red
            if network:
                os.environ["TARGET_NETWORK"] = network
                self.log_message(f"Mapeando topología de red: {network}")
            
            # Ejecutar mapeo topológico
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
            self._send_json_response(202, response)
            
        except Exception as e:
            self._send_json_response(500, {"error": str(e)})
    
    def _send_json_response(self, status_code, data):
        """Envía respuesta JSON"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def _send_404(self):
        """Envía respuesta 404"""
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {"error": "Endpoint no encontrado"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Log personalizado con timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")

def start_server():
    """Inicia el servidor HTTP"""
    port = int(os.getenv("HTTP_PORT", "8080"))
    
    print(f"Iniciando servidor HTTP en puerto {port}...")
    
    with socketserver.TCPServer(("", port), NmapScannerHandler) as httpd:
        try:
            print(f"Servidor disponible en http://localhost:{port}")
            print("Endpoints disponibles:")
            print("  GET  / - Interfaz web")
            print("  POST /scan - Iniciar escaneo")
            print("  POST /topology - Mapeo topológico")
            print("  GET  /status - Estado del sistema")
            print("  GET  /health - Health check")
            
            httpd.serve_forever()
            
        except KeyboardInterrupt:
            print("\nDeteniendo servidor HTTP...")
            httpd.shutdown()

if __name__ == "__main__":
    start_server()