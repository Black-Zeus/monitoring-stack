FROM nginx:alpine

# Crear directorios para contenido estático
RUN mkdir -p /usr/share/nginx/html/results

# Copiar configuración nginx personalizada
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar archivos estáticos
COPY static/ /usr/share/nginx/html/

# Usuario no privilegiado
RUN adduser -D -s /bin/sh nginx-user && \
    chown -R nginx-user:nginx-user /usr/share/nginx/html

USER nginx-user

EXPOSE 80