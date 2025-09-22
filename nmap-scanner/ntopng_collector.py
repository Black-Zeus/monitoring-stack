#!/usr/bin/env python3
"""
ntopng_collector.py - Recolecta métricas de ntopng vía API REST
y las envía a InfluxDB para dashboards unificados
"""

import os
import time
import requests
import logging
from datetime import datetime
import json

# Configuración
NTOPNG_URL = os.getenv("NTOPNG_URL", "http://ntopng:3000")
NTOPNG_USER = os.getenv("NTOPNG_USER", "admin")  
NTOPNG_PASSWORD = os.getenv("NTOPNG_PASSWORD", "admin")
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "home")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "nmap_bucket")
COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "300"))  # 5 min

class NtopngCollector:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = NTOPNG_URL.rstrip('/')
        
    def authenticate(self):
        """Autenticación con ntopng"""
        try:
            # ntopng típicamente usa autenticación básica
            self.session.auth = (NTOPNG_USER, NTOPNG_PASSWORD)
            
            # Verificar conectividad
            response = self.session.get(f"{self.base_url}/lua/rest/v2/get/system/stats.lua")
            response.raise_for_status()
            logging.info("Autenticación con ntopng exitosa")
            return True
        except Exception as e:
            logging.error(f"Error autenticando con ntopng: {e}")
            return False
    
    def get_interface_stats(self, interface_id="0"):
        """Obtiene estadísticas de interfaz"""
        try:
            url = f"{self.base_url}/lua/rest/v2/get/interface/stats.lua"
            params = {"ifid": interface_id}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error obteniendo stats de interfaz: {e}")
            return None
    
    def get_top_talkers(self, interface_id="0", limit=20):
        """Obtiene top talkers (hosts con más tráfico)"""
        try:
            url = f"{self.base_url}/lua/rest/v2/get/host/active.lua"
            params = {
                "ifid": interface_id,
                "currentPage": 1,
                "perPage": limit,
                "sortColumn": "bytes",
                "sortOrder": "desc"
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error obteniendo top talkers: {e}")
            return None
    
    def get_protocol_stats(self, interface_id="0"):
        """Obtiene estadísticas de protocolos"""
        try:
            url = f"{self.base_url}/lua/rest/v2/get/interface/l7/stats.lua"
            params = {"ifid": interface_id}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error obteniendo stats de protocolos: {e}")
            return None
    
    def get_active_flows(self, interface_id="0"):
        """Obtiene flujos activos"""
        try:
            url = f"{self.base_url}/lua/rest/v2/get/flow/active.lua"
            params = {"ifid": interface_id}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error obteniendo flujos activos: {e}")
            return None

    def collect_all_metrics(self):
        """Recolecta todas las métricas disponibles"""
        metrics = {}
        
        # Stats de interfaz
        interface_stats = self.get_interface_stats()
        if interface_stats:
            metrics["interface"] = interface_stats
        
        # Top talkers
        top_talkers = self.get_top_talkers()
        if top_talkers:
            metrics["top_talkers"] = top_talkers
        
        # Protocolos
        protocol_stats = self.get_protocol_stats()
        if protocol_stats:
            metrics["protocols"] = protocol_stats
        
        # Flujos activos
        active_flows = self.get_active_flows()
        if active_flows:
            metrics["flows"] = active_flows
        
        return metrics

def convert_to_influx_points(metrics_data):
    """Convierte métricas de ntopng a formato InfluxDB"""
    points = []
    now_ns = int(time.time() * 1e9)
    
    # Estadísticas de interfaz
    if "interface" in metrics_data:
        iface = metrics_data["interface"]
        if "stats" in iface:
            stats = iface["stats"]
            fields = []
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    fields.append(f"{key}={value}")
            
            if fields:
                point = f'ntopng_interface {",".join(fields)} {now_ns}'
                points.append(point)
    
    # Top talkers
    if "top_talkers" in metrics_data:
        talkers = metrics_data["top_talkers"]
        if "data" in talkers:
            for host in talkers["data"]:
                ip = host.get("host", "unknown")
                bytes_sent = host.get("bytes.sent", 0)
                bytes_rcvd = host.get("bytes.rcvd", 0)
                
                # Escapar IP para tags
                ip_escaped = str(ip).replace(",", "\\,").replace(" ", "\\ ").replace("=", "\\=")
                
                point = f'ntopng_hosts,ip={ip_escaped} bytes_sent={bytes_sent},bytes_rcvd={bytes_rcvd} {now_ns}'
                points.append(point)
    
    # Estadísticas de protocolos
    if "protocols" in metrics_data:
        protocols = metrics_data["protocols"]
        for proto_name, proto_data in protocols.items():
            if isinstance(proto_data, dict) and "bytes" in proto_data:
                proto_escaped = str(proto_name).replace(",", "\\,").replace(" ", "\\ ").replace("=", "\\=")
                bytes_val = proto_data["bytes"]
                
                point = f'ntopng_protocols,protocol={proto_escaped} bytes={bytes_val} {now_ns}'
                points.append(point)
    
    # Número de flujos activos
    if "flows" in metrics_data:
        flows = metrics_data["flows"]
        if "perPage" in flows:
            active_flows_count = len(flows.get("data", []))
            point = f'ntopng_flows active_count={active_flows_count} {now_ns}'
            points.append(point)
    
    return points

def push_to_influx(points):
    """Envía puntos a InfluxDB"""
    if not points:
        logging.info("No hay puntos para enviar")
        return
    
    url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ns"
    headers = {
        "Authorization": f"Token {INFLUX_TOKEN}",
        "Content-Type": "text/plain; charset=utf-8"
    }
    payload = "\n".join(points)
    
    try:
        response = requests.post(url, data=payload.encode("utf-8"), headers=headers, timeout=30)
        response.raise_for_status()
        logging.info(f"Métricas ntopng enviadas a InfluxDB: {len(points)} puntos")
    except Exception as e:
        logging.error(f"Error enviando métricas a InfluxDB: {e}")

def main():
    logging.basicConfig(level=logging.INFO)
    
    collector = NtopngCollector()
    
    if not collector.authenticate():
        logging.error("No se pudo autenticar con ntopng")
        return 1
    
    while True:
        try:
            logging.info("Recolectando métricas de ntopng...")
            metrics = collector.collect_all_metrics()
            
            if metrics:
                points = convert_to_influx_points(metrics)
                push_to_influx(points)
            else:
                logging.warning("No se obtuvieron métricas")
            
            logging.info(f"Esperando {COLLECTION_INTERVAL} segundos hasta próxima recolección...")
            time.sleep(COLLECTION_INTERVAL)
            
        except KeyboardInterrupt:
            logging.info("Deteniendo recolección de métricas")
            break
        except Exception as e:
            logging.error(f"Error en ciclo principal: {e}")
            time.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())