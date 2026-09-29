import argparse
import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from src.config import ROOT, TARGET_REPO, GROQ_MODEL, REQUEST_DELAY
from src.classifier import classify as C
from src.ingestion.db import get_conn

LABELS_CSV = ROOT / "data" / "labeled_comments.csv"
LOG = ROOT / "data" / "eval_log.jsonl"


def main(split):
    conn = get_conn()
    with open(LABELS_CSV, encoding="utf-8-sig", newline="") as f:
        items = [r for r in csv.DictReader(f) if r["label"].strip()]
    if split != "all":
        items = [r for r in items if r["split"] == split]
    if not items:
        raise SystemExit("No labeled rows found for this split. Did you fill the 'label' column?")

    y_true, y_pred, out_rows = [], [], []
    for it in items:
        label = it["label"].strip().lower()
        if label not in C.CATEGORIES:
            raise SystemExit(f"Bad label '{label}' for id {it['id']}. Allowed: {C.CATEGORIES}")
        row = C.fetch_one(conn, TARGET_REPO, it["kind"], int(it["id"]))
        if row is None:
            raise SystemExit(f"Comment {it['kind']} {it['id']} not found in DB")
        try:
            res = C.classify_comment(row)
            pred, reason = res.category, res.reason
        except C.ClassificationError:
            pred, reason = "invalid", ""    # counts as a wrong prediction
        y_true.append(label)
        y_pred.append(pred)
        out_rows.append({"kind": it["kind"], "id": it["id"], "label": label,
                         "pred": pred, "correct": label == pred,
                         "reason": reason, "url": it["url"]})
        time.sleep(REQUEST_DELAY)

    present = [c for c in C.CATEGORIES if c in y_true]
    acc = accuracy_score(y_true, y_pred)
    macro = f1_score(y_true, y_pred, labels=present, average="macro", zero_division=0)
    baseline = Counter(y_true).most_common(1)[0][1] / len(y_true)

    print(f"\nPrompt {C.PROMPT_VERSION} | model {GROQ_MODEL} | split={split} | n={len(y_true)}")
    print(f"Accuracy: {acc:.1%} | Macro-F1: {macro:.3f} | Majority-class baseline: {baseline:.1%}")
    print(f"Invalid outputs (before retry): {C.stats['invalid_json']} / {C.stats['calls']} calls\n")
    print(classification_report(y_true, y_pred, labels=C.CATEGORIES, zero_division=0))
    pd.set_option("display.width", 200)
    cm = confusion_matrix(y_true, y_pred, labels=C.CATEGORIES)
    print(pd.DataFrame(cm, index=[f"true:{c}" for c in C.CATEGORIES],
                       columns=[f"pred:{c}"[:14] for c in C.CATEGORIES]))

    pred_path = ROOT / "data" / f"eval_preds_{C.PROMPT_VERSION}_{split}.csv"
    pd.DataFrame(out_rows).to_csv(pred_path, index=False)
    print(f"\nPer-comment predictions saved to {pred_path} (open it and read the wrong ones)")

    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(), "prompt_version": C.PROMPT_VERSION,
            "model": GROQ_MODEL, "split": split, "n": len(y_true),
            "accuracy": round(acc, 4), "macro_f1": round(macro, 4),
            "majority_baseline": round(baseline, 4),
            "invalid_outputs": C.stats["invalid_json"], "api_calls": C.stats["calls"],
        }) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    main(ap.parse_args().split)