import argparse
import pandas as pd
import joblib
import json
from pathlib import Path

from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score,
    balanced_accuracy_score
)

def load_data(csv_path):
    df = pd.read_csv(csv_path)
    X = df[['accuracy', 'avg_time', 'hints_used']].copy()
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
        "feature_means": raw_df[['accuracy','avg_time','hints_used']].mean().to_dict(),
        "feature_std": raw_df[['accuracy','avg_time','hints_used']].std().to_dict()
    }
    with open(out_dir / "eda.json", "w") as f:
        json.dump(eda, f, indent=2)

    # 2) Train/test split (stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=y
    )

    # 3) Pipeline: scaler + logistic regression
    pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(solver='lbfgs', max_iter=1000, class_weight='balanced'))
    ])

    # 4) Grid search for C (regularization strength) - mogla bih samo staviti na C = 1.0
    param_grid = {
        'clf__C': [0.01, 0.1, 1.0, 5.0, 10.0],
        'clf__penalty': ['l2']
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.seed)
    grid = GridSearchCV(pipe, param_grid, cv=cv, scoring='f1_macro', n_jobs=-1, verbose=1)
    grid.fit(X_train, y_train)

    # Save CV results and best params
    pd.DataFrame(grid.cv_results_).to_csv(out_dir / "cv_results.csv", index=False)
    with open(out_dir / "best_params.json", "w") as f:
        json.dump(grid.best_params_, f, indent=2)

    # 5) Evaluate on test set
    best_model = grid.best_estimator_
    y_pred = best_model.predict(X_test)
    y_proba = best_model.predict_proba(X_test)

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
    joblib.dump(best_model, out_dir / "mlr_model.pkl")
    print("Saved model to:", out_dir / "mlr_model.pkl")

    # 7) Inspect coefficients (after scaler, classifier is inside pipeline)
    clf = best_model.named_steps['clf']
    scaler = best_model.named_steps['scaler']
    coef = clf.coef_  # shape (n_classes, n_features)
    features = ['accuracy','avg_time','hints_used']
    coef_df = pd.DataFrame(coef, columns=features)
    coef_df['class'] = range(coef_df.shape[0])
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
