import csv
import random
from datetime import datetime, timedelta

INPUT_CSV  = "dataset.csv"
OUTPUT_CSV = "dataset_labeled.csv"

FIELDNAMES = [
    "timestamp", "files_created", "files_deleted",
    "files_modified", "files_renamed",
    "cpu_avg", "cpu_max", "ram_avg",
    "process_count", "alert_count", "label",
]

# ── Règles de labellisation (DOC-33) ─────────────────────────
def assign_label(row):
    """
    Attribue un label à une fenêtre d'observation selon les critères.
    0 = normal | 1 = suspect | 2 = ransomware
    """
    renamed  = int(float(row["files_renamed"]))
    deleted  = int(float(row["files_deleted"]))
    cpu_avg  = float(row["cpu_avg"])
    alerts   = int(float(row["alert_count"]))

    # Label 2 — Comportement ransomware
    if renamed >= 100 or deleted >= 100 or alerts >= 5:
        return 2

    # Label 1 — Comportement suspect
    if (renamed >= 10 or deleted >= 20) and (cpu_avg >= 70 or alerts >= 1):
        return 1

    # Label 0 — Activité normale
    return 0

# ── Lecture + labellisation + écriture ───────────────────────
def label_dataset(input_path=INPUT_CSV, output_path=OUTPUT_CSV):
    with open(input_path, newline="") as fin, \
         open(output_path, "w", newline="") as fout:

        reader  = csv.DictReader(fin)
        writer  = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()

        counts = {0: 0, 1: 0, 2: 0}

        for row in reader:
            row["label"] = assign_label(row)
            counts[row["label"]] += 1
            writer.writerow(row)

    print(f"[✔] Dataset labellisé — {output_path}")
    print(f"    Label 0 (normal)     : {counts[0]}")
    print(f"    Label 1 (suspect)    : {counts[1]}")
    print(f"    Label 2 (ransomware) : {counts[2]}")
    return counts

# ── Générateur de données synthétiques ───────────────────────
def generate_synthetic_data(n_normal=100, n_suspect=50, n_ransom=50, output_path=OUTPUT_CSV):
    """Génère les observations minimales si la base n'en contient pas assez."""
    rows = []
    base = datetime(2026, 6, 9, 10, 0, 0)

    # Observations normales
    for i in range(n_normal):
        ts = base + timedelta(minutes=i)
        rows.append({
            "timestamp"     : ts.strftime("%Y-%m-%d %H:%M:%S"),
            "files_created" : random.randint(0, 5),
            "files_deleted" : random.randint(0, 3),
            "files_modified": random.randint(0, 8),
            "files_renamed" : random.randint(0, 4),
            "cpu_avg"       : round(random.uniform(5, 40), 1),
            "cpu_max"       : round(random.uniform(10, 55), 1),
            "ram_avg"       : round(random.uniform(30, 60), 1),
            "process_count" : random.randint(180, 195),
            "alert_count"   : 0,
            "label"         : 0,
        })

    # Observations suspectes
    for i in range(n_suspect):
        ts = base + timedelta(minutes=n_normal + i)
        rows.append({
            "timestamp"     : ts.strftime("%Y-%m-%d %H:%M:%S"),
            "files_created" : random.randint(10, 40),
            "files_deleted" : random.randint(20, 60),
            "files_modified": random.randint(5, 20),
            "files_renamed" : random.randint(10, 60),
            "cpu_avg"       : round(random.uniform(65, 85), 1),
            "cpu_max"       : round(random.uniform(75, 92), 1),
            "ram_avg"       : round(random.uniform(55, 75), 1),
            "process_count" : random.randint(188, 205),
            "alert_count"   : random.randint(1, 3),
            "label"         : 1,
        })

    # Observations ransomware
    for i in range(n_ransom):
        ts = base + timedelta(minutes=n_normal + n_suspect + i)
        rows.append({
            "timestamp"     : ts.strftime("%Y-%m-%d %H:%M:%S"),
            "files_created" : random.randint(80, 250),
            "files_deleted" : random.randint(100, 300),
            "files_modified": random.randint(50, 120),
            "files_renamed" : random.randint(100, 400),
            "cpu_avg"       : round(random.uniform(80, 99), 1),
            "cpu_max"       : round(random.uniform(90, 100), 1),
            "ram_avg"       : round(random.uniform(58, 82), 1),
            "process_count" : random.randint(190, 210),
            "alert_count"   : random.randint(5, 20),
            "label"         : 2,
        })

    # Écriture du CSV
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✔] {len(rows)} observations générées — {output_path}")
    print(f"    Normal : {n_normal} | Suspect : {n_suspect} | Ransomware : {n_ransom}")

if __name__ == "__main__":
    # Option A : labelliser le dataset.csv existant
    # label_dataset()

    # Option B : générer les données synthétiques minimales
    generate_synthetic_data(n_normal=100, n_suspect=50, n_ransom=50)
