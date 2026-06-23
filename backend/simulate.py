import os, time, random, string
from pathlib import Path

TEST_DIR = Path("./watched_folder")
TEST_DIR.mkdir(exist_ok=True)

def random_name(ext=".txt"):
    return "".join(random.choices(string.ascii_lowercase, k=8)) + ext

# ── Scénario 1 : Mass Rename ────────────────────────────────
def simulate_mass_rename(n=150):
    print(f"[*] Mass Rename — {n} fichiers...")
    files = []
    for _ in range(n):
        p = TEST_DIR / random_name()
        p.write_text("data")
        files.append(p)
    time.sleep(1)
    for p in files:
        p.rename(p.with_suffix(".locked"))
    print(f"[✔] {n} renommages effectués — label attendu : 2")

# ── Scénario 2 : Mass Delete ─────────────────────────────────
def simulate_mass_delete(n=120):
    print(f"[*] Mass Delete — {n} fichiers...")
    files = []
    for _ in range(n):
        p = TEST_DIR / random_name()
        p.write_text("data")
        files.append(p)
    time.sleep(1)
    for p in files:
        try: p.unlink()
        except: pass
    print(f"[✔] {n} suppressions effectuées — label attendu : 2")

# ── Scénario 3 : Mass File Creation ──────────────────────────
def simulate_mass_creation(n=200):
    print(f"[*] Mass Creation — {n} fichiers...")
    for _ in range(n):
        p = TEST_DIR / random_name(".enc")
        p.write_bytes(os.urandom(512))   # simule du contenu chiffré
    print(f"[✔] {n} créations effectuées — label attendu : 1 ou 2")

# ── Scénario 4 : High CPU Usage ──────────────────────────────
def simulate_high_cpu(duration=30):
    print(f"[*] High CPU — {duration}s de charge intensive...")
    end = time.time() + duration
    while time.time() < end:
        _ = [x**2 for x in range(100_000)]
    print(f"[✔] Charge CPU maintenue {duration}s — label attendu : 1")

# ── Scénario combiné (label 2 garanti) ───────────────────────
def simulate_full_ransomware(n=100):
    print("[*] Simulation complète ransomware...")
    simulate_mass_creation(n)
    simulate_mass_rename(n)
    simulate_mass_delete(n // 2)
    print("[✔] Simulation complète terminée — label : 2")

if __name__ == "__main__":
    simulate_mass_rename()
    simulate_mass_delete()
    simulate_mass_creation()
    simulate_high_cpu(duration=20)
