import mysql.connector
from datetime import datetime
from contextlib import contextmanager

from .config import DB_CONFIG

# ── Gestionnaire de connexion ──────────────────────────────
@contextmanager
def get_connection():
    """Context manager : ouvre une connexion, la ferme proprement."""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        yield conn
    finally:
        if conn and conn.is_connected():
            conn.close()

# ── Insérer un événement fichier ───────────────────────────
def insert_file_event(event_type, file_path, cpu, ram,
                       alert_level="LOW", dest_path=None):
    sql = """
        INSERT INTO file_events
            (timestamp, event_type, file_path, dest_path,
             cpu_percent, ram_percent, alert_level)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (
            datetime.now(), event_type, file_path,
            dest_path, cpu, ram, alert_level
        ))
        conn.commit()
        return cursor.lastrowid   # retourne l'ID inséré

# ── Insérer des métriques système ──────────────────────────
def insert_system_metrics(cpu, ram, ram_used, ram_total, proc_count):
    sql = """
        INSERT INTO system_metrics
            (timestamp, cpu_percent, ram_percent,
             ram_used_mb, ram_total_mb, process_count)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (datetime.now(), cpu, ram,
                             ram_used, ram_total, proc_count))
        conn.commit()

# ── Insérer une alerte ─────────────────────────────────────
def insert_alert(level, rule_name, description,
                  event_id=None, cpu=None, ram=None):
    sql = """
        INSERT INTO alerts
            (timestamp, level, rule_name, description,
             event_id, cpu_at_alert, ram_at_alert)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (datetime.now(), level, rule_name,
                             description, event_id, cpu, ram))
        conn.commit()

# ── Test de connexion ──────────────────────────────────────
if __name__ == "__main__":
    with get_connection() as conn:
        print(f"[✔] Connecté à MySQL — version : {conn.get_server_info()}")