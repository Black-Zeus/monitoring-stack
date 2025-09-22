#!/usr/bin/env python3
"""
topology_mapper.py - Extensión para generar mapeo topológico de la red
Complementa scan.py agregando traceroute y detección de gateway/switches
"""

import os
import subprocess
import json
import logging
from datetime import datetime
import requests

# Configuración
TARGET_NETWORK = os.getenv("TARGET_NETWORK", "192.168.1.0/24")
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "home")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "nmap_bucket")


def discover_topology():
    """Descubre la topología usando traceroute y análisis de ARP"""
    topology_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "nodes": [],
        "edges": []
    }
    
    # Agregar nodo local
    topology_data["nodes"].append({
        "id": "local",
        "type": "host", 
        "label": "Local Host"
    })
    
    # 1. Obtener gateway por defecto
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True, check=True)
        gateway_line = result.stdout.strip().split('\n')[0]
        gateway_ip = gateway_line.split()[2]
        logging.info(f"Gateway detectado: {gateway_ip}")
        
        topology_data["nodes"].append({
            "id": gateway_ip,
            "type": "gateway",
            "label": f"Gateway ({gateway_ip})"
        })
    except Exception as e:
        logging.error(f"Error detectando gateway: {e}")

    # 2. Escaneo ping para hosts activos
    active_hosts = discover_active_hosts()
    
    # 3. Agregar hosts activos como nodos
    for host in active_hosts:
        if not any(node["id"] == host for node in topology_data["nodes"]):
            topology_data["nodes"].append({
                "id": host,
                "type": "host",
                "label": f"Host {host}"
            })

    # 4. Análisis de tabla ARP para dispositivos en misma subred
    try:
        arp_neighbors = get_arp_neighbors()
        for neighbor in arp_neighbors:
            neighbor_ip = neighbor["ip"]
            
            # Agregar nodo si no existe
            if not any(node["id"] == neighbor_ip for node in topology_data["nodes"]):
                node_type = "gateway" if neighbor_ip == gateway_ip else "host"
                topology_data["nodes"].append({
                    "id": neighbor_ip,
                    "type": node_type,
                    "label": f"Host {neighbor_ip}"
                })
            
            # Agregar edge
            topology_data["edges"].append({
                "source": "local",
                "target": neighbor_ip,
                "type": "l2_neighbor",
                "mac": neighbor["mac"]
            })
    except Exception as e:
        logging.error(f"Error analizando ARP: {e}")
    
    return topology_data

def discover_active_hosts():
    """Descubre hosts activos usando ping rápido"""
    network_base = TARGET_NETWORK.split('/')[0].rsplit('.', 1)[0]
    active_hosts = []
    
    # Ping rápido a rango común
    for i in range(1, 255):
        host = f"{network_base}.{i}"
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '1', host],
                capture_output=True, timeout=2
            )
            if result.returncode == 0:
                active_hosts.append(host)
                logging.info(f"Host activo encontrado: {host}")
        except:
            continue
    
    return active_hosts

def parse_traceroute(output):
    """Parsea output de traceroute y extrae IPs de hops"""
    hops = []
    lines = output.strip().split('\n')[1:]  # Skip primera línea
    
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 2:
            # Buscar IP en formato xxx.xxx.xxx.xxx
            for part in parts:
                if '.' in part and part.replace('.', '').replace('*', '').isdigit():
                    hops.append(part)
                    break
    
    return hops

def get_arp_neighbors():
    """Obtiene vecinos de tabla ARP"""
    neighbors = []
    try:
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            if '(' in line and ')' in line:
                # Formato: hostname (ip) at mac [flags] on interface
                ip_start = line.find('(') + 1
                ip_end = line.find(')')
                ip = line[ip_start:ip_end]
                
                mac_parts = line.split(' at ')
                if len(mac_parts) > 1:
                    mac = mac_parts[1].split()[0]
                    neighbors.append({"ip": ip, "mac": mac})
    
    except Exception as e:
        logging.error(f"Error obteniendo tabla ARP: {e}")
    
    return neighbors

def push_topology_to_influx(topology_data):
    """Envía datos de topología a InfluxDB"""
    points = []
    now_ns = int(datetime.utcnow().timestamp() * 1e9)
    
    # Crear puntos para nodos
    for node in topology_data["nodes"]:
        point = f'network_topology,node_id={node["id"]},node_type={node["type"]} label="{node["label"]}" {now_ns}'
        points.append(point)
    
    # Crear puntos para edges
    for edge in topology_data["edges"]:
        tags = f'source={edge["source"]},target={edge["target"]},edge_type={edge["type"]}'
        fields = f'connected=1i'
        if "mac" in edge:
            fields += f',mac="{edge["mac"]}"'
        point = f'network_edges,{tags} {fields} {now_ns}'
        points.append(point)
    
    # Enviar a InfluxDB
    if points:
        url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ns"
        headers = {
            "Authorization": f"Token {INFLUX_TOKEN}",
            "Content-Type": "text/plain; charset=utf-8"
        }
        payload = "\n".join(points)
        
        try:
            response = requests.post(url, data=payload.encode("utf-8"), headers=headers, timeout=30)
            response.raise_for_status()
            logging.info(f"Topología enviada a InfluxDB: {len(points)} puntos")
        except Exception as e:
            logging.error(f"Error enviando topología a InfluxDB: {e}")

def generate_topology_json(topology_data, output_file="/results/topology.json"):
    """Guarda topología en formato JSON para visualización"""
    try:
        with open(output_file, 'w') as f:
            json.dump(topology_data, f, indent=2)
        logging.info(f"Topología guardada en {output_file}")
    except Exception as e:
        logging.error(f"Error guardando topología: {e}")

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Iniciando descubrimiento de topología")
    
    topology_data = discover_topology()
    
    # Guardar en archivo JSON
    generate_topology_json(topology_data)
    
    # Enviar a InfluxDB para dashboards
    push_topology_to_influx(topology_data)
    
    logging.info("Mapeo topológico completado")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())