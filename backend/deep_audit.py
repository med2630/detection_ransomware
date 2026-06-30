import os, sys, warnings
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score, permutation_test_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.inspection import permutation_importance

warnings.filterwarnings("ignore")

DATASET = "dataset_labeled.csv"
MODEL   = "model.pkl"
TARGET  = "label"
RANDOM  = 42

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m⚠\033[0m"

issues   = []
warnings_list = []

def sep(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)

def flag(msg):
    issues.append(msg)
    print(f"  {FAIL} {msg}")

def warn(msg):
    warnings_list.append(msg)
    print(f"  {WARN} {msg}")

def ok(msg):
    print(f"  {PASS} {msg}")

# ── 0. Files ────────────────────────────────────────────────────────────────
sep("CHECK 0 — FILES")
for path in [DATASET, MODEL]:
    if not os.path.exists(path):
        print(f"  {FAIL} Missing: {path}")
        sys.exit(1)
    ok(f"Found: {path}")

# ── Load ─────────────────────────────────────────────────────────────────────
df    = pd.read_csv(DATASET)
model = joblib.load(MODEL)
X     = df.drop(columns=[TARGET])
X = X.drop(columns=[c for c in ["timestamp"] if c in X.columns])
y     = df[TARGET]

print(f"\n  Dataset : {len(df)} rows × {len(df.columns)} columns")
print(f"  Classes : {sorted(y.unique())}")

# ── 1. Size ──────────────────────────────────────────────────────────────────
sep("CHECK 1 — DATASET SIZE")
if len(df) < 500:
    flag(f"Only {len(df)} samples — results are unreliable below 500.")
else:
    ok(f"{len(df)} samples (≥ 500).")

# ── 2. Missing values ─────────────────────────────────────────────────────────
sep("CHECK 2 — MISSING VALUES")
n_missing = df.isnull().sum().sum()
if n_missing:
    flag(f"{n_missing} missing values detected.")
else:
    ok("No missing values.")

# ── 3. Duplicate rows ─────────────────────────────────────────────────────────
sep("CHECK 3 — DUPLICATE ROWS")
n_dup = df.duplicated().sum()
if n_dup:
    flag(f"{n_dup} fully duplicate rows.")
else:
    ok("No duplicate rows.")

# ── 4. Label distribution ─────────────────────────────────────────────────────
sep("CHECK 4 — CLASS BALANCE")
counts = y.value_counts()
pcts   = (counts / len(y) * 100).round(1)
for cls in counts.index:
    print(f"  Class {cls}: {counts[cls]} samples ({pcts[cls]}%)")
min_pct = pcts.min()
if min_pct < 10:
    warn(f"Minority class is only {min_pct}% — model may be biased.")
else:
    ok("Class balance looks reasonable.")

# ── 5. Train / Test split (mirroring evaluate_model.py) ──────────────────────
sep("CHECK 5 — TRAIN / TEST SPLIT")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=RANDOM, stratify=y
)
print(f"  Train: {len(X_train)} | Test: {len(X_test)}")
if set(y_train.unique()) != set(y_test.unique()):
    flag("Not all classes appear in both Train and Test.")
else:
    ok("All classes present in Train and Test.")

# ── 6. Data leakage (row overlap) ─────────────────────────────────────────────
sep("CHECK 6 — DATA LEAKAGE (row overlap)")
train_df = X_train.copy(); train_df[TARGET] = y_train.values
test_df  = X_test.copy();  test_df[TARGET]  = y_test.values
shared   = pd.merge(train_df, test_df, how="inner")
if len(shared):
    flag(f"{len(shared)} identical rows found in both Train and Test.")
else:
    ok("No row overlap between Train and Test.")

# ── 7. Conflicting labels ──────────────────────────────────────────────────────
sep("CHECK 7 — CONFLICTING LABELS")
feat_cols  = list(X.columns)
conflicts  = df.groupby(feat_cols)[TARGET].nunique()
n_conflict = (conflicts > 1).sum()
if n_conflict:
    flag(f"{n_conflict} feature vectors map to multiple labels.")
else:
    ok("No conflicting labels.")

# ── 8. Trivially separable features ──────────────────────────────────────────
sep("CHECK 8 — TRIVIALLY SEPARABLE FEATURES")
trivial = []
for col in X.columns:
    per_class = df.groupby(TARGET)[col].apply(set)
    sets = list(per_class)
    if len(sets) > 1:
        union  = sets[0].union(*sets[1:])
        # If one class has a unique range that never overlaps others
        ranges = df.groupby(TARGET)[col].agg(["min","max"])
        for i, (cls_i, row_i) in enumerate(ranges.iterrows()):
            for j, (cls_j, row_j) in enumerate(ranges.iterrows()):
                if i >= j:
                    continue
                if row_i["max"] < row_j["min"] or row_j["max"] < row_i["min"]:
                    trivial.append((col, cls_i, cls_j))
if trivial:
    warn(f"{len(trivial)} feature/class pair(s) are perfectly non-overlapping "
         f"(a single feature perfectly separates those classes).")
    for col, a, b in trivial[:5]:
        print(f"    '{col}' perfectly separates class {a} vs {b}")
else:
    ok("No single feature trivially separates all classes.")

