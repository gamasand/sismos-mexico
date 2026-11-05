-- Migración aditiva para nuevas instalaciones. shared/esquema.py hace lo
-- mismo al arrancar el recolector sobre volúmenes existentes.
CREATE TABLE IF NOT EXISTS ventanas_cargas (
    ventana_key VARCHAR(32) PRIMARY KEY,
    inicio_utc DATETIME(3), fin_utc DATETIME(3),
    ultima_consulta_utc DATETIME(3), ultimo_intento_utc DATETIME(3) NOT NULL,
    total INT UNSIGNED NOT NULL DEFAULT 0,
    estado VARCHAR(16) NOT NULL, error TEXT, firma_config CHAR(64),
    parametros_json JSON,
    solicitud_inicio_utc DATETIME(3), solicitud_fin_utc DATETIME(3)
);

CREATE TABLE IF NOT EXISTS ventana_sismos (
    ventana_key VARCHAR(32) NOT NULL,
    sismo_id VARCHAR(50) NOT NULL,
    PRIMARY KEY (ventana_key, sismo_id),
    CONSTRAINT fk_ventana_carga FOREIGN KEY (ventana_key)
        REFERENCES ventanas_cargas (ventana_key),
    CONSTRAINT fk_ventana_sismo FOREIGN KEY (sismo_id) REFERENCES sismos (id)
);
