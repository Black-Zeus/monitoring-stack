FROM nginx:alpine

# Crear directorio para los datos
RUN mkdir -p /usr/share/nginx/html/results

# Configuración nginx básica
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    location / { \
    root /usr/share/nginx/html; \
    index index.html; \
    autoindex on; \
    autoindex_exact_size off; \
    autoindex_localtime on; \
    } \
    location /results/ { \
    alias /usr/share/nginx/html/results/; \
    autoindex on; \
    autoindex_exact_size off; \
    autoindex_localtime on; \
    } \
    }' > /etc/nginx/conf.d/default.conf

EXPOSE 80