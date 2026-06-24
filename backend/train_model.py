import pandas as pd
import numpy  as np
import joblib
import csv
from sklearn.ensemble        import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics         import (
    classification_report, confusion_matrix, accuracy_score
)

# ── Configuration ──────────────────────────────────────────
DATASET_PATH = "dataset_labeled.csv"
MODEL_PATH   = "model.pkl"
FEAT_IMP_CSV = "feature_importance.csv"

FEATURES = [
    "files_created", "files_deleted", "files_modified",
    "files_renamed", "cpu_avg", "cpu_max",
    "ram_avg", "process_count", "alert_count",
]
TARGET = "label"

# ── 1. Chargement du dataset ───────────────────────────────
print("[1] Chargement du dataset...")
df = pd.read_csv(DATASET_PATH)
print(f"    {len(df)} observations, {df[TARGET].nunique()} classes")
print(df[TARGET].value_counts().to_string())

# ── 2. Séparation features / label ────────────────────────
X = df[FEATURES]
y = df[TARGET]

# ── 3. Split 80% entraînement / 20% test ──────────────────
print("\n[2] Split train/test 80/20...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size    = 0.2,
    random_state = 42,
    stratify     = y,   # préserve la proportion des classes
)
print(f"    Train : {len(X_train)} | Test : {len(X_test)}")

# ── 4. Entraînement du Random Forest ──────────────────────
print("\n[3] Entraînement Random Forest...")
model = RandomForestClassifier(
    n_estimators = 100,
    random_state = 42,
    class_weight = "balanced",  # compense le déséquilibre des classes
    max_depth    = 10,           # limite la profondeur → réduit l'overfitting
    min_samples_leaf = 2,        # chaque feuille doit avoir ≥ 2 exemples
)
model.fit(X_train, y_train)
print("    Entraînement terminé.")

# ── 5. Évaluation sur le test set ─────────────────────────
print("\n[4] Évaluation sur le test set...")
y_pred = model.predict(X_test)
acc    = accuracy_score(y_test, y_pred)

print(f"\n    Accuracy : {acc:.2%}")
print("\n    Classification Report :")
print(classification_report(y_test, y_pred,
      target_names=["Normal", "Suspect", "Ransomware"]))

print("    Matrice de confusion :")
print(confusion_matrix(y_test, y_pred))

# ── 6. Sauvegarde du modèle ────────────────────────────────
print(f"\n[5] Sauvegarde → {MODEL_PATH}")
joblib.dump(model, MODEL_PATH)
print("    Modèle sauvegardé.")

# ── 7. Feature Importance ──────────────────────────────────
print(f"\n[6] Feature Importance → {FEAT_IMP_CSV}")
importances = model.feature_importances_
feat_imp    = sorted(
    zip(FEATURES, importances),
    key=lambda x: x[1], reverse=True
)
with open(FEAT_IMP_CSV, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["feature", "importance"])
    for name, score in feat_imp:
        w.writerow([name, round(score, 4)])
        print(f"    {name:<20} {score:.4f}")

print("\n[✔] Pipeline complet terminé.")

# ── 8. Exemple de prédiction temps réel ───────────────────
print("\n[7] Exemple de prédiction...")
sample = pd.DataFrame([{
    "files_created" : 180,
    "files_deleted" : 160,
    "files_modified": 90,
    "files_renamed" : 220,
    "cpu_avg"       : 93.5,
    "cpu_max"       : 98.1,
    "ram_avg"       : 65.2,
    "process_count" : 191,
    "alert_count"   : 10,
}])
pred  = model.predict(sample)[0]
proba = model.predict_proba(sample)[0]
labels = {0: "NORMAL", 1: "SUSPECT", 2: "RANSOMWARE"}
print(f"    Prédiction : {labels[pred]}")
print(f"    Probabilités : Normal={proba[0]:.2%} Suspect={proba[1]:.2%} Ransomware={proba[2]:.2%}")







