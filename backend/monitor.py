import time
import json
import logging
import threading
import psutil
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from database import insert_file_event, insert_alert, insert_system_metrics

# ── Configuration ──────────────────────────────────────────
WATCH_PATH = "backend/watched_folder"
LOG_FILE   = "backend/events.log"
THRESHOLDS = {"cpu_medium": 80, "cpu_high": 95, "ram_high": 90}
METRICS_INTERVAL = 15  # secondes entre deux collectes système

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(message)s")

def get_metrics():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    return cpu, ram.percent

# ── Collecte périodique des métriques système ──────────────
def collect_system_metrics(interval=METRICS_INTERVAL):
    while True:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        try:
            insert_system_metrics(
                cpu, ram.percent,
                ram.used // (1024 * 1024), ram.total // (1024 * 1024),
                len(psutil.pids()),
            )
        except Exception as e:
            print(f"[!] Erreur MySQL (system_metrics) : {e}")
        time.sleep(interval)

def get_alert_level(cpu, ram):
    if cpu >= THRESHOLDS["cpu_high"] or ram >= THRESHOLDS["ram_high"]:
        return "HIGH"
    elif cpu >= THRESHOLDS["cpu_medium"]:
        return "MEDIUM"
    return "LOW"

def log_event(event_type, file_path, dest_path=None):
    cpu, ram  = get_metrics()
    level     = get_alert_level(cpu, ram)

    # 1. Log JSON fichier
    entry = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             "event_type": event_type, "file_path": file_path,
             "dest_path": dest_path, "cpu_percent": cpu,
             "ram_percent": ram, "alert_level": level}
    line = json.dumps(entry, ensure_ascii=False)
    print(line)
    logging.info(line)

    # 2. Insertion MySQL
    try:
        event_id = insert_file_event(event_type, file_path,
                                      cpu, ram, level, dest_path)
        # 3. Si HIGH ou CRITICAL → insérer aussi dans alerts
        if level in ("HIGH", "CRITICAL"):
            insert_alert(
                level     = level,
                rule_name = f"threshold_{event_type}",
                description= f"Seuil CPU/RAM dépassé lors d'un {event_type} sur {file_path}",
                event_id  = event_id,
                cpu       = cpu,
                ram       = ram,
            )
    except Exception as e:
        print(f"[!] Erreur MySQL : {e}")   # L'agent continue même si la DB est down

# ── Handler ────────────────────────────────────────────────
class RansomwareMonitor(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory: log_event("created", event.src_path)
    def on_modified(self, event):
        if not event.is_directory: log_event("modified", event.src_path)
    def on_deleted(self, event):
        if not event.is_directory: log_event("deleted", event.src_path)
    def on_moved(self, event):
        if not event.is_directory:
            log_event("renamed", event.src_path, event.dest_path)

# ── Main ───────────────────────────────────────────────────
if __name__ == "__main__":
    metrics_thread = threading.Thread(target=collect_system_metrics, daemon=True)
    metrics_thread.start()

    observer = Observer()
    observer.schedule(RansomwareMonitor(), path=WATCH_PATH, recursive=True)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()