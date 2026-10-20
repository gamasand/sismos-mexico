FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY leer_ejemplo.py .
COPY ejemplo_sismo.json .
COPY comprobar_bd.py .
COPY guardar_ejemplo.py .
COPY consultar_api.py .
COPY guardar_api.py .

CMD ["python", "comprobar_bd.py"]