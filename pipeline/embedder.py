from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Sequence

import numpy as np


def resolve_device(device: str = "auto") -> str:
    device = (device or "auto").lower()
    if device != "auto":
        return device

    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def _safe_model_slug(model_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "__", model_name).strip("_")


def _sha256_json(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class Embedder:
    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        cache_dir: str | Path = ".align_cache",
        batch_size: int = 32,
    ) -> None:
        self.model_name = model_name
        self.device = resolve_device(device)
        self.cache_dir = Path(cache_dir) / _safe_model_slug(model_name)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "Missing dependency: sentence-transformers. Install with: "
                    "pip install sentence-transformers torch"
                ) from exc
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def _prepare_texts(self, texts: Sequence[str]) -> list[str]:
        # E5 models were trained with query:/passage: prefixes. For symmetric sentence
        # alignment, use passage: for both sides.
        if self.model_name.lower().startswith("intfloat/multilingual-e5"):
            return [f"passage: {t}" for t in texts]
        return list(texts)

    def _cache_path(self, texts: Sequence[str], namespace: str | None = None) -> Path:
        key = _sha256_json(
            {
                "model": self.model_name,
                "namespace": namespace or "",
                "texts": list(texts),
            }
        )
        return self.cache_dir / f"{key}.npy"

    def encode(self, texts: Sequence[str], namespace: str | None = None) -> np.ndarray:
        texts = list(texts)
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)

        cache_path = self._cache_path(texts, namespace=namespace)
        if cache_path.exists():
            return np.load(cache_path)

        prepared = self._prepare_texts(texts)
        emb = self.model.encode(
            prepared,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        tmp_path = cache_path.with_suffix(".tmp.npy")
        np.save(tmp_path, emb)
        tmp_path.replace(cache_path)
        return emb
