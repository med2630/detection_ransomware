import joblib
import psutil
import pandas as pd
import mysql.connector
from flask           import Flask, jsonify, request
from datetime        import datetime, timedelta
from flask_cors       import CORS

app  = Flask(__name__)
CORS(app)   # permet au dashboard HTML d'appeler l'API

# ── Chargement du modèle au démarrage ─────────────────────
MODEL    = joblib.load("backend/model.pkl")
FEATURES = [
    "files_created", "files_deleted", "files_modified",
    "files_renamed", "cpu_avg", "cpu_max",
    "ram_avg", "process_count", "alert_count",
]
from backend.config import DB_CONFIG

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ── GET /health ────────────────────────────────────────────
@app.route("/health")
def health():
    """État du système : modèle, base de données, métriques."""
    try:
        conn = get_db(); conn.close(); db_ok = True
    except: db_ok = False

    return jsonify({
        "status"    : "ok",
        "timestamp" : datetime.now().isoformat(),
        "model"     : "loaded",
        "database"  : "ok" if db_ok else "error",
        "cpu"       : psutil.cpu_percent(interval=0.1),
        "ram"       : psutil.virtual_memory().percent,
    })

# ── GET /metrics ───────────────────────────────────────────
@app.route("/metrics")
def metrics():
    """Métriques système temps réel."""
    ram = psutil.virtual_memory()
    return jsonify({
        "timestamp"    : datetime.now().isoformat(),
        "cpu_percent"  : psutil.cpu_percent(interval=0.1),
        "ram_percent"  : ram.percent,
        "ram_used_mb"  : round(ram.used / 1024**2, 1),
        "process_count": len(psutil.pids()),
    })

# ── GET /alerts ────────────────────────────────────────────
@app.route("/alerts")
def alerts():
    """20 dernières alertes depuis MySQL."""
    limit = int(request.args.get("limit", 20))
    conn  = get_db()
    cur   = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT id, timestamp, level, rule_name, description,
               cpu_at_alert, ram_at_alert, resolved
        FROM alerts
        ORDER BY timestamp DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    # Convertir les datetime en string pour JSON
    for r in rows:
        r["timestamp"] = str(r["timestamp"])
    return jsonify({"alerts": rows, "count": len(rows)})

# ── POST /predict ──────────────────────────────────────────
@app.route("/predict", methods=["POST"])
def predict():
    """
    Reçoit un vecteur de features JSON et retourne la prédiction IA.
    Body JSON attendu : { "files_renamed": 148, "cpu_avg": 91.7, ... }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON requis"}), 400

    try:
        X      = pd.DataFrame([{f: data.get(f, 0) for f in FEATURES}])
        pred   = int(MODEL.predict(X)[0])
        proba  = MODEL.predict_proba(X)[0].tolist()
        labels = {0: "NORMAL", 1: "SUSPECT", 2: "RANSOMWARE"}

        result = {
            "label"          : pred,
            "class"          : labels[pred],
            "proba_normal"   : round(proba[0], 4),
            "proba_suspect"  : round(proba[1], 4),
            "proba_ransomware": round(proba[2], 4),
            "timestamp"      : datetime.now().isoformat(),
        }

        # Si ransomware → insérer dans la table alerts
        if pred == 2:
            _save_alert(result, data)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _save_alert(result, features):
    """Persiste une alerte CRITICAL en MySQL."""
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO alerts (timestamp, level, rule_name, description,
                                cpu_at_alert, ram_at_alert)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            datetime.now(), "CRITICAL", "RandomForest_label2",
            f"Ransomware détecté — proba={result['proba_ransomware']:.2%}",
            features.get("cpu_avg"), features.get("ram_avg")
        ))
        conn.commit(); conn.close()
    except: pass

# ── GET /events (bonus) ────────────────────────────────────
@app.route("/events")
def events():
    """Derniers événements fichiers."""
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT timestamp, event_type, file_path, alert_level, cpu_percent, ram_percent
        FROM file_events ORDER BY timestamp DESC LIMIT 1000
    """)
    rows = cur.fetchall()
    conn.close()
    for r in rows: r["timestamp"] = str(r["timestamp"])
    return jsonify({"events": rows})

if __name__ == "__main__":
    print("[*] Démarrage Flask API — http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)