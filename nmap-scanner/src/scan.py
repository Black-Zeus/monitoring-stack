#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan.py - Ejecuta nmap, parsea salida XML y empuja los resultados a InfluxDB v2.
Diseñado para correr dentro del contenedor nmap-scanner.
"""

import os
import sys
import subprocess
import time
import uuid
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import requests
import fcntl

# --- Configuración por entorno ---
TARGET_NETWORK = os.getenv("TARGET_NETWORK", "192.168.1.0/24")
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "home")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "nmap_bucket")
SCAN_TIMEOUT = int(os.getenv("SCAN_TIMEOUT", "900"))  # segundos
RESULT_DIR = os.getenv("RESULT_DIR", "/results")
LOCKFILE = os.getenv("LOCKFILE", "/tmp/nmap_scan.lock")
NMAP_CMD = os.getenv("NMAP_CMD", "nmap")  # permite sobreescribir si es necesario
MEASUREMENT = os.getenv("MEASUREMENT", "nmap_ports")
# ---------------------------------

# Logging básico
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout
)

def obtain_lock(lockfile=LOCKFILE):
    """Crear y bloquear archivo para evitar ejecución concurrente."""
    fd = open(lockfile, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        return fd
    except BlockingIOError:
        fd.close()
        return None

def release_lock(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
    except Exception:
        pass

def run_nmap(target, out_xml, timeout=SCAN_TIMEOUT):
    """Ejecuta nmap -sV y guarda salida en out_xml. Lanza excepción en error."""
    cmd = [NMAP_CMD, "-sV", "-oX", out_xml, target]
    logging.info("Ejecutando Nmap: %s", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, timeout=timeout, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logging.info("Nmap finalizó correctamente. XML: %s", out_xml)
    except subprocess.CalledProcessError as e:
        logging.error("Nmap exit code != 0. stdout: %s stderr: %s", e.stdout, e.stderr)
        raise
    except subprocess.TimeoutExpired:
        logging.error("Nmap excedió timeout de %s segundos", timeout)
        raise

def xml_to_points(xmlfile):
    """Parsea XML de nmap y retorna lista de puntos en line-protocol para InfluxDB."""
    points = []
    try:
        tree = ET.parse(xmlfile)
        root = tree.getroot()
    except ET.ParseError as e:
        logging.error("Error parseando XML %s: %s", xmlfile, e)
        return points

    now_ns = int(time.time() * 1e9)
    run_id = uuid.uuid4().hex[:8]

    # Nmap XML estructura: <nmaprun><host>...
    for host in root.findall("host"):
        # obtener IP
        ip = None
        for addr in host.findall("address"):
            if addr.get("addrtype") in ("ipv4", "ipv6"):
                ip = addr.get("addr")
                break
        if ip is None:
            continue

        # Obtener hostname si existe
        hostname = ""
        hostnames = host.find("hostnames")
        if hostnames is not None:
            hn = hostnames.find("hostname")
            if hn is not None:
                hostname = hn.get("name", "")

        # obtener puerto/servicio
        ports = host.find("ports")
        if ports is None:
            continue
        for port in ports.findall("port"):
            portid = port.get("portid", "")
            protocol = port.get("protocol", "")
            state_el = port.find("state")
            state = state_el.get("state") if state_el is not None else ""
            service_el = port.find("service")
            service = ""
            version = ""
            product = ""
            if service_el is not None:
                service = service_el.get("name", "") or ""
                product = service_el.get("product", "") or ""
                version = service_el.get("version", "") or ""

            # Escapar comas/espacios/igual en tags y campos para line protocol
            def esc_tag(s):
                return str(s).replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")
            def esc_field_str(s):
                return str(s).replace("\\", "\\\\").replace('"', '\\"')

            tags = f"ip={esc_tag(ip)},port={esc_tag(portid)},protocol={esc_tag(protocol)},service={esc_tag(service)}"
            # Campos: state (string), product+version (string), hostname (string), run_id
            fields = f'state="{esc_field_str(state)}",product="{esc_field_str(product)}",version="{esc_field_str(version)}",hostname="{esc_field_str(hostname)}",run_id="{run_id}"'
            point = f"{MEASUREMENT},{tags} {fields} {now_ns}"
            points.append(point)
    logging.info("Puntos generados desde XML %s: %d", xmlfile, len(points))
    return points

def push_to_influx(points):
    """Envía lista de points (line protocol) a InfluxDB v2."""
    if not points:
        logging.info("Sin puntos a enviar a InfluxDB.")
        return
    url = f"{INFLUX_URL.rstrip('/')}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ns"
    headers = {
        "Authorization": f"Token {INFLUX_TOKEN}",
        "Content-Type": "text/plain; charset=utf-8"
    }
    payload = "\n".join(points)
    logging.info("Enviando %d puntos a InfluxDB en %s", len(points), url)
    try:
        r = requests.post(url, data=payload.encode("utf-8"), headers=headers, timeout=30)
        r.raise_for_status()
        logging.info("InfluxDB write OK (status %s)", r.status_code)
    except Exception as e:
        logging.error("Error enviando a InfluxDB: %s", e)
        raise

def ensure_result_dir(path=RESULT_DIR):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        logging.error("No se pudo crear directorio %s: %s", path, e)
        raise

def main():
    logging.info("Inicio de scan.py - target=%s", TARGET_NETWORK)

    # obtener lock para evitar ejecuciones paralelas
    lockfd = obtain_lock()
    if lockfd is None:
        logging.warning("Otro scan está en curso (lock detectado). Abortando ejecución.")
        return 0

    ensure_result_dir()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    xml_out = os.path.join(RESULT_DIR, f"nmap_{timestamp}.xml")

    try:
        run_nmap(TARGET_NETWORK, xml_out)
    except Exception as e:
        logging.error("Fallo en ejecución de nmap: %s", e)
        release_lock(lockfd)
        return 2

    try:
        points = xml_to_points(xml_out)
        if points:
            push_to_influx(points)
        else:
            logging.info("No se generaron puntos desde el XML; no se envía nada a InfluxDB.")
    except Exception as e:
        logging.error("Error durante parse/push: %s", e)
        # no fallamos silenciosamente, pero liberamos lock
        release_lock(lockfd)
        return 3

    release_lock(lockfd)
    logging.info("Scan finalizado correctamente. XML guardado en %s", xml_out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
