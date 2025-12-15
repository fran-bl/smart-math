import numpy as np
import pandas as pd
import argparse
import random

def heuristic(acc, avg_time, hints):
    if acc >= 0.9 and avg_time <= 5 and hints <= 1: return 2
    if 0.6 <= acc <= 0.75 and 7 <= avg_time <= 10 and 2 <= hints <= 3: return 1
    if acc <= 0.4 and avg_time >= 13 and hints >= 4: return 0
    elif acc < 0.4 and avg_time < 6 and hints <= 1: return 1
    else: return None

def generate(n=5000, seed=42, balance=False):
    np.random.seed(seed)
    random.seed(seed)

    rows = []
    while len(rows) < n:
        # Tocnost sampleana iz beta distribucije
        acc = np.clip(np.random.beta(a=2.0, b=2.0), 0.0, 1.0)

        # Avg time sampleano iz normalne distribucije s tim da acc utjece na mean (veci acc korelira s kracim vremenom odgovaranja)
        avg_time = np.abs(np.random.normal(loc=10.0 + (0.5 - acc) * 10.0, scale=5.0))
        avg_time = float(np.clip(avg_time, 1.0, 120.0))

        # Hintovi sampleani iz Poissonove distribucije (najcesce manje vrijednosti) s tim da acc utjece na mean (veci acc korelira s manjim brojem hintova)
        hints = np.random.poisson(lam=max(0.1, 1.5 + (0.5 - acc) * 3.0))
        hints = int(min(hints, 10)) # cappano na 10 da nema velikih outliera

        label = heuristic(acc, avg_time, hints)

        if label is None: continue

        rows.append({
            'accuracy': float(acc),
            'avg_time': float(avg_time),
            'hints_used': int(hints),
            'label': int(label)
        })

    df = pd.DataFrame(rows)
    # Ako zelimo balansirati primjere po klasama oversamplamo klase s manjim brojem primjera da se izjednace sa onom koja ima najvise
    if balance:
        classes = df['label'].unique().tolist()
        max_count = df['label'].value_counts().max()
        samples = []

        for c in classes:
            dfc = df[df['label'] == c]
            if len(dfc) < max_count:
                dfc_up = dfc.sample(max_count, replace=True, random_state=seed)
                samples.append(dfc_up)
            else:
                samples.append(dfc)

        df = pd.concat(samples).sample(frac=1, random_state=seed).reset_index(drop=True)

    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=5000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--balance', action='store_true')
    args = parser.parse_args()

    df = generate(n=args.n, seed=args.seed, balance=args.balance)
    df.to_csv('train_dataset.csv', index=False)

    print(df['label'].value_counts(normalize=False))