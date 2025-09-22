#!/usr/bin/env python3
"""
server.py - Servidor HTTP para nmap-scanner con endpoints avanzados
Incluye gestión de configuración, escaneos en 2 fases e historial
"""

import os
import json
import glob
import subprocess
import http.server
import socketserver
from datetime import datetime
from urllib.parse import parse_qs, urlparse
import logging
import traceback
from config_manager import get_config_manager

# Configurar logging detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class NmapScannerHandler(http.server.BaseHTTPRequestHandler):
    
    def __init__(self, *args, **kwargs):
        self.config_manager = get_config_manager()
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Log personalizado con timestamp"""
        logging.info(f"HTTP: {format % args}")
    
    def do_GET(self):
        """Maneja peticiones GET"""
        logging.info(f"🌐 GET request: {self.path} from {self.client_address[0]}")
        
        try:
            if self.path == "/":
                self._serve_interface()
            elif self.path == "/health":
                self._handle_health()
            elif self.path == "/status":
                self._handle_status()
            elif self.path == "/config":
                self._handle_get_config()
            elif self.path == "/scan-history":
                self._handle_scan_history()
            elif self.path.startswith("/static/"):
                self._serve_static_file()
            else:
                logging.warning(f"❌ 404 - Path not found: {self.path}")
                self._send_404()
                
        except Exception as e:
            logging.error(f"Error en GET {self.path}: {e}")
            logging.error(traceback.format_exc())
            self._send_500(str(e))
    
    def do_POST(self):
        """Maneja peticiones POST"""
        logging.info(f"📤 POST request: {self.path} from {self.client_address[0]}")
        
        try:
            if self.path == "/scan":
                self._handle_scan()
            elif self.path == "/topology":
                self._handle_topology()
            elif self.path == "/advanced-scan":
                self._handle_advanced_scan()
            elif self.path == "/add-network":
                self._handle_add_network()
            elif self.path == "/remove-network":
                self._handle_remove_network()
            elif self.path == "/enable-network":
                self._handle_enable_network()
            elif self.path == "/update-config":
                self._handle_update_config()
            else:
                logging.warning(f"❌ 404 - POST path not found: {self.path}")
                self._send_404()
                
        except Exception as e:
            logging.error(f"Error en POST {self.path}: {e}")
            logging.error(traceback.format_exc())
            self._send_500(str(e))
    
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
            self._serve_fallback_interface()
    
    def _serve_fallback_interface(self):
        """Interfaz de fallback con todos los endpoints"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        
        fallback_html = """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Advanced Nmap Scanner API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
                h2 { color: #34495e; margin-top: 30px; }
                .endpoint { background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #3498db; }
                .method { font-weight: bold; color: #e74c3c; }
                button { background: #3498db; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; margin: 5px; }
                button:hover { background: #2980b9; }
                .result { margin: 10px 0; padding: 10px; background: #d5dbdb; border-radius: 4px; font-family: monospace; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 Advanced Nmap Scanner API</h1>
                <p><strong>Estado:</strong> Servidor funcionando correctamente</p>
                
                <h2>📊 Endpoints de Estado</h2>
                <div class="endpoint">
                    <span class="method">GET</span> /health - Health check
                    <button onclick="testEndpoint('/health')">Test</button>
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> /status - Estado del sistema
                    <button onclick="testEndpoint('/status')">Test</button>
                </div>
                
                <h2>⚙️ Gestión de Configuración</h2>
                <div class="endpoint">
                    <span class="method">GET</span> /config - Ver configuración actual
                    <button onclick="testEndpoint('/config')">Ver Config</button>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> /add-network - Agregar nueva red<br>
                    <small>Body: {"name": "red1", "cidr": "192.168.1.0/24", "description": "Red doméstica"}</small>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> /remove-network - Eliminar red<br>
                    <small>Body: {"name": "red1"}</small>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> /enable-network - Habilitar/deshabilitar red<br>
                    <small>Body: {"name": "red1", "enabled": true}</small>
                </div>
                
                <h2>🔍 Escaneos</h2>
                <div class="endpoint">
                    <span class="method">POST</span> /scan - Escaneo básico (original)
                    <button onclick="testBasicScan()">Test Básico</button>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> /advanced-scan - Escaneo avanzado en 2 fases<br>
                    <small>Body: {"network_name": "red1"} o {"network_cidr": "192.168.1.0/24"}</small>
                    <button onclick="testAdvancedScan()">Test Avanzado</button>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> /topology - Mapeo topológico
                    <button onclick="testTopology()">Test Topology</button>
                </div>
                
                <h2>📚 Historial</h2>
                <div class="endpoint">
                    <span class="method">GET</span> /scan-history - Ver historial de escaneos
                    <button onclick="testEndpoint('/scan-history')">Ver Historial</button>
                </div>
                
                <div id="result" class="result" style="display:none;"></div>
                
                <script>
                    function testEndpoint(endpoint) {
                        fetch(endpoint)
                            .then(r => r.json())
                            .then(data => {
                                document.getElementById('result').style.display = 'block';
                                document.getElementById('result').innerHTML = '<strong>' + endpoint + '</strong><br>' + JSON.stringify(data, null, 2);
                            })
                            .catch(e => {
                                document.getElementById('result').style.display = 'block';
                                document.getElementById('result').innerHTML = '<strong>Error:</strong> ' + e.message;
                            });
                    }
                    
                    function testBasicScan() {
                        fetch('/scan', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({network: '192.168.1.0/24'})
                        })
                        .then(r => r.json())
                        .then(data => {
                            document.getElementById('result').style.display = 'block';
                            document.getElementById('result').innerHTML = '<strong>Basic Scan:</strong><br>' + JSON.stringify(data, null, 2);
                        });
                    }
                    
                    function testAdvancedScan() {
                        fetch('/advanced-scan', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({network_cidr: '192.168.1.0/24'})
                        })
                        .then(r => r.json())
                        .then(data => {
                            document.getElementById('result').style.display = 'block';
                            document.getElementById('result').innerHTML = '<strong>Advanced Scan:</strong><br>' + JSON.stringify(data, null, 2);
                        });
                    }
                    
                    function testTopology() {
                        fetch('/topology', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({network: '192.168.1.0/24'})
                        })
                        .then(r => r.json())
                        .then(data => {
                            document.getElementById('result').style.display = 'block';
                            document.getElementById('result').innerHTML = '<strong>Topology:</strong><br>' + JSON.stringify(data, null, 2);
                        });
                    }
                </script>
            </div>
        </body>
        </html>
        """
        self.wfile.write(fallback_html.encode('utf-8'))
    
    def _serve_static_file(self):
        """Sirve archivos estáticos"""
        try:
            # Remover /static/ del path
            file_path = self.path[8:]  # Remover "/static/"
            full_path = f"/opt/nmap-scanner/static/{file_path}"
            
            with open(full_path, 'rb') as f:
                content = f.read()
            
            # Determinar content type
            if file_path.endswith('.css'):
                content_type = 'text/css'
            elif file_path.endswith('.js'):
                content_type = 'application/javascript'
            elif file_path.endswith('.html'):
                content_type = 'text/html'
            else:
                content_type = 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(content)
            
        except FileNotFoundError:
            self._send_404()
    
    def _handle_health(self):
        """Health check endpoint"""
        logging.info("💚 Health check solicitado")
        response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": ["nmap-scanner", "topology-mapper", "advanced-scanner"],
            "server": "running",
            "config_loaded": len(self.config_manager.get_networks()) > 0
        }
        self._send_json_response(200, response)
    
    def _handle_status(self):
        """Endpoint de estado del sistema"""
        logging.info("📊 Status check solicitado")
        
        # Archivos de escaneo
        scan_files = glob.glob("/results/nmap_*.xml")
        advanced_scan_files = glob.glob("/results/advanced_scan_*.json")
        topology_file = "/results/topology.json"
        history_file = "/results/scan_history.json"
        
        # Configuración actual
        config_summary = self.config_manager.get_config_summary()
        
        response = {
            "last_scan_count": len(scan_files),
            "advanced_scan_count": len(advanced_scan_files),
            "topology_available": os.path.exists(topology_file),
            "history_available": os.path.exists(history_file),
            "target_network": os.getenv("TARGET_NETWORK"),
            "scan_schedule": os.getenv("SCAN_SCHEDULE"),
            "topology_schedule": os.getenv("TOPOLOGY_SCHEDULE"),
            "server_status": "running",
            "configuration": config_summary
        }
        
        # Información del último escaneo básico
        if scan_files:
            latest_scan = max(scan_files, key=os.path.getctime)
            response["last_scan_file"] = os.path.basename(latest_scan)
            response["last_scan_time"] = datetime.fromtimestamp(
                os.path.getctime(latest_scan)
            ).isoformat() + "Z"
        
        # Información del último escaneo avanzado
        if advanced_scan_files:
            latest_advanced = max(advanced_scan_files, key=os.path.getctime)
            response["last_advanced_scan_file"] = os.path.basename(latest_advanced)
            response["last_advanced_scan_time"] = datetime.fromtimestamp(
                os.path.getctime(latest_advanced)
            ).isoformat() + "Z"
        
        logging.info(f"📈 Status response: {response}")
        self._send_json_response(200, response)
    
    def _handle_get_config(self):
        """Endpoint para obtener configuración actual"""
        logging.info("⚙️ Configuración solicitada")
        
        try:
            config_summary = self.config_manager.get_config_summary()
            networks = self.config_manager.get_networks()
            scan_limits = self.config_manager.get_scan_limits()
            scan_options = self.config_manager.get_scan_options()
            
            response = {
                "summary": config_summary,
                "networks": networks,
                "scan_limits": scan_limits,
                "scan_options": scan_options,
                "influxdb": {
                    "enabled": self.config_manager.get_influxdb_config().get("enabled", False),
                    "url": self.config_manager.get_influxdb_config().get("url", "")
                }
            }
            
            self._send_json_response(200, response)
            
        except Exception as e:
            logging.error(f"Error obteniendo configuración: {e}")
            self._send_json_response(500, {"error": str(e)})
    
    def _handle_scan_history(self):
        """Endpoint para obtener historial de escaneos"""
        logging.info("📚 Historial de escaneos solicitado")
        
        try:
            history_file = "/results/scan_history.json"
            
            if not os.path.exists(history_file):
                response = {
                    "history": [],
                    "total_scans": 0,
                    "message": "No hay historial de escaneos avanzados disponible"
                }
            else:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                
                response = {
                    "history": history,
                    "total_scans": len(history),
                    "latest_scan": history[-1] if history else None
                }
            
            self._send_json_response(200, response)
            
        except Exception as e:
            logging.error(f"Error obteniendo historial: {e}")
            self._send_json_response(500, {"error": str(e)})
    
    def _handle_scan(self):
        """Endpoint para iniciar escaneo de puertos (original)"""
        logging.info("🔍 Scan básico solicitado")
        try:
            data = self._read_json_body()
            network = data.get('network') if data else None
            
            if network:
                os.environ["TARGET_NETWORK"] = network
                logging.info(f"🎯 Configurada red objetivo: {network}")
            
            logging.info("🚀 Iniciando proceso de escaneo básico...")
            subprocess.Popen([
                "/usr/local/bin/python", 
                "/opt/nmap-scanner/src/scan.py"
            ])
            
            response = {
                "status": "scan_started",
                "type": "basic_scan",
                "network": network or os.getenv("TARGET_NETWORK"),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": "Escaneo básico de puertos iniciado"
            }
            logging.info(f"✅ Scan básico iniciado: {response}")
            self._send_json_response(202, response)
            
        except Exception as e:
            logging.error(f"❌ Error en scan básico: {e}")
            self._send_json_response(500, {"error": str(e)})
    
    def _handle_topology(self):
        """Endpoint para iniciar mapeo topológico"""
        logging.info("🗺️ Topology mapping solicitado")
        try:
            data = self._read_json_body()
            network = data.get('network') if data else None
            
            if network:
                os.environ["TARGET_NETWORK"] = network
                logging.info(f"🌐 Red configurada para topología: {network}")
            
            logging.info("🚀 Iniciando proceso de mapeo topológico...")
            subprocess.Popen([
                "/usr/local/bin/python",
                "/opt/nmap-scanner/src/topology_mapper.py"
            ])
            
            response = {
                "status": "topology_scan_started",
                "network": network or os.getenv("TARGET_NETWORK"),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": "Mapeo topológico iniciado"
            }
            logging.info(f"✅ Topology mapping iniciado: {response}")
            self._send_json_response(202, response)
            
        except Exception as e:
            logging.error(f"❌ Error en topology mapping: {e}")
            self._send_json_response(500, {"error": str(e)})
    
    def _handle_advanced_scan(self):
        """Endpoint para escaneo avanzado en 2 fases"""
        logging.info("🎯 Advanced scan solicitado")
        try:
            data = self._read_json_body()
            
            if not data:
                raise ValueError("Body JSON requerido")
            
            network_name = data.get('network_name')
            network_cidr = data.get('network_cidr')
            
            if not network_name and not network_cidr:
                raise ValueError("Debe especificar 'network_name' o 'network_cidr'")
            
            # Validar red si se especifica por nombre
            if network_name:
                network_config = self.config_manager.get_network(network_name)
                if not network_config:
                    raise ValueError(f"Red '{network_name}' no encontrada en configuración")
                if not network_config.get("enabled", True):
                    raise ValueError(f"Red '{network_name}' está deshabilitada")
                network_cidr = network_config["cidr"]
            
            # Validar CIDR si se especifica directamente
            if network_cidr and not self.config_manager.validate_network_cidr(network_cidr):
                raise ValueError(f"CIDR inválido: {network_cidr}")
            
            logging.info(f"🚀 Iniciando escaneo avanzado...")
            logging.info(f"   Red: {network_name or 'manual'}")
            logging.info(f"   CIDR: {network_cidr}")
            
            # Preparar argumentos para el script
            cmd = ["/usr/local/bin/python", "/opt/nmap-scanner/src/advanced_scan.py"]
            if network_name:
                cmd.extend(["--network", network_name])
            else:
                cmd.extend(["--cidr", network_cidr])
            
            subprocess.Popen(cmd)
            
            response = {
                "status": "advanced_scan_started",
                "type": "advanced_scan_2_phases",
                "network_name": network_name,
                "network_cidr": network_cidr,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": "Escaneo avanzado iniciado (Fase 1: Descubrimiento rápido, Fase 2: Detalle)",
                "phases": ["discovery", "detailed_scan"],
                "estimated_duration": "5-30 minutos dependiendo del tamaño de la red"
            }
            logging.info(f"✅ Advanced scan iniciado: {response}")
            self._send_json_response(202, response)
            
        except Exception as e:
            logging.error(f"❌ Error en advanced scan: {e}")
            self._send_json_response(400, {"error": str(e)})
    
    def _handle_add_network(self):
        """Endpoint para agregar nueva red"""
        logging.info("➕ Agregar red solicitado")
        try:
            data = self._read_json_body()
            
            if not data:
                raise ValueError("Body JSON requerido")
            
            name = data.get('name')
            cidr = data.get('cidr')
            description = data.get('description', '')
            
            if not name or not cidr:
                raise ValueError("Campos 'name' y 'cidr' son requeridos")
            
            success = self.config_manager.add_network(name, cidr, description)
            
            if success:
                response = {
                    "status": "success",
                    "message": f"Red '{name}' agregada exitosamente",
                    "network": {
                        "name": name,
                        "cidr": cidr,
                        "description": description
                    }
                }
                self._send_json_response(201, response)
            else:
                raise ValueError("Error agregando red (posiblemente CIDR inválido)")
                
        except Exception as e:
            logging.error(f"❌ Error agregando red: {e}")
            self._send_json_response(400, {"error": str(e)})
    
    def _handle_remove_network(self):
        """Endpoint para eliminar red"""
        logging.info("➖ Eliminar red solicitado")
        try:
            data = self._read_json_body()
            
            if not data:
                raise ValueError("Body JSON requerido")
            
            name = data.get('name')
            if not name:
                raise ValueError("Campo 'name' es requerido")
            
            success = self.config_manager.remove_network(name)
            
            if success:
                response = {
                    "status": "success",
                    "message": f"Red '{name}' eliminada exitosamente"
                }
                self._send_json_response(200, response)
            else:
                raise ValueError(f"Red '{name}' no encontrada")
                
        except Exception as e:
            logging.error(f"❌ Error eliminando red: {e}")
            self._send_json_response(400, {"error": str(e)})
    
    def _handle_enable_network(self):
        """Endpoint para habilitar/deshabilitar red"""
        logging.info("🔧 Cambiar estado de red solicitado")
        try:
            data = self._read_json_body()
            
            if not data:
                raise ValueError("Body JSON requerido")
            
            name = data.get('name')
            enabled = data.get('enabled', True)
            
            if not name:
                raise ValueError("Campo 'name' es requerido")
            
            success = self.config_manager.enable_network(name, enabled)
            
            if success:
                status = "habilitada" if enabled else "deshabilitada"
                response = {
                    "status": "success",
                    "message": f"Red '{name}' {status} exitosamente",
                    "network_enabled": enabled
                }
                self._send_json_response(200, response)
            else:
                raise ValueError(f"Red '{name}' no encontrada")
                
        except Exception as e:
            logging.error(f"❌ Error cambiando estado de red: {e}")
            self._send_json_response(400, {"error": str(e)})
    
    def _handle_update_config(self):
        """Endpoint para actualizar sección de configuración"""
        logging.info("🔧 Actualizar configuración solicitado")
        try:
            data = self._read_json_body()
            
            if not data:
                raise ValueError("Body JSON requerido")
            
            section = data.get('section')
            config_data = data.get('data')
            
            if not section or not config_data:
                raise ValueError("Campos 'section' y 'data' son requeridos")
            
            success = self.config_manager.update_config_section(section, config_data)
            
            if success:
                response = {
                    "status": "success",
                    "message": f"Sección '{section}' actualizada exitosamente"
                }
                self._send_json_response(200, response)
            else:
                raise ValueError(f"Sección '{section}' no encontrada")
                
        except Exception as e:
            logging.error(f"❌ Error actualizando configuración: {e}")
            self._send_json_response(400, {"error": str(e)})
    
    def _read_json_body(self):
        """Lee y parsea body JSON de la petición"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                return json.loads(post_data.decode('utf-8'))
            return None
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido: {e}")
        except Exception as e:
            raise ValueError(f"Error leyendo body: {e}")
    
    def _send_json_response(self, status_code, data):
        """Envía respuesta JSON"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        response_json = json.dumps(data, indent=2, ensure_ascii=False)
        self.wfile.write(response_json.encode('utf-8'))
        logging.info(f"📤 JSON response sent: {status_code}")
    
    def _send_404(self):
        """Envía respuesta 404"""
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {"error": "Endpoint no encontrado"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def _send_500(self, error_message):
        """Envía respuesta 500"""
        self.send_response(500)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {"error": f"Error interno del servidor: {error_message}"}
        self.wfile.write(json.dumps(response).encode('utf-8'))


def start_server():
    """Inicia el servidor HTTP"""
    port = int(os.getenv("HTTP_PORT", "8080"))
    
    logging.info("=" * 60)
    logging.info("🚀 ADVANCED NMAP SCANNER HTTP SERVER")
    logging.info("=" * 60)
    logging.info(f"📡 Puerto: {port}")
    logging.info(f"🌐 Red objetivo: {os.getenv('TARGET_NETWORK', 'Configuración dinámica')}")
    
    # Inicializar gestor de configuración
    config_manager = get_config_manager()
    config_summary = config_manager.get_config_summary()
    logging.info(f"📋 Redes configuradas: {config_summary['total_networks']}")
    logging.info(f"📋 Redes habilitadas: {config_summary['enabled_networks']}")
    
    logging.info("=" * 60)
    
    with socketserver.TCPServer(("", port), NmapScannerHandler) as httpd:
        try:
            logging.info(f"✅ Servidor HTTP activo en puerto {port}")
            logging.info("🔗 Endpoints disponibles:")
            logging.info("   📊 ESTADO:")
            logging.info("     GET  / - Interfaz web")
            logging.info("     GET  /health - Health check")
            logging.info("     GET  /status - Estado del sistema")
            logging.info("   ⚙️  CONFIGURACIÓN:")
            logging.info("     GET  /config - Ver configuración")
            logging.info("     POST /add-network - Agregar red")
            logging.info("     POST /remove-network - Eliminar red")
            logging.info("     POST /enable-network - Habilitar/deshabilitar red")
            logging.info("   🔍 ESCANEOS:")
            logging.info("     POST /scan - Escaneo básico (original)")
            logging.info("     POST /advanced-scan - Escaneo avanzado 2 fases")
            logging.info("     POST /topology - Mapeo topológico")
            logging.info("   📚 HISTORIAL:")
            logging.info("     GET  /scan-history - Ver historial")
            logging.info("=" * 60)
            logging.info("⏳ Esperando peticiones...")
            
            httpd.serve_forever()
            
        except KeyboardInterrupt:
            logging.info("\n🛑 Deteniendo servidor HTTP...")
            httpd.shutdown()


if __name__ == "__main__":
    start_server()