# ── 9. Model performance on held-out test set ─────────────────────────────────
sep("CHECK 9 — MODEL PERFORMANCE (existing model on test set)")
y_pred = model.predict(X_test)
acc    = accuracy_score(y_test, y_pred)
print(f"  Accuracy on 20 % test set : {acc:.4f} ({acc*100:.1f}%)")
print("\n" + classification_report(y_test, y_pred, target_names=[str(c) for c in sorted(y.unique())]))
if acc == 1.0:
    warn("Perfect accuracy on the test set. This is extremely rare with real data — "
         "verify the dataset is not synthetic or trivially separable.")

# ── 10. Stratified k-fold cross-validation (retrain fresh) ────────────────────
sep("CHECK 10 — 5-FOLD CROSS-VALIDATION (fresh model, full dataset)")
cv_model = RandomForestClassifier(n_estimators=100, random_state=RANDOM)
skf      = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM)
cv_scores = cross_val_score(cv_model, X, y, cv=skf, scoring="f1_weighted")
mean_cv   = cv_scores.mean()
std_cv    = cv_scores.std()
print(f"  CV F1 scores : {[round(s,4) for s in cv_scores]}")
print(f"  Mean ± Std   : {mean_cv:.4f} ± {std_cv:.4f}")
if std_cv > 0.05:
    warn(f"High variance across folds (std={std_cv:.4f}) — model may be unstable.")
elif mean_cv == 1.0 and std_cv == 0.0:
    warn("CV also gives perfect scores across every fold — dataset is likely trivial or leaking.")
else:
    ok(f"CV mean F1 = {mean_cv:.4f} (std={std_cv:.4f})")

# ── 11. Permutation / shuffle test ────────────────────────────────────────────
sep("CHECK 11 — PERMUTATION TEST (does the model learn anything real?)")
print("  Running permutation test with 50 shuffles (may take ~30 s) …")
perm_model = RandomForestClassifier(n_estimators=50, random_state=RANDOM)
score, perm_scores, p_value = permutation_test_score(
    perm_model, X, y,
    scoring="f1_weighted",
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM),
    n_permutations=50,
    random_state=RANDOM,
    n_jobs=-1
)
print(f"  Real score            : {score:.4f}")
print(f"  Permuted scores mean  : {perm_scores.mean():.4f} ± {perm_scores.std():.4f}")
print(f"  p-value               : {p_value:.4f}")
if p_value > 0.05:
    flag(f"Permutation p-value = {p_value:.4f} > 0.05 — the model may NOT be learning "
         "real patterns (statistically indistinguishable from random).")
else:
    ok(f"p-value = {p_value:.4f} — the model is learning real patterns.")

# ── 12. Feature importance ────────────────────────────────────────────────────
sep("CHECK 12 — TOP 5 FEATURE IMPORTANCES")
cv_model.fit(X_train, y_train)
imp = pd.Series(cv_model.feature_importances_, index=X.columns).sort_values(ascending=False)
print(f"{'Feature':<30} Importance")
for feat, val in imp.head(5).items():
    bar = "█" * int(val * 50)
    print(f"  {feat:<28} {val:.4f}  {bar}")
top_feat = imp.index[0]
top_val  = imp.iloc[0]
if top_val > 0.5:
    warn(f"Feature '{top_feat}' alone accounts for {top_val*100:.1f}% of importance — "
         "model may be relying on a near-perfect proxy feature.")

# ── 13. Confusion matrix plot ─────────────────────────────────────────────────
sep("CHECK 13 — CONFUSION MATRIX (audit model)")
cm       = confusion_matrix(y_test, y_pred, labels=sorted(y.unique()))
fig, ax  = plt.subplots(figsize=(6,5))
im       = ax.imshow(cm, cmap="Blues")
plt.colorbar(im, ax=ax)
classes  = [str(c) for c in sorted(y.unique())]
ax.set_xticks(range(len(classes))); ax.set_xticklabels(classes)
ax.set_yticks(range(len(classes))); ax.set_yticklabels(classes)
ax.set_xlabel("Predicted label"); ax.set_ylabel("True label")
ax.set_title("Confusion Matrix — Audit")
for i in range(len(classes)):
    for j in range(len(classes)):
        ax.text(j, i, cm[i,j], ha="center", va="center",
                color="white" if cm[i,j] > cm.max()/2 else "black")
plt.tight_layout()
plt.savefig("audit_confusion_matrix.png", dpi=120)
ok("Saved: audit_confusion_matrix.png")

# ── FINAL VERDICT ─────────────────────────────────────────────────────────────
sep("FINAL VERDICT")
print(f"  Issues   : {len(issues)}")
print(f"  Warnings : {len(warnings_list)}")
if issues:
    print(f"\n  {FAIL} PROBLEMS DETECTED — do not trust these results:")
    for i, msg in enumerate(issues, 1):
        print(f"    {i}. {msg}")
if warnings_list:
    print(f"\n  {WARN} WARNINGS — investigate before concluding:")
    for i, msg in enumerate(warnings_list, 1):
        print(f"    {i}. {msg}")
if not issues and not warnings_list:
    print(f"\n  {PASS} No issues or warnings. Results appear credible.")
elif not issues:
    print(f"\n  {WARN} No hard issues, but warnings above deserve attention.")

print("\n" + "=" * 70)
