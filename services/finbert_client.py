from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from transformers import AutoModelForSequenceClassification, AutoTokenizer, TextClassificationPipeline


FINBERT_MODEL_NAME = "ProsusAI/finbert"


@dataclass(frozen=True)
class FinBertResult:
    text: str
    label: str
    score: float
    numeric_score: float


class FinBertClient:
    def __init__(self, model_name: str = FINBERT_MODEL_NAME) -> None:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self._pipeline = TextClassificationPipeline(
            model=model,
            tokenizer=tokenizer,
            return_all_scores=False,
            truncation=True,
            padding=True,
        )

    @staticmethod
    def _label_to_numeric(label: str) -> float:
        normalized = label.lower()
        if "positive" in normalized:
            return 100.0
        if "negative" in normalized:
            return 0.0
        return 50.0

    def score_texts(self, texts: Iterable[str]) -> List[FinBertResult]:
        cleaned = [t for t in (text.strip() for text in texts) if t]
        if not cleaned:
            return []

        outputs = self._pipeline(list(cleaned))
        results: List[FinBertResult] = []
        for text, out in zip(cleaned, outputs):
            label = out["label"]
            score = float(out["score"])
            numeric = self._label_to_numeric(label)
            results.append(
                FinBertResult(
                    text=text,
                    label=label,
                    score=score,
                    numeric_score=numeric,
                )
            )
        return results

    def average_numeric_score(self, texts: Iterable[str]) -> float:
        results = self.score_texts(texts)
        if not results:
            return 50.0
        return float(sum(r.numeric_score for r in results) / len(results))
