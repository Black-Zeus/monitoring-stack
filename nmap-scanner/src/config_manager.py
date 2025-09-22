#!/usr/bin/env python3
"""
config_manager.py - Gestor de configuración JSON para escaneos avanzados
Maneja redes, límites, historial y configuración del sistema
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import ipaddress


class ConfigManager:
    #def __init__(self, config_path: str = "/scan_config.json"):
    def __init__(self, config_path: str = "/opt/nmap-scanner/src/scan_config.json"):
        self.config_path = config_path
        self.config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Carga configuración desde archivo JSON"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logging.info(f"Configuración cargada desde {self.config_path}")
            else:
                logging.info("Archivo de configuración no existe, creando configuración por defecto")
                self.create_default_config()
        except Exception as e:
            logging.error(f"Error cargando configuración: {e}")
            self.create_default_config()
    
    def create_default_config(self) -> None:
        """Crea configuración por defecto"""
        self.config = {
            "version": "1.0",
            "created": datetime.utcnow().isoformat() + "Z",
            "networks": {},
            "scan_limits": {
                "max_hosts_per_scan": 254,
                "max_ports_per_host": 65535,
                "phase1_timeout": 1800,
                "phase2_timeout": 3600,
                "concurrent_scans": 1
            },
            "scan_options": {
                "phase1": {
                    "command": "nmap -p- --open -sS --min-rate 5000 -vvv -n -Pn",
                    "description": "Descubrimiento rápido de puertos abiertos"
                },
                "phase2": {
                    "command": "nmap -sCV -p{ports}",
                    "description": "Detección de servicios y versiones en puertos específicos"
                }
            },
            "influxdb": {
                "enabled": True,
                "url": os.getenv("INFLUX_URL", "http://influxdb:8086"),
                "token": os.getenv("INFLUX_TOKEN", "supersecrettoken"),
                "org": os.getenv("INFLUX_ORG", "home"),
                "bucket": os.getenv("INFLUX_BUCKET", "nmap_bucket"),
                "measurement": "advanced_nmap_scan"
            },
            "output": {
                "results_dir": "/results",
                "keep_xml_files": True,
                "max_history_files": 50,
                "history_file": "/results/scan_history.json"
            },
            "logging": {
                "level": "INFO",
                "file": "/var/log/advanced_scan.log",
                "max_size_mb": 10,
                "backup_count": 5
            }
        }
        self.save_config()
    
    def save_config(self) -> None:
        """Guarda configuración a archivo JSON"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logging.info(f"Configuración guardada en {self.config_path}")
        except Exception as e:
            logging.error(f"Error guardando configuración: {e}")
            raise
    
    def add_network(self, name: str, cidr: str, description: str = "") -> bool:
        """Agrega nueva red a la configuración"""
        try:
            # Validar CIDR
            network = ipaddress.ip_network(cidr, strict=False)
            
            if name in self.config["networks"]:
                logging.warning(f"Red {name} ya existe, sobrescribiendo")
            
            self.config["networks"][name] = {
                "cidr": str(network),
                "description": description,
                "added": datetime.utcnow().isoformat() + "Z",
                "last_scan": None,
                "scan_count": 0,
                "enabled": True
            }
            
            self.save_config()
            logging.info(f"Red agregada: {name} ({cidr})")
            return True
            
        except ValueError as e:
            logging.error(f"CIDR inválido {cidr}: {e}")
            return False
        except Exception as e:
            logging.error(f"Error agregando red {name}: {e}")
            return False
    
    def remove_network(self, name: str) -> bool:
        """Elimina red de la configuración"""
        try:
            if name not in self.config["networks"]:
                logging.warning(f"Red {name} no existe")
                return False
            
            del self.config["networks"][name]
            self.save_config()
            logging.info(f"Red eliminada: {name}")
            return True
            
        except Exception as e:
            logging.error(f"Error eliminando red {name}: {e}")
            return False
    
    def get_networks(self) -> Dict[str, Any]:
        """Obtiene todas las redes configuradas"""
        return self.config.get("networks", {})
    
    def get_network(self, name: str) -> Optional[Dict[str, Any]]:
        """Obtiene configuración de una red específica"""
        return self.config.get("networks", {}).get(name)
    
    def enable_network(self, name: str, enabled: bool = True) -> bool:
        """Habilita/deshabilita una red"""
        try:
            if name not in self.config["networks"]:
                logging.error(f"Red {name} no existe")
                return False
            
            self.config["networks"][name]["enabled"] = enabled
            self.save_config()
            status = "habilitada" if enabled else "deshabilitada"
            logging.info(f"Red {name} {status}")
            return True
            
        except Exception as e:
            logging.error(f"Error modificando estado de red {name}: {e}")
            return False
    
    def update_network_scan_info(self, name: str, scan_started: bool = True) -> None:
        """Actualiza información de último escaneo de una red"""
        try:
            if name in self.config["networks"]:
                if scan_started:
                    self.config["networks"][name]["last_scan"] = datetime.utcnow().isoformat() + "Z"
                    self.config["networks"][name]["scan_count"] = self.config["networks"][name].get("scan_count", 0) + 1
                self.save_config()
        except Exception as e:
            logging.error(f"Error actualizando info de escaneo para {name}: {e}")
    
    def get_scan_limits(self) -> Dict[str, Any]:
        """Obtiene límites de escaneo"""
        return self.config.get("scan_limits", {})
    
    def get_scan_options(self) -> Dict[str, Any]:
        """Obtiene opciones de comandos de escaneo"""
        return self.config.get("scan_options", {})
    
    def get_influxdb_config(self) -> Dict[str, Any]:
        """Obtiene configuración de InfluxDB"""
        return self.config.get("influxdb", {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """Obtiene configuración de archivos de salida"""
        return self.config.get("output", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Obtiene configuración de logging"""
        return self.config.get("logging", {})
    
    def update_config_section(self, section: str, data: Dict[str, Any]) -> bool:
        """Actualiza una sección completa de la configuración"""
        try:
            if section in self.config:
                self.config[section].update(data)
                self.save_config()
                logging.info(f"Sección {section} actualizada")
                return True
            else:
                logging.error(f"Sección {section} no existe")
                return False
        except Exception as e:
            logging.error(f"Error actualizando sección {section}: {e}")
            return False
    
    def get_enabled_networks(self) -> Dict[str, Any]:
        """Obtiene solo las redes habilitadas"""
        networks = self.get_networks()
        return {name: config for name, config in networks.items() 
                if config.get("enabled", True)}
    
    def validate_network_cidr(self, cidr: str) -> bool:
        """Valida formato CIDR"""
        try:
            ipaddress.ip_network(cidr, strict=False)
            return True
        except ValueError:
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de la configuración actual"""
        networks = self.get_networks()
        enabled_networks = self.get_enabled_networks()
        
        return {
            "version": self.config.get("version"),
            "total_networks": len(networks),
            "enabled_networks": len(enabled_networks),
            "networks_list": list(networks.keys()),
            "last_modified": datetime.utcnow().isoformat() + "Z",
            "config_file": self.config_path,
            "influxdb_enabled": self.config.get("influxdb", {}).get("enabled", False)
        }
    
    def export_config(self) -> str:
        """Exporta configuración como JSON string"""
        return json.dumps(self.config, indent=2)
    
    def import_config(self, config_json: str) -> bool:
        """Importa configuración desde JSON string"""
        try:
            new_config = json.loads(config_json)
            
            # Validar estructura básica
            required_sections = ["networks", "scan_limits", "scan_options", "influxdb", "output", "logging"]
            for section in required_sections:
                if section not in new_config:
                    logging.error(f"Configuración inválida: falta sección {section}")
                    return False
            
            self.config = new_config
            self.save_config()
            logging.info("Configuración importada exitosamente")
            return True
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON inválido: {e}")
            return False
        except Exception as e:
            logging.error(f"Error importando configuración: {e}")
            return False


# Instancia global del gestor de configuración
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """Obtiene instancia global del gestor de configuración"""
    return config_manager