-- ═══════════════════════════════════════════════════════
-- Projet : Détection précoce des ransomwares par IA
-- Fichier : schema.sql  — Version 1.0
-- ═══════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS ransomware_ai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ransomware_ai;

-- ─────────────────────────────────────────────────────
-- TABLE 1 : file_events
-- Stocke chaque événement fichier détecté par Watchdog
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS file_events (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    timestamp    DATETIME NOT NULL,
    event_type   ENUM('created', 'modified', 'deleted', 'renamed') NOT NULL,
    file_path    VARCHAR(512) NOT NULL,
    dest_path    VARCHAR(512) DEFAULT NULL,  -- uniquement pour renamed
    cpu_percent  FLOAT DEFAULT NULL,
    ram_percent  FLOAT DEFAULT NULL,
    alert_level  ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') DEFAULT 'LOW',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────
-- TABLE 2 : system_metrics
-- Snapshots des métriques CPU / RAM toutes les N sec
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_metrics (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    timestamp      DATETIME NOT NULL,
    cpu_percent    FLOAT NOT NULL,
    ram_percent    FLOAT NOT NULL,
    ram_used_mb    FLOAT DEFAULT NULL,
    ram_total_mb   FLOAT DEFAULT NULL,
    process_count  INT DEFAULT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────
-- TABLE 3 : alerts
-- Alertes générées par le moteur de détection
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    timestamp      DATETIME NOT NULL,
    level          ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL,
    rule_name      VARCHAR(128) NOT NULL,
    description    TEXT,
    event_id       INT DEFAULT NULL,
    cpu_at_alert   FLOAT DEFAULT NULL,
    ram_at_alert   FLOAT DEFAULT NULL,
    resolved       BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES file_events(id) ON DELETE SET NULL
);

-- ─────────────────────────────────────────────────────
-- TABLE 4 : features
-- Vecteurs de features extraits pour l'IA (Semaine 7+)
-- ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS features (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    timestamp           DATETIME NOT NULL,
    window_seconds      INT NOT NULL DEFAULT 60,
    rename_count        INT DEFAULT 0,
    delete_count        INT DEFAULT 0,
    create_count        INT DEFAULT 0,
    modify_count        INT DEFAULT 0,
    avg_cpu             FLOAT DEFAULT NULL,
    max_cpu             FLOAT DEFAULT NULL,
    avg_ram             FLOAT DEFAULT NULL,
    label               TINYINT DEFAULT NULL,  -- 0=normal, 1=ransomware
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────
-- INDEX pour accélérer les requêtes d'investigation
-- ─────────────────────────────────────────────────────
CREATE INDEX idx_file_events_timestamp   ON file_events(timestamp);
CREATE INDEX idx_file_events_type        ON file_events(event_type);
CREATE INDEX idx_file_events_alert       ON file_events(alert_level);
CREATE INDEX idx_alerts_level            ON alerts(level);
CREATE INDEX idx_system_metrics_ts       ON system_metrics(timestamp);