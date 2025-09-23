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
        """Endpoint de estado del sistema mejorado con progreso de escaneos"""
        logging.info("📊 Status check solicitado")
        
        # Archivos de escaneo
        scan_files = glob.glob("/results/nmap_*.xml")
        advanced_scan_files = glob.glob("/results/advanced_scan_*.json")
        topology_file = "/results/topology.json"
        history_file = "/results/scan_history.json"
        
        # Configuración actual
        config_summary = self.config_manager.get_config_summary()
        
        # Verificar procesos activos
        active_scans = self._check_active_scans()
        system_resources = self._get_system_resources()
        recent_activity = self._get_recent_activity()
        
        # Agregar diagnósticos cuando no hay actividad
        diagnostics = None
        if not active_scans and len(scan_files) == 0:
            diagnostics = self._get_scan_diagnostics()
        
        response = {
            # Información básica (mantener compatibilidad)
            "last_scan_count": len(scan_files),
            "advanced_scan_count": len(advanced_scan_files),
            "topology_available": os.path.exists(topology_file),
            "history_available": os.path.exists(history_file),
            "target_network": os.getenv("TARGET_NETWORK"),
            "scan_schedule": os.getenv("SCAN_SCHEDULE"),
            "topology_schedule": os.getenv("TOPOLOGY_SCHEDULE"),
            "server_status": "running",
            "configuration": config_summary,
            
            # Información mejorada de progreso
            "active_scans": active_scans,
            "system_status": {
                "cpu_usage": system_resources.get("cpu_percent"),
                "memory_usage": system_resources.get("memory_percent"),
                "disk_usage": system_resources.get("disk_percent"),
                "uptime_seconds": system_resources.get("uptime"),
                "uptime_human": system_resources.get("uptime_human"),
                "load_average": system_resources.get("load_average")
            },
            "recent_activity": recent_activity,
            "scan_queue": self._get_scan_queue_status(),
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
        
        # Agregar diagnósticos si están disponibles
        if diagnostics:
            response["diagnostics"] = diagnostics
        
        # Información del último escaneo básico
        if scan_files:
            latest_scan = max(scan_files, key=os.path.getctime)
            scan_stat = os.stat(latest_scan)
            response["last_scan_file"] = os.path.basename(latest_scan)
            response["last_scan_time"] = datetime.fromtimestamp(scan_stat.st_ctime).isoformat() + "Z"
            response["last_scan_size"] = scan_stat.st_size
            
            # Analizar contenido del último escaneo
            scan_analysis = self._analyze_scan_file(latest_scan)
            response["last_scan_results"] = scan_analysis
        
        # Información del último escaneo avanzado
        if advanced_scan_files:
            latest_advanced = max(advanced_scan_files, key=os.path.getctime)
            adv_stat = os.stat(latest_advanced)
            response["last_advanced_scan_file"] = os.path.basename(latest_advanced)
            response["last_advanced_scan_time"] = datetime.fromtimestamp(adv_stat.st_ctime).isoformat() + "Z"
            response["last_advanced_scan_size"] = adv_stat.st_size
        
        logging.info(f"📈 Enhanced status response generated")
        self._send_json_response(200, response)

    def _check_active_scans(self):
        """Verifica procesos de escaneo activos con mejor detección"""
        active_scans = []
        
        try:
            # Verificar procesos nmap con más detalle
            try:
                nmap_procs = subprocess.run(['pgrep', '-f', 'nmap'], capture_output=True, text=True, timeout=5)
                nmap_pids = [pid.strip() for pid in nmap_procs.stdout.strip().split('\n') 
                            if pid.strip() and pid.strip().isdigit()] if nmap_procs.returncode == 0 else []
                
                for pid in nmap_pids:
                    try:
                        # Información detallada del proceso
                        proc_info = subprocess.run(['ps', '-p', pid, '-o', 'pid,ppid,cmd,etime,pcpu,pmem'], 
                                                 capture_output=True, text=True, timeout=5)
                        if proc_info.returncode == 0:
                            lines = proc_info.stdout.strip().split('\n')
                            if len(lines) > 1:
                                # Parse process information
                                proc_data = lines[1].split(None, 5)
                                if len(proc_data) >= 6:
                                    active_scans.append({
                                        "type": "nmap_process",
                                        "pid": pid,
                                        "parent_pid": proc_data[1],
                                        "command": (proc_data[5][:120] + "...") if len(proc_data[5]) > 120 else proc_data[5],
                                        "elapsed_time": proc_data[3],
                                        "cpu_percent": proc_data[4],
                                        "memory_percent": proc_data[4],  # Fixed index
                                        "status": "running"
                                    })
                    except Exception as e:
                        logging.debug(f"Error obteniendo info del proceso {pid}: {e}")
            except Exception as e:
                logging.debug(f"Error buscando procesos nmap: {e}")
            
            # Verificar scripts Python de escaneo
            try:
                python_pattern = r'python.*\.(scan|advanced_scan|topology_mapper)\.py'
                python_procs = subprocess.run(['pgrep', '-f', python_pattern], 
                                             capture_output=True, text=True, timeout=5)
                python_pids = [pid.strip() for pid in python_procs.stdout.strip().split('\n') 
                              if pid.strip() and pid.strip().isdigit()] if python_procs.returncode == 0 else []
                
                for pid in python_pids:
                    try:
                        proc_info = subprocess.run(['ps', '-p', pid, '-o', 'pid,cmd,etime'], 
                                                 capture_output=True, text=True, timeout=5)
                        if proc_info.returncode == 0:
                            lines = proc_info.stdout.strip().split('\n')
                            if len(lines) > 1:
                                proc_data = lines[1].split(None, 2)
                                if len(proc_data) >= 3:
                                    script_type = "unknown_script"
                                    if "scan.py" in proc_data[2]:
                                        script_type = "basic_scan_script"
                                    elif "advanced_scan.py" in proc_data[2]:
                                        script_type = "advanced_scan_script"
                                    elif "topology_mapper.py" in proc_data[2]:
                                        script_type = "topology_script"
                                    
                                    active_scans.append({
                                        "type": script_type,
                                        "pid": pid,
                                        "command": (proc_data[2][:100] + "...") if len(proc_data[2]) > 100 else proc_data[2],
                                        "elapsed_time": proc_data[1] if len(proc_data) > 1 else "unknown",
                                        "status": "running"
                                    })
                    except Exception as e:
                        logging.debug(f"Error obteniendo info del script Python {pid}: {e}")
            except Exception as e:
                logging.debug(f"Error buscando scripts Python: {e}")
            
            # Verificar lockfiles con más detalle
            lockfiles = {
                "/tmp/nmap_scan.lock": "basic_scan",
                "/tmp/advanced_scan.lock": "advanced_scan"
            }
            
            for lockfile, scan_type in lockfiles.items():
                if os.path.exists(lockfile):
                    try:
                        stat_info = os.stat(lockfile)
                        age_seconds = int(datetime.utcnow().timestamp() - stat_info.st_mtime)
                        
                        # Leer contenido del lock
                        lock_content = "unknown"
                        try:
                            with open(lockfile, 'r') as f:
                                lock_content = f.read().strip()
                        except:
                            pass
                        
                        # Verificar si el proceso del lock aún existe
                        lock_valid = False
                        if ":" in lock_content:
                            try:
                                lock_pid = lock_content.split(":")[0]
                                if lock_pid.isdigit():
                                    proc_check = subprocess.run(['ps', '-p', lock_pid], 
                                                               capture_output=True, timeout=2)
                                    lock_valid = proc_check.returncode == 0
                            except:
                                pass
                        
                        status = "active_lock" if lock_valid else "stale_lock"
                        if age_seconds > 3600:  # Más de 1 hora
                            status = "stale_lock"
                        
                        active_scans.append({
                            "type": f"{scan_type}_lock",
                            "lockfile": lockfile,
                            "lock_content": lock_content,
                            "locked_since": datetime.fromtimestamp(stat_info.st_mtime).isoformat() + "Z",
                            "lock_age_seconds": age_seconds,
                            "lock_age_human": self._format_uptime(age_seconds),
                            "lock_valid": lock_valid,
                            "status": status
                        })
                    except Exception as e:
                        logging.debug(f"Error procesando lockfile {lockfile}: {e}")
        
        except Exception as e:
            logging.error(f"Error verificando escaneos activos: {e}")
            active_scans.append({
                "type": "error",
                "error": str(e),
                "status": "error"
            })
        
        return active_scans

    def _get_system_resources(self):
        """Obtiene información de recursos del sistema con múltiples fallbacks"""
        resources = {}
        
        try:
            # CPU usage - múltiples métodos
            try:
                # Método 1: uptime
                load_avg = subprocess.run(['uptime'], capture_output=True, text=True, timeout=5)
                if load_avg.returncode == 0 and load_avg.stdout:
                    load_info = load_avg.stdout.strip()
                    if "load average:" in load_info:
                        resources["load_average"] = load_info.split("load average:")[-1].strip()
                        # Extraer primer valor de load average como porcentaje aproximado
                        load_values = resources["load_average"].split(',')
                        if load_values:
                            try:
                                first_load = float(load_values[0].strip())
                                resources["cpu_percent"] = min(round(first_load * 100, 1), 100.0)
                            except:
                                pass
            except:
                pass
            
            # CPU usage fallback - usando /proc/stat
            if "cpu_percent" not in resources:
                try:
                    with open('/proc/stat', 'r') as f:
                        cpu_line = f.readline()
                        cpu_times = [int(x) for x in cpu_line.split()[1:]]
                        total_time = sum(cpu_times)
                        idle_time = cpu_times[3]  # idle time
                        cpu_usage = round((1 - idle_time / total_time) * 100, 1) if total_time > 0 else 0
                        resources["cpu_percent"] = cpu_usage
                except:
                    resources["cpu_percent"] = "unavailable"
            
            # Memory usage - múltiples métodos
            try:
                # Método 1: free command
                memory_info = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=5)
                if memory_info.returncode == 0:
                    lines = memory_info.stdout.strip().split('\n')
                    if len(lines) > 1:
                        mem_line = lines[1].split()
                        if len(mem_line) >= 3:
                            total = int(mem_line[1])
                            used = int(mem_line[2])
                            resources["memory_total_mb"] = total
                            resources["memory_used_mb"] = used
                            resources["memory_percent"] = round((used / total) * 100, 1)
            except:
                pass
            
            # Memory fallback - usando /proc/meminfo
            if "memory_percent" not in resources:
                try:
                    with open('/proc/meminfo', 'r') as f:
                        meminfo = f.read()
                        
                    mem_total = None
                    mem_available = None
                    
                    for line in meminfo.split('\n'):
                        if line.startswith('MemTotal:'):
                            mem_total = int(line.split()[1]) // 1024  # Convert KB to MB
                        elif line.startswith('MemAvailable:'):
                            mem_available = int(line.split()[1]) // 1024
                    
                    if mem_total and mem_available:
                        mem_used = mem_total - mem_available
                        resources["memory_total_mb"] = mem_total
                        resources["memory_used_mb"] = mem_used
                        resources["memory_percent"] = round((mem_used / mem_total) * 100, 1)
                except:
                    resources["memory_percent"] = "unavailable"
            
            # Disk usage - con fallbacks
            try:
                # Método 1: df command
                disk_info = subprocess.run(['df', '-h', '/results'], capture_output=True, text=True, timeout=5)
                if disk_info.returncode == 0:
                    lines = disk_info.stdout.strip().split('\n')
                    if len(lines) > 1:
                        disk_line = lines[1].split()
                        if len(disk_line) >= 5:
                            resources["disk_total"] = disk_line[1]
                            resources["disk_used"] = disk_line[2]
                            resources["disk_available"] = disk_line[3]
                            resources["disk_percent"] = float(disk_line[4].replace('%', ''))
            except:
                pass
            
            # Disk usage fallback - usando os.statvfs
            if "disk_percent" not in resources:
                try:
                    statvfs = os.statvfs('/results')
                    total_bytes = statvfs.f_frsize * statvfs.f_blocks
                    free_bytes = statvfs.f_frsize * statvfs.f_available
                    used_bytes = total_bytes - free_bytes
                    
                    resources["disk_total"] = f"{total_bytes // (1024**3)}G"
                    resources["disk_used"] = f"{used_bytes // (1024**3)}G"
                    resources["disk_available"] = f"{free_bytes // (1024**3)}G"
                    resources["disk_percent"] = round((used_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0
                except:
                    resources["disk_percent"] = "unavailable"
            
            # System uptime
            try:
                # Método 1: /proc/uptime
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                    resources["uptime"] = int(uptime_seconds)
                    resources["uptime_human"] = self._format_uptime(uptime_seconds)
            except:
                try:
                    # Método 2: uptime command
                    uptime_info = subprocess.run(['uptime', '-s'], capture_output=True, text=True, timeout=5)
                    if uptime_info.returncode == 0:
                        # uptime -s da fecha de inicio, calcular diferencia
                        from datetime import datetime
                        boot_time = datetime.strptime(uptime_info.stdout.strip(), '%Y-%m-%d %H:%M:%S')
                        now = datetime.now()
                        uptime_seconds = (now - boot_time).total_seconds()
                        resources["uptime"] = int(uptime_seconds)
                        resources["uptime_human"] = self._format_uptime(uptime_seconds)
                except:
                    resources["uptime"] = "unavailable"
        
        except Exception as e:
            logging.error(f"Error obteniendo recursos del sistema: {e}")
            resources["error"] = str(e)
        
        return resources

    def _format_uptime(self, seconds):
        """Formatea tiempo de actividad en formato legible"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _get_recent_activity(self):
        """Obtiene actividad reciente del sistema"""
        activity = []
        
        try:
            # Archivos creados recientemente en /results
            result_files = glob.glob("/results/*")
            if result_files:
                # Ordenar por fecha de modificación (más reciente primero)
                result_files.sort(key=os.path.getmtime, reverse=True)
                
                for file_path in result_files[:5]:  # Solo los 5 más recientes
                    stat_info = os.stat(file_path)
                    filename = os.path.basename(file_path)
                    
                    # Determinar tipo de archivo
                    file_type = "unknown"
                    if filename.startswith("nmap_") and filename.endswith(".xml"):
                        file_type = "basic_scan"
                    elif filename.startswith("advanced_scan_") and filename.endswith(".json"):
                        file_type = "advanced_scan"
                    elif filename == "topology.json":
                        file_type = "topology"
                    elif filename == "scan_history.json":
                        file_type = "history"
                    
                    activity.append({
                        "type": "file_created",
                        "filename": filename,
                        "file_type": file_type,
                        "size_bytes": stat_info.st_size,
                        "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat() + "Z",
                        "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat() + "Z"
                    })
            
            # Log entries recientes (si existe archivo de log)
            log_file = "/var/log/nmap_scanner.log"
            if os.path.exists(log_file):
                try:
                    # Leer las últimas 10 líneas del log
                    tail_result = subprocess.run(['tail', '-n', '10', log_file], 
                                               capture_output=True, text=True)
                    if tail_result.returncode == 0:
                        log_lines = tail_result.stdout.strip().split('\n')
                        for line in log_lines[-3:]:  # Solo las 3 más recientes
                            if line.strip():
                                activity.append({
                                    "type": "log_entry",
                                    "message": line.strip()[:100] + "..." if len(line.strip()) > 100 else line.strip(),
                                    "timestamp": "recent"
                                })
                except:
                    pass
        
        except Exception as e:
            logging.error(f"Error obteniendo actividad reciente: {e}")
        
        return activity

    def _get_scan_queue_status(self):
        """Obtiene estado de la cola de escaneos"""
        queue_status = {
            "pending_scans": 0,
            "max_concurrent": 1,
            "can_accept_new": True
        }
        
        try:
            # Verificar límites de configuración
            scan_limits = self.config_manager.get_scan_limits()
            max_concurrent = scan_limits.get("concurrent_scans", 1)
            
            # Contar escaneos activos
            active_scans = self._check_active_scans()
            active_count = len([scan for scan in active_scans if scan.get("status") == "running"])
            
            queue_status.update({
                "active_scans": active_count,
                "max_concurrent": max_concurrent,
                "can_accept_new": active_count < max_concurrent,
                "queue_availability": f"{active_count}/{max_concurrent}"
            })
        
        except Exception as e:
            logging.error(f"Error obteniendo estado de cola: {e}")
        
        return queue_status

    def _analyze_scan_file(self, xml_file):
        """Analiza rápidamente un archivo de escaneo XML"""
        analysis = {
            "hosts_found": 0,
            "ports_found": 0,
            "services_identified": 0,
            "scan_complete": False
        }
        
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            hosts = root.findall("host")
            analysis["hosts_found"] = len(hosts)
            
            total_ports = 0
            services = set()
            
            for host in hosts:
                ports = host.find("ports")
                if ports is not None:
                    port_list = ports.findall("port")
                    total_ports += len(port_list)
                    
                    for port in port_list:
                        service_el = port.find("service")
                        if service_el is not None:
                            service_name = service_el.get("name")
                            if service_name:
                                services.add(service_name)
            
            analysis["ports_found"] = total_ports
            analysis["services_identified"] = len(services)
            analysis["scan_complete"] = root.get("exit") == "success"
            
            # Lista de servicios únicos encontrados
            analysis["unique_services"] = sorted(list(services))[:10]  # Top 10
        
        except Exception as e:
            logging.error(f"Error analizando archivo de escaneo: {e}")
            analysis["error"] = str(e)
        
        return analysis

    def _get_scan_diagnostics(self):
        """Obtiene diagnósticos específicos para debugging de escaneos"""
        diagnostics = {
            "environment_vars": {},
            "scan_capabilities": {},
            "network_connectivity": {},
            "file_permissions": {}
        }
        
        try:
            # Variables de entorno relevantes
            env_vars = [
                "TARGET_NETWORK", "INFLUX_URL", "INFLUX_TOKEN", "SCAN_SCHEDULE", 
                "TOPOLOGY_SCHEDULE", "HTTP_PORT", "SCAN_TIMEOUT"
            ]
            for var in env_vars:
                value = os.getenv(var)
                diagnostics["environment_vars"][var] = value if value else "not_set"
            
            # Verificar capacidades de escaneo
            try:
                nmap_version = subprocess.run(['nmap', '--version'], capture_output=True, text=True, timeout=10)
                if nmap_version.returncode == 0:
                    version_line = nmap_version.stdout.split('\n')[0] if nmap_version.stdout else "unknown"
                    diagnostics["scan_capabilities"]["nmap_version"] = version_line
                else:
                    diagnostics["scan_capabilities"]["nmap_version"] = "nmap_not_available"
            except:
                diagnostics["scan_capabilities"]["nmap_version"] = "nmap_error"
            
            # Verificar herramientas de red
            network_tools = ["ping", "traceroute", "ip", "arp"]
            for tool in network_tools:
                try:
                    tool_check = subprocess.run(['which', tool], capture_output=True, timeout=5)
                    diagnostics["scan_capabilities"][f"{tool}_available"] = tool_check.returncode == 0
                except:
                    diagnostics["scan_capabilities"][f"{tool}_available"] = False
            
            # Verificar conectividad básica
            target_network = os.getenv("TARGET_NETWORK", "192.168.1.1")
            if target_network:
                # Extraer primera IP para ping test
                try:
                    import ipaddress
                    if "/" in target_network:
                        network = ipaddress.ip_network(target_network, strict=False)
                        test_ip = str(list(network.hosts())[0]) if list(network.hosts()) else str(network.network_address)
                    else:
                        test_ip = target_network
                    
                    ping_test = subprocess.run(['ping', '-c', '1', '-W', '2', test_ip], 
                                             capture_output=True, timeout=5)
                    diagnostics["network_connectivity"]["ping_test"] = {
                        "target": test_ip,
                        "success": ping_test.returncode == 0,
                        "response_time": "measured" if ping_test.returncode == 0 else "failed"
                    }
                except Exception as e:
                    diagnostics["network_connectivity"]["ping_test"] = {
                        "error": str(e)
                    }
            
            # Verificar permisos de archivos
            directories = ["/results", "/var/log", "/tmp"]
            for directory in directories:
                try:
                    if os.path.exists(directory):
                        stat_info = os.stat(directory)
                        diagnostics["file_permissions"][directory] = {
                            "exists": True,
                            "writable": os.access(directory, os.W_OK),
                            "readable": os.access(directory, os.R_OK),
                            "size": stat_info.st_size if os.path.isfile(directory) else "directory"
                        }
                    else:
                        diagnostics["file_permissions"][directory] = {
                            "exists": False
                        }
                except Exception as e:
                    diagnostics["file_permissions"][directory] = {
                        "error": str(e)
                    }
        
        except Exception as e:
            diagnostics["error"] = str(e)
        
        return diagnostics
        
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
        """Endpoint para escaneo avanzado en 2-3 fases (opcional: topología)"""
        logging.info("🎯 Advanced scan solicitado")
        try:
            data = self._read_json_body()
            
            if not data:
                raise ValueError("Body JSON requerido")
            
            network_name = data.get('network_name')
            network_cidr = data.get('network_cidr')
            include_topology = data.get('include_topology', True)  # Nueva opción
            
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
            logging.info(f"   Incluir topología: {include_topology}")
            
            # Preparar argumentos para el script
            cmd = ["/usr/local/bin/python", "/opt/nmap-scanner/src/advanced_scan.py"]
            if network_name:
                cmd.extend(["--network", network_name])
            else:
                cmd.extend(["--cidr", network_cidr])
            
            if include_topology:
                cmd.extend(["--topology"])  # Nuevo parámetro
            
            subprocess.Popen(cmd)
            
            phases = ["discovery", "detailed_scan"]
            if include_topology:
                phases.append("topology_mapping")
            
            response = {
                "status": "advanced_scan_started",
                "type": "advanced_scan_with_optional_topology",
                "network_name": network_name,
                "network_cidr": network_cidr,
                "include_topology": include_topology,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": f"Escaneo avanzado iniciado ({len(phases)} fases)",
                "phases": phases,
                "estimated_duration": "5-45 minutos dependiendo del tamaño de la red y opciones"
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