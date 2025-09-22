#!/usr/bin/env python3
"""
advanced_scan.py - Escaneo avanzado en 2 fases con nmap
Fase 1: Descubrimiento rápido de puertos abiertos
Fase 2: Detección detallada de servicios en puertos encontrados
"""

import os
import sys
import subprocess
import json
import time
import uuid
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Tuple
import requests
import fcntl
from config_manager import get_config_manager


class AdvancedScanner:
    def __init__(self, network_name: str = None, network_cidr: str = None):
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config
        
        # Configurar logging
        self._setup_logging()
        
        # Identificador único del escaneo
        self.scan_id = uuid.uuid4().hex[:8]
        self.start_time = datetime.utcnow()
        
        # Red objetivo
        self.network_name = network_name
        self.network_cidr = network_cidr
        
        # Resultados de las fases
        self.phase1_results = {}  # {ip: [ports]}
        self.phase2_results = {}  # Resultados detallados
        
        # Configuraciones
        self.limits = self.config_manager.get_scan_limits()
        self.scan_options = self.config_manager.get_scan_options()
        self.output_config = self.config_manager.get_output_config()
        self.influx_config = self.config_manager.get_influxdb_config()
        
        # Archivos de salida
        self.results_dir = self.output_config.get("results_dir", "/results")
        self.timestamp = self.start_time.strftime("%Y%m%dT%H%M%SZ")
        
        logging.info(f"🚀 Advanced Scanner iniciado - ID: {self.scan_id}")
    
    def _setup_logging(self):
        """Configura logging detallado"""
        log_config = self.config_manager.get_logging_config()
        log_level = getattr(logging, log_config.get("level", "INFO"))
        
        # Crear directorio de logs si no existe
        log_file = log_config.get("file", "/var/log/advanced_scan.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Configurar logging
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file)
            ]
        )
    
    def get_lock(self, lockfile: str = "/tmp/advanced_scan.lock") -> Optional[object]:
        """Obtiene lock para evitar escaneos concurrentes"""
        try:
            fd = open(lockfile, "w")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fd.write(f"{os.getpid()}:{self.scan_id}")
            fd.flush()
            return fd
        except BlockingIOError:
            return None
        except Exception as e:
            logging.error(f"Error obteniendo lock: {e}")
            return None
    
    def release_lock(self, fd):
        """Libera lock de escaneo"""
        try:
            if fd:
                fcntl.flock(fd, fcntl.LOCK_UN)
                fd.close()
        except Exception as e:
            logging.error(f"Error liberando lock: {e}")
    
    def validate_target(self) -> bool:
        """Valida red objetivo"""
        if self.network_cidr:
            return self.config_manager.validate_network_cidr(self.network_cidr)
        
        if self.network_name:
            network_config = self.config_manager.get_network(self.network_name)
            if not network_config:
                logging.error(f"Red {self.network_name} no encontrada en configuración")
                return False
            
            if not network_config.get("enabled", True):
                logging.error(f"Red {self.network_name} está deshabilitada")
                return False
            
            self.network_cidr = network_config["cidr"]
            return True
        
        logging.error("No se especificó red objetivo válida")
        return False
    
    def run_phase1(self) -> Dict[str, List[int]]:
        """
        Fase 1: Descubrimiento rápido de puertos abiertos
        Comando: nmap -p- --open -sS --min-rate 5000 -vvv -n -Pn
        """
        logging.info("🔍 FASE 1: Iniciando descubrimiento rápido de puertos")
        
        phase1_cmd = self.scan_options["phase1"]["command"]
        xml_file = os.path.join(self.results_dir, f"phase1_{self.scan_id}_{self.timestamp}.xml")
        
        # Construir comando completo
        cmd = phase1_cmd.split() + ["-oX", xml_file, self.network_cidr]
        
        logging.info(f"Ejecutando: {' '.join(cmd)}")
        
        try:
            # Ejecutar con timeout
            timeout = self.limits.get("phase1_timeout", 1800)
            start_time = time.time()
            
            proc = subprocess.run(
                cmd,
                timeout=timeout,
                capture_output=True,
                text=True,
                check=True
            )
            
            elapsed = time.time() - start_time
            logging.info(f"✅ Fase 1 completada en {elapsed:.1f} segundos")
            
            # Parsear resultados
            results = self._parse_phase1_xml(xml_file)
            self.phase1_results = results
            
            # Estadísticas
            total_hosts = len(results)
            total_ports = sum(len(ports) for ports in results.values())
            logging.info(f"📊 Fase 1 - Hosts: {total_hosts}, Puertos abiertos: {total_ports}")
            
            return results
            
        except subprocess.TimeoutExpired:
            logging.error(f"❌ Fase 1 excedió timeout de {timeout} segundos")
            raise
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ Fase 1 falló - Exit code: {e.returncode}")
            logging.error(f"STDOUT: {e.stdout}")
            logging.error(f"STDERR: {e.stderr}")
            raise
        except Exception as e:
            logging.error(f"❌ Error en Fase 1: {e}")
            raise
    
    def _parse_phase1_xml(self, xml_file: str) -> Dict[str, List[int]]:
        """Parsea XML de Fase 1 y extrae IPs con puertos abiertos"""
        results = {}
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            for host in root.findall("host"):
                # Obtener IP
                ip = None
                for addr in host.findall("address"):
                    if addr.get("addrtype") in ("ipv4", "ipv6"):
                        ip = addr.get("addr")
                        break
                
                if not ip:
                    continue
                
                # Obtener puertos abiertos
                open_ports = []
                ports = host.find("ports")
                if ports is not None:
                    for port in ports.findall("port"):
                        state_el = port.find("state")
                        if state_el is not None and state_el.get("state") == "open":
                            port_num = int(port.get("portid"))
                            open_ports.append(port_num)
                
                if open_ports:
                    results[ip] = sorted(open_ports)
                    logging.debug(f"Host {ip}: {len(open_ports)} puertos abiertos")
            
            logging.info(f"Fase 1 parseada: {len(results)} hosts con puertos abiertos")
            return results
            
        except Exception as e:
            logging.error(f"Error parseando XML Fase 1: {e}")
            return {}
    
    def run_phase2(self, phase1_results: Dict[str, List[int]]) -> Dict[str, Dict]:
        """
        Fase 2: Detección detallada de servicios
        Comando: nmap -sCV -p<puertos_encontrados>
        """
        logging.info("🔬 FASE 2: Iniciando detección detallada de servicios")
        
        if not phase1_results:
            logging.warning("No hay resultados de Fase 1, saltando Fase 2")
            return {}
        
        phase2_cmd_template = self.scan_options["phase2"]["command"]
        all_results = {}
        
        # Procesar cada host individualmente
        for ip, ports in phase1_results.items():
            try:
                logging.info(f"🎯 Analizando {ip} - {len(ports)} puertos")
                
                # Construir lista de puertos
                ports_str = ",".join(map(str, ports))
                phase2_cmd = phase2_cmd_template.replace("{ports}", ports_str)
                
                xml_file = os.path.join(self.results_dir, f"phase2_{self.scan_id}_{ip}_{self.timestamp}.xml")
                cmd = phase2_cmd.split() + ["-oX", xml_file, ip]
                
                logging.debug(f"Ejecutando: {' '.join(cmd)}")
                
                # Ejecutar con timeout
                timeout = self.limits.get("phase2_timeout", 3600)
                start_time = time.time()
                
                proc = subprocess.run(
                    cmd,
                    timeout=timeout,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                elapsed = time.time() - start_time
                logging.info(f"✅ Fase 2 para {ip} completada en {elapsed:.1f}s")
                
                # Parsear resultados detallados
                host_results = self._parse_phase2_xml(xml_file)
                if host_results:
                    all_results[ip] = host_results
                
            except subprocess.TimeoutExpired:
                logging.error(f"❌ Fase 2 para {ip} excedió timeout")
                continue
            except subprocess.CalledProcessError as e:
                logging.error(f"❌ Fase 2 para {ip} falló - Exit code: {e.returncode}")
                continue
            except Exception as e:
                logging.error(f"❌ Error en Fase 2 para {ip}: {e}")
                continue
        
        self.phase2_results = all_results
        logging.info(f"📊 Fase 2 completada - {len(all_results)} hosts analizados")
        return all_results
    
    def _parse_phase2_xml(self, xml_file: str) -> Dict:
        """Parsea XML de Fase 2 con información detallada"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            host_data = {}
            
            for host in root.findall("host"):
                # IP y hostname
                ip = None
                hostname = ""
                
                for addr in host.findall("address"):
                    if addr.get("addrtype") in ("ipv4", "ipv6"):
                        ip = addr.get("addr")
                        break
                
                hostnames = host.find("hostnames")
                if hostnames is not None:
                    hn = hostnames.find("hostname")
                    if hn is not None:
                        hostname = hn.get("name", "")
                
                if not ip:
                    continue
                
                # Información de puertos y servicios
                ports_info = {}
                ports = host.find("ports")
                if ports is not None:
                    for port in ports.findall("port"):
                        port_num = port.get("portid")
                        protocol = port.get("protocol", "tcp")
                        
                        state_el = port.find("state")
                        state = state_el.get("state") if state_el is not None else "unknown"
                        
                        service_el = port.find("service")
                        service_info = {}
                        if service_el is not None:
                            service_info = {
                                "name": service_el.get("name", ""),
                                "product": service_el.get("product", ""),
                                "version": service_el.get("version", ""),
                                "extrainfo": service_el.get("extrainfo", ""),
                                "tunnel": service_el.get("tunnel", ""),
                                "method": service_el.get("method", "")
                            }
                        
                        # Scripts NSE
                        scripts = {}
                        for script in port.findall("script"):
                            script_id = script.get("id", "")
                            script_output = script.get("output", "")
                            if script_id:
                                scripts[script_id] = script_output
                        
                        ports_info[f"{port_num}/{protocol}"] = {
                            "state": state,
                            "service": service_info,
                            "scripts": scripts
                        }
                
                # OS Detection
                os_info = {}
                os_el = host.find("os")
                if os_el is not None:
                    for osmatch in os_el.findall("osmatch"):
                        name = osmatch.get("name", "")
                        accuracy = osmatch.get("accuracy", "0")
                        if name:
                            os_info[name] = accuracy
                
                host_data = {
                    "ip": ip,
                    "hostname": hostname,
                    "ports": ports_info,
                    "os": os_info,
                    "scan_time": datetime.utcnow().isoformat() + "Z"
                }
            
            return host_data
            
        except Exception as e:
            logging.error(f"Error parseando XML Fase 2: {e}")
            return {}
    
    def generate_summary_report(self) -> Dict:
        """Genera reporte resumen del escaneo completo"""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        # Estadísticas generales
        total_hosts_phase1 = len(self.phase1_results)
        total_ports_phase1 = sum(len(ports) for ports in self.phase1_results.values())
        total_hosts_phase2 = len(self.phase2_results)
        
        # Servicios únicos encontrados
        unique_services = set()
        for host_data in self.phase2_results.values():
            for port_info in host_data.get("ports", {}).values():
                service_name = port_info.get("service", {}).get("name", "")
                if service_name:
                    unique_services.add(service_name)
        
        summary = {
            "scan_id": self.scan_id,
            "network": {
                "name": self.network_name,
                "cidr": self.network_cidr
            },
            "timing": {
                "start_time": self.start_time.isoformat() + "Z",
                "end_time": end_time.isoformat() + "Z",
                "duration_seconds": round(duration, 2)
            },
            "statistics": {
                "phase1": {
                    "hosts_with_open_ports": total_hosts_phase1,
                    "total_open_ports": total_ports_phase1
                },
                "phase2": {
                    "hosts_analyzed": total_hosts_phase2,
                    "unique_services": len(unique_services),
                    "services_list": sorted(list(unique_services))
                }
            },
            "results": {
                "phase1_summary": {ip: len(ports) for ip, ports in self.phase1_results.items()},
                "phase2_detailed": self.phase2_results
            }
        }
        
        return summary
    
    def save_results(self, summary: Dict) -> str:
        """Guarda resultados en archivo JSON"""
        try:
            os.makedirs(self.results_dir, exist_ok=True)
            
            filename = f"advanced_scan_{self.scan_id}_{self.timestamp}.json"
            filepath = os.path.join(self.results_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logging.info(f"📄 Resultados guardados en {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Error guardando resultados: {e}")
            raise
    
    def update_scan_history(self, summary: Dict) -> None:
        """Actualiza historial de escaneos"""
        try:
            history_file = self.output_config.get("history_file", "/results/scan_history.json")
            
            # Cargar historial existente
            history = []
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history = json.load(f)
            
            # Agregar nuevo escaneo
            history_entry = {
                "scan_id": self.scan_id,
                "network_name": self.network_name,
                "network_cidr": self.network_cidr,
                "start_time": summary["timing"]["start_time"],
                "end_time": summary["timing"]["end_time"],
                "duration_seconds": summary["timing"]["duration_seconds"],
                "hosts_discovered": summary["statistics"]["phase1"]["hosts_with_open_ports"],
                "ports_found": summary["statistics"]["phase1"]["total_open_ports"],
                "services_identified": summary["statistics"]["phase2"]["unique_services"]
            }
            
            history.append(history_entry)
            
            # Mantener solo últimos N escaneos
            max_history = self.output_config.get("max_history_files", 50)
            if len(history) > max_history:
                history = history[-max_history:]
            
            # Guardar historial actualizado
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            logging.info(f"📚 Historial actualizado - {len(history)} escaneos registrados")
            
        except Exception as e:
            logging.error(f"Error actualizando historial: {e}")
    
    def send_to_influxdb(self, summary: Dict) -> None:
        """Envía resultados a InfluxDB"""
        if not self.influx_config.get("enabled", False):
            logging.info("InfluxDB deshabilitado, saltando envío")
            return
        
        try:
            points = self._convert_to_influx_points(summary)
            if not points:
                logging.warning("No se generaron puntos para InfluxDB")
                return
            
            url = f"{self.influx_config['url']}/api/v2/write"
            params = {
                "org": self.influx_config["org"],
                "bucket": self.influx_config["bucket"],
                "precision": "ns"
            }
            headers = {
                "Authorization": f"Token {self.influx_config['token']}",
                "Content-Type": "text/plain; charset=utf-8"
            }
            
            payload = "\n".join(points)
            
            response = requests.post(url, params=params, headers=headers, 
                                   data=payload.encode("utf-8"), timeout=30)
            response.raise_for_status()
            
            logging.info(f"📊 Enviados {len(points)} puntos a InfluxDB")
            
        except Exception as e:
            logging.error(f"Error enviando a InfluxDB: {e}")
    
    def _convert_to_influx_points(self, summary: Dict) -> List[str]:
        """Convierte resultados a formato InfluxDB line protocol"""
        points = []
        now_ns = int(time.time() * 1e9)
        measurement = self.influx_config.get("measurement", "advanced_nmap_scan")
        
        # Punto resumen del escaneo
        tags = f"scan_id={self.scan_id},network_name={self.network_name or 'manual'},network_cidr={self.network_cidr}"
        fields = []
        fields.append(f"hosts_discovered={summary['statistics']['phase1']['hosts_with_open_ports']}i")
        fields.append(f"ports_found={summary['statistics']['phase1']['total_open_ports']}i")
        fields.append(f"services_identified={summary['statistics']['phase2']['unique_services']}i")
        fields.append(f"duration_seconds={summary['timing']['duration_seconds']}")
        
        point = f"{measurement}_summary,{tags} {','.join(fields)} {now_ns}"
        points.append(point)
        
        # Puntos detallados por host
        for ip, host_data in summary["results"]["phase2_detailed"].items():
            for port_key, port_info in host_data.get("ports", {}).items():
                port_num, protocol = port_key.split("/")
                service_name = port_info.get("service", {}).get("name", "unknown")
                service_product = port_info.get("service", {}).get("product", "")
                service_version = port_info.get("service", {}).get("version", "")
                
                tags = f"scan_id={self.scan_id},ip={ip},port={port_num},protocol={protocol},service={service_name}"
                fields = [f'state="{port_info.get("state", "unknown")}"']
                if service_product:
                    fields.append(f'product="{service_product}"')
                if service_version:
                    fields.append(f'version="{service_version}"')
                
                point = f"{measurement}_ports,{tags} {','.join(fields)} {now_ns}"
                points.append(point)
        
        return points
    
    def run_full_scan(self) -> Dict:
        """Ejecuta escaneo completo en 2 fases"""
        logging.info("🎯 Iniciando escaneo avanzado completo")
        
        # Validar objetivo
        if not self.validate_target():
            raise ValueError("Red objetivo inválida")
        
        # Obtener lock
        lock_fd = self.get_lock()
        if not lock_fd:
            raise RuntimeError("Otro escaneo está en progreso")
        
        try:
            # Actualizar información de escaneo en configuración
            if self.network_name:
                self.config_manager.update_network_scan_info(self.network_name, True)
            
            # Ejecutar Fase 1
            phase1_results = self.run_phase1()
            
            # Ejecutar Fase 2
            phase2_results = self.run_phase2(phase1_results)
            
            # Generar reporte
            summary = self.generate_summary_report()
            
            # Guardar resultados
            results_file = self.save_results(summary)
            
            # Actualizar historial
            self.update_scan_history(summary)
            
            # Enviar a InfluxDB
            self.send_to_influxdb(summary)
            
            logging.info(f"🎉 Escaneo avanzado completado exitosamente - ID: {self.scan_id}")
            logging.info(f"📄 Resultados: {results_file}")
            
            return summary
            
        except Exception as e:
            logging.error(f"❌ Error en escaneo avanzado: {e}")
            raise
        finally:
            self.release_lock(lock_fd)


def main():
    """Función principal para ejecución directa"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Escaneo avanzado en 2 fases con nmap")
    parser.add_argument("--network", help="Nombre de red configurada")
    parser.add_argument("--cidr", help="CIDR de red (ej: 192.168.1.0/24)")
    
    args = parser.parse_args()
    
    if not args.network and not args.cidr:
        logging.error("Debe especificar --network o --cidr")
        return 1
    
    try:
        scanner = AdvancedScanner(
            network_name=args.network,
            network_cidr=args.cidr
        )
        
        summary = scanner.run_full_scan()
        print(f"✅ Escaneo completado - ID: {scanner.scan_id}")
        return 0
        
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())