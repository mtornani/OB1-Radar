"""NLP helpers leveraging spaCy when available."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Iterable, List

from ..data_sources.base import RecordBatch
from ..config import MLSettings


@dataclass
class GeoEligibility:
    """Represents inferred eligibility evidence."""

    country: str
    score: float
    rationale: str


class GeoEligibilityModel:
    """Wrapper around optional spaCy pipelines for geo extraction."""

    def __init__(self, settings: MLSettings) -> None:
        self.settings = settings

    @cached_property
    def nlp(self):  # pragma: no cover - optional dependency
        if not self.settings.enable_language_models or not self.settings.spacy_model:
            return None
        try:
            import spacy
        except ImportError as exc:  # pragma: no cover - optional import
            raise RuntimeError(
                "spaCy non installato. Installa l'extra 'full' per abilitare l'NLP."
            ) from exc
        return spacy.load(self.settings.spacy_model)

    def infer(self, texts: Iterable[str]) -> List[GeoEligibility]:
        model = self.nlp
        if model is None:
            return []
        results: List[GeoEligibility] = []
        for doc in model.pipe(texts):  # type: ignore[union-attr]
            entities = [ent for ent in doc.ents if ent.label_ in {"GPE", "NORP"}]
            for ent in entities:
                results.append(
                    GeoEligibility(
                        country=ent.text,
                        score=min(1.0, 0.5 + (len(ent.text) / 20)),
                        rationale=f"Entity {ent.text} ({ent.label_})",
                    )
                )
        return results

    def annotate_batch(self, batch: RecordBatch) -> RecordBatch:
        if not batch:
            return []
        texts = [record.get("article.text", "") for record in batch if record.get("article.text")]
        evidence = self.infer(texts)
        avg_score = (
            sum(item.score for item in evidence) / len(evidence)
            if evidence
            else 0.0
        )
        notes = "; ".join(item.rationale for item in evidence)
        annotated: RecordBatch = []
        for record in batch:
            updated = dict(record)
            updated.setdefault("eligibility.geo_score", avg_score)
            updated.setdefault("eligibility.geo_notes", notes)
            annotated.append(updated)
        return annotated


__all__ = ["GeoEligibilityModel", "GeoEligibility"]

