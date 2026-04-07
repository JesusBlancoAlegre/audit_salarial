DROP DATABASE IF EXISTS audit_salarial;
CREATE DATABASE IF NOT EXISTS audit_salarial;
USE audit_salarial;
-- ======================================================
-- 1) CATÁLOGOS BÁSICOS
-- ======================================================

-- Tabla de roles
CREATE TABLE rol (
    id            SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(30) NOT NULL,          -- ADMIN, AUDITOR, CLIENTE
    descripcion   VARCHAR(200) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_rol_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de sectores (CNAE)
CREATE TABLE sector (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo        VARCHAR(20) NULL,              -- Código CNAE
    nombre        VARCHAR(120) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sector_nombre (nombre),
    KEY idx_sector_codigo (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dimensiones de análisis
CREATE TABLE dimension (
    id            SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo        VARCHAR(40) NOT NULL,          -- GLOBAL, CATEGORIA, PUESTO, DEPARTAMENTO, CONTRATO, JORNADA, ANTIGUEDAD
    nombre        VARCHAR(80) NOT NULL,
    descripcion   VARCHAR(255) NULL,
    orden         TINYINT UNSIGNED DEFAULT 0,
    activo        TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_dimension_codigo (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================
-- 2) EMPRESAS Y USUARIOS
-- ======================================================

CREATE TABLE empresa (
    id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    cif                VARCHAR(20) NULL,
    nombre             VARCHAR(160) NOT NULL,
    num_trabajadores   INT UNSIGNED NOT NULL DEFAULT 0,
    email_contacto     VARCHAR(190) NULL,
    telefono_contacto  VARCHAR(30) NULL,
    direccion          VARCHAR(200) NULL,
    sector_id          INT UNSIGNED NULL,
    creada_en          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activa             TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_empresa_cif (cif),
    KEY idx_empresa_sector (sector_id),
    KEY idx_empresa_activa (activa),
    CONSTRAINT fk_empresa_sector
        FOREIGN KEY (sector_id) REFERENCES sector(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE usuario (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    rol_id          SMALLINT UNSIGNED NOT NULL,
    empresa_id      BIGINT UNSIGNED NULL,      -- Solo para clientes (rol CLIENTE)
    email           VARCHAR(190) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    nombre          VARCHAR(120) NOT NULL,
    apellidos       VARCHAR(160) NULL,
    telefono        VARCHAR(20) NULL,
    ultimo_login    DATETIME NULL,
    activo          TINYINT(1) NOT NULL DEFAULT 1,
    creado_en       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuario_email (email),
    KEY idx_usuario_rol (rol_id),
    KEY idx_usuario_empresa (empresa_id),
    KEY idx_usuario_activo (activo),
    CONSTRAINT fk_usuario_rol
        FOREIGN KEY (rol_id) REFERENCES rol(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_usuario_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresa(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================
-- 3) AUDITORÍAS Y FICHEROS
-- ======================================================

CREATE TABLE auditoria (
    id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    empresa_id         BIGINT UNSIGNED NOT NULL,
    cliente_usuario_id BIGINT UNSIGNED NULL,    -- Quién subió/solicitó
    auditor_usuario_id BIGINT UNSIGNED NULL,    -- Auditor asignado
    estado             ENUM('PENDIENTE','PROCESANDO','REVISION','COMPLETADA','ERROR','RECHAZADA') NOT NULL DEFAULT 'PENDIENTE',
    nivel_riesgo_global ENUM('BAJO','MEDIO','ALTO','CRITICO') NULL,
    fecha_periodo_ini  DATE NULL,
    fecha_periodo_fin  DATE NULL,
    creada_en          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    procesada_en       DATETIME NULL,
    finalizada_en      DATETIME NULL,
    notas              TEXT NULL,
    PRIMARY KEY (id),
    KEY idx_auditoria_empresa (empresa_id),
    KEY idx_auditoria_estado (estado),
    KEY idx_auditoria_riesgo (nivel_riesgo_global),
    KEY idx_auditoria_auditor (auditor_usuario_id),
    CONSTRAINT fk_auditoria_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresa(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_auditoria_cliente
        FOREIGN KEY (cliente_usuario_id) REFERENCES usuario(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_auditoria_auditor
        FOREIGN KEY (auditor_usuario_id) REFERENCES usuario(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE auditoria_archivo (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    auditoria_id  BIGINT UNSIGNED NOT NULL,
    tipo          ENUM('EXCEL_ORIGEN','WORD_TECNICO','PDF_EJECUTIVO','CSV_PROCESADO','OTRO') NOT NULL,
    ruta          VARCHAR(500) NOT NULL,
    nombre        VARCHAR(255) NOT NULL,
    mime          VARCHAR(120) NULL,
    tam_bytes     BIGINT UNSIGNED NULL,
    hash_sha256   CHAR(64) NULL,
    creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_archivo_auditoria (auditoria_id),
    KEY idx_archivo_tipo (tipo),
    CONSTRAINT fk_archivo_auditoria
        FOREIGN KEY (auditoria_id) REFERENCES auditoria(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE auditoria_evento (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    auditoria_id  BIGINT UNSIGNED NOT NULL,
    usuario_id    BIGINT UNSIGNED NULL,
    evento        VARCHAR(60) NOT NULL,
    estado_anterior VARCHAR(30) NULL,
    estado_nuevo    VARCHAR(30) NULL,
    detalle       VARCHAR(500) NULL,
    ip_origen     VARCHAR(45) NULL,
    creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_evento_auditoria (auditoria_id),
    KEY idx_evento_fecha (creado_en),
    CONSTRAINT fk_evento_auditoria
        FOREIGN KEY (auditoria_id) REFERENCES auditoria(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_evento_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================
-- 4) RESULTADOS (Brechas y scoring)
-- ======================================================

CREATE TABLE resultado (
    id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    auditoria_id          BIGINT UNSIGNED NOT NULL,
    dimension_id          SMALLINT UNSIGNED NOT NULL,
    dimension_valor       VARCHAR(140) NULL,
    
    n_total               INT UNSIGNED NULL,
    n_hombres             INT UNSIGNED NULL,
    n_mujeres             INT UNSIGNED NULL,
    n_otros               INT UNSIGNED NULL DEFAULT 0,
    
    media_hombres         DECIMAL(12,2) NULL,
    media_mujeres         DECIMAL(12,2) NULL,
    mediana_hombres       DECIMAL(12,2) NULL,
    mediana_mujeres       DECIMAL(12,2) NULL,
    salario_minimo        DECIMAL(12,2) NULL,
    salario_maximo        DECIMAL(12,2) NULL,
    desviacion_tipica     DECIMAL(12,2) NULL,
    
    brecha_media_pct      DECIMAL(7,3) NULL,
    brecha_mediana_pct    DECIMAL(7,3) NULL,
    brecha_media_euros    DECIMAL(12,2) NULL,
    
    score_riesgo          DECIMAL(6,3) NULL,
    nivel_riesgo          ENUM('BAJO','MEDIO','ALTO','CRITICO') NULL,
    
    creado_en             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en        DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    KEY idx_resultado_auditoria (auditoria_id),
    KEY idx_resultado_dimension (dimension_id),
    KEY idx_resultado_riesgo (nivel_riesgo),
    KEY idx_resultado_brecha (brecha_media_pct),
    CONSTRAINT fk_resultado_auditoria
        FOREIGN KEY (auditoria_id) REFERENCES auditoria(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_resultado_dimension
        FOREIGN KEY (dimension_id) REFERENCES dimension(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================
-- 5) ANOMALÍAS (Outliers detectados)
-- ======================================================

CREATE TABLE anomalia (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    auditoria_id    BIGINT UNSIGNED NOT NULL,
    dimension_id    SMALLINT UNSIGNED NULL,
    dimension_valor VARCHAR(140) NULL,
    
    metodo          ENUM('IQR','Z_SCORE','DESVIACION','MANUAL') NOT NULL,
    campo           VARCHAR(60) NOT NULL,
    valor           DECIMAL(12,2) NOT NULL,
    umbral_superior DECIMAL(12,2) NULL,
    umbral_inferior DECIMAL(12,2) NULL,
    z_score         DECIMAL(6,3) NULL,
    
    severidad       ENUM('BAJA','MEDIA','ALTA') NOT NULL DEFAULT 'MEDIA',
    descripcion     VARCHAR(500) NULL,
    revisada        TINYINT(1) NOT NULL DEFAULT 0,
    revisada_por    BIGINT UNSIGNED NULL,
    
    creado_en       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    KEY idx_anomalia_auditoria (auditoria_id),
    KEY idx_anomalia_severidad (severidad),
    KEY idx_anomalia_revisada (revisada),
    CONSTRAINT fk_anomalia_auditoria
        FOREIGN KEY (auditoria_id) REFERENCES auditoria(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_anomalia_dimension
        FOREIGN KEY (dimension_id) REFERENCES dimension(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================
-- 6) RECOMENDACIONES
-- ======================================================

CREATE TABLE recomendacion_catalogo (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo          VARCHAR(40) NOT NULL,
    titulo          VARCHAR(160) NOT NULL,
    descripcion     TEXT NOT NULL,
    tipo            ENUM('ORGANIZATIVA','RETRIBUTIVA','FORMACION','PROCESO','LEGAL','OTRA') NOT NULL DEFAULT 'OTRA',
    coste_estimado_default DECIMAL(12,2) NULL,
    impacto_default DECIMAL(5,2) NULL,
    meses_default   TINYINT UNSIGNED NULL,
    activa          TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_reco_codigo (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE auditoria_recomendacion (
    id                       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    auditoria_id             BIGINT UNSIGNED NOT NULL,
    recomendacion_id         INT UNSIGNED NOT NULL,
    
    prioridad                ENUM('BAJA','MEDIA','ALTA','URGENTE') NOT NULL DEFAULT 'MEDIA',
    coste_estimado_eur       DECIMAL(14,2) NULL,
    impacto_reduccion_pct    DECIMAL(7,3) NULL,
    meses_estimados          TINYINT UNSIGNED NULL,
    
    aplicada                 TINYINT(1) NOT NULL DEFAULT 0,
    fecha_aplicacion         DATETIME NULL,
    notas                    VARCHAR(600) NULL,
    
    creado_en                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    UNIQUE KEY uq_auditoria_reco (auditoria_id, recomendacion_id),
    KEY idx_aud_reco_prioridad (prioridad),
    KEY idx_aud_reco_aplicada (aplicada),
    CONSTRAINT fk_aud_reco_auditoria
        FOREIGN KEY (auditoria_id) REFERENCES auditoria(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_aud_reco_catalogo
        FOREIGN KEY (recomendacion_id) REFERENCES recomendacion_catalogo(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================
-- 7) ESTADÍSTICAS SECTORIALES (Comparador anónimo)
-- ======================================================

CREATE TABLE estadisticas_sectoriales (
    id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    sector_id          INT UNSIGNED NOT NULL,
    dimension_id       SMALLINT UNSIGNED NOT NULL,
    dimension_valor    VARCHAR(140) NULL,
    anio               INT NOT NULL,
    
    n_empresas         INT UNSIGNED NULL,
    n_empleados_total  BIGINT UNSIGNED NULL,
    
    salario_medio      DECIMAL(12,2) NULL,
    salario_p25        DECIMAL(12,2) NULL,
    salario_p50        DECIMAL(12,2) NULL,
    salario_p75        DECIMAL(12,2) NULL,
    
    brecha_media_pct   DECIMAL(7,3) NULL,
    brecha_mediana_pct DECIMAL(7,3) NULL,
    brecha_p25_pct     DECIMAL(7,3) NULL,
    brecha_p75_pct     DECIMAL(7,3) NULL,
    
    percentil_empresa_brecha DECIMAL(5,2) NULL,
    
    actualizado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    UNIQUE KEY uq_sector_dim_anio (sector_id, dimension_id, dimension_valor, anio),
    KEY idx_sector_periodo (sector_id, anio),
    KEY idx_sector_brecha (brecha_media_pct),
    CONSTRAINT fk_est_sector
        FOREIGN KEY (sector_id) REFERENCES sector(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_est_dimension
        FOREIGN KEY (dimension_id) REFERENCES dimension(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================
-- 8) ALERTAS Y NOTIFICACIONES
-- ======================================================

CREATE TABLE alerta (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    auditoria_id    BIGINT UNSIGNED NULL,
    empresa_id      BIGINT UNSIGNED NULL,
    usuario_id      BIGINT UNSIGNED NULL,
    tipo            ENUM('RIESGO_CRITICO','BRECHA_ALTA','ANOMALIA','AUDITORIA_VENCIDA','RECOMENDACION','SISTEMA') NOT NULL,
    severidad       ENUM('INFO','WARNING','ERROR','CRITICO') NOT NULL DEFAULT 'INFO',
    canal           ENUM('EMAIL','SISTEMA','AMBOS') NOT NULL DEFAULT 'AMBOS',
    asunto          VARCHAR(190) NULL,
    mensaje         TEXT NOT NULL,
    leida           TINYINT(1) NOT NULL DEFAULT 0,
    enviada         TINYINT(1) NOT NULL DEFAULT 0,
    enviada_en      DATETIME NULL,
    creada_en       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    KEY idx_alerta_no_enviada (enviada, leida),
    KEY idx_alerta_usuario (usuario_id),
    KEY idx_alerta_empresa (empresa_id),
    KEY idx_alerta_tipo (tipo),
    CONSTRAINT fk_alerta_auditoria
        FOREIGN KEY (auditoria_id) REFERENCES auditoria(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_alerta_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresa(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_alerta_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuario(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;