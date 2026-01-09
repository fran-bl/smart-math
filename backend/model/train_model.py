import argparse
import pandas as pd
import joblib
import json
from pathlib import Path

from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score,
    balanced_accuracy_score
)

FEATURES = ['accuracy', 'avg_time', 'hints_used']
CLASSES = [0, 1, 2]

def load_data(csv_path):
    df = pd.read_csv(csv_path)
    X = df[FEATURES].copy()
    y = df['label'].astype(int)
    return X, y, df

def main(args):
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Load
    X, y, raw_df = load_data(args.csv)

    # Quick EDA checks (save to json)
    eda = {
        "n_samples": int(len(raw_df)),
        "class_counts": raw_df['label'].value_counts().to_dict(),
        "feature_means": raw_df[FEATURES].mean().to_dict(),
        "feature_std": raw_df[FEATURES].std().to_dict()
    }
    with open(out_dir / "eda.json", "w") as f:
        json.dump(eda, f, indent=2)

    # 2) Train/test split (stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=y
    )

    # 3) Scaling
    scaler = StandardScaler()
    scaler.partial_fit(X_train)
    X_train_scaled = scaler.transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 4) mlr with SGD
    model = SGDClassifier(
        loss='log_loss',
        penalty='l2',
        alpha=0.0001,
        learning_rate='invscaling',
        eta0=0.01,
        power_t=0.25,
        max_iter=1,
        tol=None,
        random_state=args.seed
    )

    model.partial_fit(X_train_scaled, y_train, classes=CLASSES)

    # 5) Evaluation
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)

    report = classification_report(y_test, y_pred, output_dict=True)
    conf = confusion_matrix(y_test, y_pred).tolist()
    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average='macro')
    bal_acc = balanced_accuracy_score(y_test, y_pred)

    # Save evaluation
    eval_summary = {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "balanced_accuracy": bal_acc,
        "confusion_matrix": conf,
        "classification_report": report
    }
    with open(out_dir / "evaluation.json", "w") as f:
        json.dump(eval_summary, f, indent=2)

    # Save predictions (for inspection)
    test_out = X_test.copy()
    test_out['y_true'] = list(y_test)
    test_out['y_pred'] = list(y_pred)
    # append predicted probs per class
    for i in range(y_proba.shape[1]):
        test_out[f'prob_class_{i}'] = y_proba[:, i]
    test_out.to_csv(out_dir / "test_predictions.csv", index=False)

    # 6) Save model + scaler
    joblib.dump(model, out_dir / "model.pkl")
    joblib.dump(scaler, out_dir / "scaler.pkl")

    coef_df = pd.DataFrame(model.coef_, columns=FEATURES)
    coef_df['class'] = CLASSES
    coef_df.to_csv(out_dir / "model_coefficients.csv", index=False)

    print("Training complete. Metrics saved to", out_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, default="train_dataset.csv")
    parser.add_argument("--output_dir", type=str, default="model_output")
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    main(args)
