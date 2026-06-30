import pandas as pd
import numpy  as np
import joblib, csv
import matplotlib
matplotlib.use("Agg")   # mode sans écran (serveur Linux)
import matplotlib.pyplot as plt
from sklearn.ensemble        import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics         import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix,
    ConfusionMatrixDisplay
)

# ── Configuration ──────────────────────────────────────────
DATASET_PATH = "dataset_labeled.csv"
MODEL_PATH   = "model.pkl"
FEATURES = [
    "files_created", "files_deleted", "files_modified",
    "files_renamed", "cpu_avg", "cpu_max",
    "ram_avg", "process_count", "alert_count",
]
TARGET   = "label"
CLASSES  = ["Normal", "Suspect", "Ransomware"]

# ── 1. Chargement ──────────────────────────────────────────
df = pd.read_csv(DATASET_PATH)
X  = df[FEATURES]
y  = df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
model = joblib.load(MODEL_PATH)
y_pred = model.predict(X_test)

# ── 2. Métriques complètes ─────────────────────────────────
print("═" * 55)
print("  RAPPORT D'ÉVALUATION — Modèle Random Forest")
print("═" * 55)

acc   = accuracy_score(y_test, y_pred)
prec  = precision_score(y_test, y_pred, average="weighted")
rec   = recall_score(y_test, y_pred, average="weighted")
f1    = f1_score(y_test, y_pred, average="weighted")

print(f"\n  Accuracy  : {acc:.4f}  ({acc:.2%})")
print(f"  Precision : {prec:.4f}  ({prec:.2%})")
print(f"  Recall    : {rec:.4f}  ({rec:.2%})")
print(f"  F1 Score  : {f1:.4f}  ({f1:.2%})")
print()
print(classification_report(y_test, y_pred, target_names=CLASSES))

# Export métriques CSV
with open("metrics_report.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["metric", "value"])
    for name, val in [("accuracy",acc),("precision",prec),
                       ("recall",rec),("f1",f1)]:
        w.writerow([name, round(val, 4)])
print("[✔] metrics_report.csv exporté")

# ── 3. Matrice de confusion ────────────────────────────────
cm = confusion_matrix(y_test, y_pred)
fig, ax = plt.subplots(figsize=(6, 5))
disp = ConfusionMatrixDisplay(cm, display_labels=CLASSES)
disp.plot(ax=ax, cmap="Blues", values_format="d")
ax.set_title("Matrice de Confusion — Random Forest", fontsize=13)
plt.tight_layout()
plt.savefig("confusion_matrix.png", dpi=150)
print("[✔] confusion_matrix.png exporté")

# ── 4. Analyse FP / FN ─────────────────────────────────────
test_df = X_test.copy()
test_df["true_label"] = y_test.values
test_df["pred_label"] = y_pred

fp_ransom = test_df[(test_df["pred_label"] == 2) & (test_df["true_label"] != 2)]
fn_ransom = test_df[(test_df["true_label"] == 2) & (test_df["pred_label"] != 2)]

print(f"\n  Faux Positifs ransomware (FP) : {len(fp_ransom)}")
print(f"  Faux Négatifs ransomware (FN) : {len(fn_ransom)}")

if not fn_ransom.empty:
    print("\n  Détail des FN (attaques manquées) :")
    print(fn_ransom[["files_renamed", "cpu_avg", "alert_count",
                     "true_label", "pred_label"]].to_string())

# ── 5. Comparaison n_estimators ────────────────────────────
print("\n═" * 55)
print("  COMPARAISON n_estimators (50 / 100 / 200)")
print("═" * 55)
results = []
for n in [50, 100, 200]:
    rf = RandomForestClassifier(n_estimators=n, random_state=42,
                                   class_weight="balanced", max_depth=10)
    scores = cross_val_score(rf, X, y, cv=5, scoring="f1_weighted")
    print(f"  n={n:<4}  F1 moyen = {scores.mean():.4f}  (±{scores.std():.4f})")
    results.append((n, scores.mean(), scores.std()))

best_n = max(results, key=lambda x: x[1])
print(f"\n  → Meilleur : n_estimators = {best_n[0]}  (F1 = {best_n[1]:.4f})")

# ── 6. Top 5 features ──────────────────────────────────────
print("\n  TOP 5 FEATURES")
importances = model.feature_importances_
top5 = sorted(zip(FEATURES, importances), key=lambda x: x[1], reverse=True)[:5]
for rank, (feat, score) in enumerate(top5, 1):
    bar = "█" * int(score * 100)
    print(f"  {rank}. {feat:<20} {score:.4f}  {bar}")