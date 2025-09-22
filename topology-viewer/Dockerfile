FROM nginx:alpine

# Crear directorios necesarios con permisos correctos
RUN mkdir -p /var/cache/nginx/client_temp \
    /var/cache/nginx/proxy_temp \
    /var/cache/nginx/fastcgi_temp \
    /var/cache/nginx/uwsgi_temp \
    /var/cache/nginx/scgi_temp \
    /usr/share/nginx/html/results && \
    chown -R nginx:nginx /var/cache/nginx /usr/share/nginx/html && \
    chmod -R 755 /var/cache/nginx

# Copiar configuración y archivos
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY static/ /usr/share/nginx/html/

# No cambiar a usuario no privilegiado - nginx maneja esto internamente
EXPOSE 80