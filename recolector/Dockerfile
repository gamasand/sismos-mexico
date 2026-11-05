FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

COPY certs/ /usr/local/share/ca-certificates/
RUN update-ca-certificates
COPY recolector/requirements.txt .
RUN pip install --cert /etc/ssl/certs/ca-certificates.crt --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY recolector/*.py ./
COPY recolector/ejemplo_sismo.json ./
COPY tests_backend/ ./tests_backend/

CMD ["python", "guardar_api.py"]
