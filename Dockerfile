FROM python:3

WORKDIR /app

COPY . /app

EXPOSE 80

VOLUME [ "/app/etc" ]

CMD ["python3", "main.py"]