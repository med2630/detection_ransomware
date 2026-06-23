import csv
from datetime import datetime, timedelta
from collections import defaultdict

from database import get_connection

WINDOW_SECONDS = 60  # Taille de la fenêtre temporelle
OUTPUT_CSV     = "dataset.csv"

# ── Colonnes du dataset ─────────────────────────────────────
FIELDNAMES = [
    "timestamp", "files_created", "files_deleted",
    "files_modified", "files_renamed",
    "cpu_avg", "cpu_max", "ram_avg",
    "process_count", "alert_count", "label",
]

# ── Extraction des événements fichiers ─────────────────────
def fetch_file_events(conn):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT timestamp, event_type, cpu_percent, ram_percent, alert_level
        FROM   file_events
        ORDER  BY timestamp ASC
    """)
    return cursor.fetchall()

# ── Extraction des métriques système ───────────────────────
def fetch_metrics(conn):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT timestamp, cpu_percent, ram_percent, process_count
        FROM   system_metrics
        ORDER  BY timestamp ASC
    """)
    return cursor.fetchall()

# ── Arrondir un timestamp à la fenêtre de 60s ─────────────
def floor_to_window(ts, window=60):
    """Arrondit un datetime à la fenêtre de N secondes la plus proche."""
    if isinstance(ts, str):
        ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    total_seconds = int(ts.timestamp())
    floored       = (total_seconds // window) * window
    return datetime.fromtimestamp(floored).strftime("%Y-%m-%d %H:%M:%S")

# ── Agrégation par fenêtre temporelle ─────────────────────
def aggregate_events(events):
    """Compte les événements par type dans chaque fenêtre de 60s."""
    windows = defaultdict(lambda: {
        "files_created": 0, "files_deleted": 0,
        "files_modified": 0, "files_renamed": 0,
        "alert_count": 0,
        "cpu_values": [], "ram_values": [],
    })

    for row in events:
        key = floor_to_window(row["timestamp"])
        ev  = row["event_type"]

        if   ev == "created"  : windows[key]["files_created"]  += 1
        elif ev == "deleted"  : windows[key]["files_deleted"]  += 1
        elif ev == "modified" : windows[key]["files_modified"] += 1
        elif ev == "renamed"  : windows[key]["files_renamed"]  += 1

        if row["alert_level"] in ("HIGH", "CRITICAL"):
            windows[key]["alert_count"] += 1

        # "is not None" : un CPU/RAM à 0.0 est une valeur valide (machine
        # idle), pas une valeur absente — un simple "if row[...]:" l'aurait
        # exclue par erreur car 0.0 est falsy en Python.
        if row["cpu_percent"] is not None:
            windows[key]["cpu_values"].append(row["cpu_percent"])
        if row["ram_percent"] is not None:
            windows[key]["ram_values"].append(row["ram_percent"])

    return windows

# ── Agrégation des métriques système par fenêtre ───────────
def aggregate_metrics(metrics):
    """Calcule cpu_avg, cpu_max, ram_avg, process_count par fenêtre."""
    windows = defaultdict(lambda: {
        "cpu_values": [], "ram_values": [], "proc_values": []
    })
    for row in metrics:
        key = floor_to_window(row["timestamp"])
        if row["cpu_percent"] is not None:
            windows[key]["cpu_values"].append(row["cpu_percent"])
        if row["ram_percent"] is not None:
            windows[key]["ram_values"].append(row["ram_percent"])
        if row["process_count"] is not None:
            windows[key]["proc_values"].append(row["process_count"])
    return windows

# ── Utilitaire : moyenne sécurisée ─────────────────────────
def safe_avg(lst):
    return round(sum(lst) / len(lst), 2) if lst else 0.0

def safe_max(lst):
    return round(max(lst), 2) if lst else 0.0

# ── Étiquetage automatique (heuristique provisoire) ─────────
def auto_label(alert_count, cpu_max, files_deleted, files_renamed):
    """
    Label provisoire (0=normal, 1=suspect) basé sur des seuils simples,
    en attendant une relecture/correction manuelle des fenêtres.
    Sans cela, la colonne "label" reste vide et le dataset est inutilisable
    pour entraîner un modèle supervisé (Random Forest, Semaine 7).
    """
    if alert_count > 0:
        return 1
    if cpu_max >= 90:
        return 1
    if files_deleted >= 3 or files_renamed >= 3:
        return 1
    return 0

# ── Construction du dataset ─────────────────────────────────
def build_dataset(event_windows, metric_windows):
    """Fusionne les deux agrégations et construit la liste de lignes CSV."""
    all_keys = sorted(set(event_windows.keys()) | set(metric_windows.keys()))
    rows = []

    for key in all_keys:
        ev = event_windows.get(key, {})
        mt = metric_windows.get(key, {})

        # CPU : on fusionne les valeurs des deux sources
        cpu_vals = ev.get("cpu_values", []) + mt.get("cpu_values", [])
        ram_vals = ev.get("ram_values", []) + mt.get("ram_values", [])

        files_deleted = ev.get("files_deleted", 0)
        files_renamed = ev.get("files_renamed", 0)
        alert_count   = ev.get("alert_count", 0)
        cpu_max       = safe_max(cpu_vals)

        rows.append({
            "timestamp"     : key,
            "files_created" : ev.get("files_created", 0),
            "files_deleted" : files_deleted,
            "files_modified": ev.get("files_modified", 0),
            "files_renamed" : files_renamed,
            "cpu_avg"       : safe_avg(cpu_vals),
            "cpu_max"       : cpu_max,
            "ram_avg"       : safe_avg(ram_vals),
            "process_count" : safe_avg(mt.get("proc_values", [])),
            "alert_count"   : alert_count,
            "label"         : auto_label(alert_count, cpu_max, files_deleted, files_renamed),
        })

    return rows

# ── Insertion en base (table `features`) ───────────────────
def insert_features_to_db(conn, rows, window=WINDOW_SECONDS):
    """Insère les fenêtres agrégées dans la table `features`."""
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO features
            (timestamp, window_seconds, rename_count, delete_count,
             create_count, modify_count, avg_cpu, max_cpu, avg_ram, label)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, [
        (
            row["timestamp"], window,
            row["files_renamed"], row["files_deleted"],
            row["files_created"], row["files_modified"],
            row["cpu_avg"], row["cpu_max"], row["ram_avg"],
            row["label"],
        )
        for row in rows
    ])
    conn.commit()
    print(f"[✔] {cursor.rowcount} ligne(s) insérée(s) dans la table `features`")
    cursor.close()

