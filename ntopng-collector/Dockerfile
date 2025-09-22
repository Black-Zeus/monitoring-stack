FROM python:3.11-slim

# Instalar dependencias mínimas
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ntopng-collector

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/

# Hacer ejecutable el script
RUN chmod +x src/ntopng_collector.py

# Usuario no privilegiado
RUN useradd -m -u 1001 collector
USER collector

# Comando directo (sin cron)
CMD ["python3", "src/ntopng_collector.py"]