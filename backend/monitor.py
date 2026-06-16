import os
import csv
import time
import json
import logging
import psutil
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── Configuration ──────────────────────────────────────────
WATCH_PATH     = "./watched_folder"
LOG_FILE       = "events.log"
METRICS_FILE   = "system_metrics.json"      # livrable
INVENTORY_FILE = "process_inventory.csv"    # livrable

# Seuils d'alerte (Exercice 4)
THRESHOLDS = {
    "cpu_medium" : 80,
    "cpu_high"   : 95,
    "ram_high"   : 90,
}

# ── Logger ─────────────────────────────────────────────────
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(message)s")

# ── Métriques système (Exercice 1) ─────────────────────────
def get_metrics():
    cpu = psutil.cpu_percent(interval=0.5)   # 0.5s = mesure plus fiable que 0.1
    ram = psutil.virtual_memory()
    return {
        "cpu_percent"  : cpu,
        "ram_percent"  : ram.percent,
        "process_count": len(psutil.pids()),
    }

# ── Process Discovery (Exercice 2) ─────────────────────────
def list_processes():
    """Liste les processus actifs : PID, Nom, Utilisateur, PPID, ligne de commande."""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "username", "ppid", "cmdline"]):
        try:
            info = proc.info
            processes.append({
                "pid"     : info["pid"],
                "name"    : info["name"],
                "username": info.get("username") or "N/A",
                "ppid"    : info.get("ppid"),
                "cmdline" : " ".join(info.get("cmdline") or []),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue   # le processus a disparu ou accès refusé -> on l'ignore
    return processes

def export_inventory():
    """Écrit l'inventaire des processus dans process_inventory.csv (livrable)."""
    processes = list_processes()
    with open(INVENTORY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["pid", "name", "username", "ppid", "cmdline"]
        )
        writer.writeheader()
        writer.writerows(processes)
    print(f"[*] {len(processes)} processus exportés vers {INVENTORY_FILE}")

# ── Calcul du niveau d'alerte (Exercice 4) ─────────────────
def get_alert_level(metrics):
    cpu = metrics["cpu_percent"]
    ram = metrics["ram_percent"]

    if cpu >= THRESHOLDS["cpu_high"] or ram >= THRESHOLDS["ram_high"]:
        return "HIGH"
    elif cpu >= THRESHOLDS["cpu_medium"]:
        return "MEDIUM"
    else:
        return "LOW"

# ── Sauvegarde dans system_metrics.json (livrable) ─────────
def save_metrics_json(event):
    """Ajoute l'événement enrichi au tableau JSON system_metrics.json."""
    try:
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []
    data.append(event)
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ── Enregistrement des événements enrichis (Exercice 3) ────
def log_event(event_type, file_path, extra=None):
    metrics = get_metrics()
    level   = get_alert_level(metrics)

    event = {
        "timestamp"    : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type"   : event_type,
        "file_path"    : file_path,
        "cpu_percent"  : metrics["cpu_percent"],
        "ram_percent"  : metrics["ram_percent"],
        "process_count": metrics["process_count"],
        "alert_level"  : level,
    }
    if extra:
        event.update(extra)

    line = json.dumps(event, ensure_ascii=False)
    print(line)
    logging.info(line)        # journal events.log (format JSON-lines)
    save_metrics_json(event)  # livrable system_metrics.json (tableau JSON)

# ── Handler Watchdog ───────────────────────────────────────
class RansomwareMonitor(FileSystemEventHandler):

    def on_created(self, event):
        if not event.is_directory:
            log_event("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            log_event("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            log_event("deleted", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            log_event("renamed", event.src_path, {"dest_path": event.dest_path})

# ── Entrée principale ──────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(WATCH_PATH, exist_ok=True)   # crée le dossier s'il n'existe pas

    print(f"[*] Surveillance démarrée : {WATCH_PATH}")
    print("[*] Ctrl+C pour arrêter\n")

    # Snapshot initial + inventaire des processus (Exercice 2)
    m = get_metrics()
    print(f"[*] CPU: {m['cpu_percent']}%  |  RAM: {m['ram_percent']}%  "
          f"|  Processus: {m['process_count']}")
    export_inventory()
    print()

    event_handler = RansomwareMonitor()
    observer      = Observer()
    observer.schedule(event_handler, path=WATCH_PATH, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()