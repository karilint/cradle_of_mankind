FROM nginx:alpine

COPY ./default.conf /etc/nginx/templates/default.conf.template
COPY ./ratelimit.conf /etc/nginx/templates/ratelimit.conf.template
COPY ./certs /certs

RUN mkdir -p /vol/static && \
    chmod 755 /vol/static && \
    mkdir -p /vol/media && \
    chmod 755 /vol/media