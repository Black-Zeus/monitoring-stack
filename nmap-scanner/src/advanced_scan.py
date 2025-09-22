def do_POST(self):
        """Maneja peticiones POST"""
        logging.info(f"📤 POST request: {self.path} from {self.client_address[0]}")
        
        if self.path == "/scan":
            self._handle_scan()
        elif self.path == "/topology":
            self._handle_topology()
        elif self.path == "/advanced-scan":  # NUEVO ENDPOINT
            self._handle_advanced_scan()
        else:
            logging.warning(f"❌ 404 - POST path not found: {self.path}")
            self._send_404()

    def _handle_advanced_scan(self):
        """Endpoint para escaneo avanzado en 2 fases"""
        logging.info("🎯 Advanced scan solicitado")
        try:
            # Leer datos JSON si están presentes
            network = None
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    network = data.get('network')
                    logging.info(f"🌐 Red especificada para advanced scan: {network}")
                except json.JSONDecodeError as e:
                    logging.warning(f"⚠️ Error parsing JSON para advanced scan: {e}")
            
            # Configurar variable de entorno si se especificó red
            if network:
                os.environ["TARGET_NETWORK"] = network
                logging.info(f"🎯 Configurada red para advanced scan: {network}")
            
            # Ejecutar escaneo avanzado
            logging.info("🚀 Iniciando escaneo avanzado en 2 fases...")
            subprocess.Popen([
                "/usr/local/bin/python",
                "/opt/nmap-scanner/src/advanced_scan.py"
            ])
            
            response = {
                "status": "advanced_scan_started",
                "network": network or os.getenv("TARGET_NETWORK"),
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Escaneo avanzado iniciado (Fase 1: Descubrimiento rápido, Fase 2: Detalle)",
                "phases": ["discovery", "detailed_scan"]
            }
            logging.info(f"✅ Advanced scan iniciado: {response}")
            self._send_json_response(202, response)
            
        except Exception as e:
            logging.error(f"❌ Error en advanced scan: {e}")
            self._send_json_response(500, {"error": str(e)})