CREATE TABLE IF NOT EXISTS sismos (
    id VARCHAR(50) PRIMARY KEY,
    fecha_utc DATETIME(3) NOT NULL,
    lugar VARCHAR(255),
    magnitud DOUBLE,
    tipo_magnitud VARCHAR(20),
    longitud DOUBLE NOT NULL,
    latitud DOUBLE NOT NULL,
    profundidad_km DOUBLE NOT NULL,
    INDEX idx_fecha (fecha_utc)
);