# ── Export CSV ─────────────────────────────────────────────
def export_csv(rows, output=OUTPUT_CSV):
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[✔] Dataset exporté : {output}  ({len(rows)} fenêtres)")

# ── Validation du dataset ──────────────────────────────────
def validate_dataset(rows):
    """Vérifie la cohérence des données : pas de valeurs négatives, CPU ≤ 100."""
    errors = 0
    for i, row in enumerate(rows):
        for f in ["files_created", "files_deleted", "files_modified", "files_renamed"]:
            if row[f] < 0:
                print(f"[!] Ligne {i} — valeur négative pour {f}")
                errors += 1
        if not (0 <= row["cpu_avg"] <= 100):
            print(f"[!] Ligne {i} — cpu_avg hors plage : {row['cpu_avg']}")
            errors += 1
    if errors == 0:
        print(f"[✔] Validation OK — {len(rows)} lignes, 0 erreur")
    else:
        print(f"[✘] {errors} erreur(s) détectée(s)")

# ── Pipeline principal ─────────────────────────────────────
if __name__ == "__main__":
    conn = get_connection()

    events  = fetch_file_events(conn)
    metrics = fetch_metrics(conn)
    conn.close()

    event_windows  = aggregate_events(events)
    metric_windows = aggregate_metrics(metrics)

    rows = build_dataset(event_windows, metric_windows)
    validate_dataset(rows)
    export_csv(rows)

    conn = get_connection()
    insert_features_to_db(conn, rows)
    conn.close()