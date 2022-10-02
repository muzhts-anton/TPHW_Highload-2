FROM python:3.8-slim

RUN mkdir /var/www
RUN mkdir /var/www/html

COPY httpd.conf /etc
COPY tests /var/www/html

WORKDIR /usr/src/app

COPY . /usr/src/app
EXPOSE 80

CMD ["python3", "main.py"]