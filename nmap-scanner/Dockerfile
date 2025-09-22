FROM python:3.11-slim

# Instalar herramientas específicas para nmap scanning
RUN apt-get update && apt-get install -y \
    nmap \
    traceroute \
    iputils-ping \
    net-tools \
    iproute2 \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/nmap-scanner

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/
COPY scripts/ ./scripts/

# Hacer ejecutables los scripts
RUN chmod +x scripts/entrypoint.sh src/scan.py src/topology_mapper.py

# Crear directorios necesarios
RUN mkdir -p /results /var/log

# Exponer puerto API
EXPOSE 8080

# Usar entrypoint específico
ENTRYPOINT ["/opt/nmap-scanner/scripts/entrypoint.sh"]