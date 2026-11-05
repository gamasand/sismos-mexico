FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

COPY certs/ /usr/local/share/ca-certificates/
RUN update-ca-certificates
COPY dashboard/requirements.txt .
RUN pip install --cert /etc/ssl/certs/ca-certificates.crt --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY dashboard/ ./

CMD ["python", "app.py"]
