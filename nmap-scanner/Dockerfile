FROM python:3.11-slim

# Instalar herramientas de red necesarias
RUN apt-get update && apt-get install -y \
    nmap \
    traceroute \
    iputils-ping \
    net-tools \
    iproute2 \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /opt/nmap-scanner

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar scripts
COPY scan.py .
COPY topology_mapper.py .
COPY ntopng_collector.py .
COPY entrypoint.sh .

# Hacer ejecutables los scripts
RUN chmod +x entrypoint.sh scan.py topology_mapper.py ntopng_collector.py

# Crear directorios necesarios
RUN mkdir -p /results /var/log

# Exponer puerto para API HTTP
EXPOSE 8080

# Punto de entrada
ENTRYPOINT ["/opt/nmap-scanner/entrypoint.sh"]