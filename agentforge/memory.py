"""Knowledge base with retrieval (RAG), stdlib only (Lesson 03).

TF-IDF + cosine similarity over paragraphs of knowledge/*.md. Real systems use
embeddings and a vector database; the interface (search -> ranked passages) is identical.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

STOPWORDS = set(
    "a an and are as at be by for from has have in is it its of on or that the this to was were will with "
    "you your we our should must any all can not no do does".split()
)


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9_]+", text.lower()) if w not in STOPWORDS and len(w) > 1]


class KnowledgeBase:
    def __init__(self, directory: Path):
        self.chunks: list[dict] = []
        for path in sorted(Path(directory).glob("*.md")):
            for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8")):
                block = block.strip()
                if len(block) < 20:
                    continue
                self.chunks.append({"source": path.name, "text": block, "tf": Counter(tokenize(block))})
        n = len(self.chunks) or 1
        df: Counter = Counter()
        for chunk in self.chunks:
            df.update(chunk["tf"].keys())
        self.idf = {term: math.log((1 + n) / (1 + d)) + 1 for term, d in df.items()}
        for chunk in self.chunks:
            chunk["vec"] = {t: f * self.idf[t] for t, f in chunk["tf"].items()}
            chunk["norm"] = math.sqrt(sum(v * v for v in chunk["vec"].values())) or 1.0

    def search(self, query: str, k: int = 3) -> list[dict]:
        q_tf = Counter(tokenize(query))
        q_vec = {t: f * self.idf[t] for t, f in q_tf.items() if t in self.idf}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        scored = []
        for chunk in self.chunks:
            dot = sum(w * chunk["vec"].get(t, 0.0) for t, w in q_vec.items())
            score = dot / (q_norm * chunk["norm"])
            if score > 0:
                scored.append({"source": chunk["source"], "text": chunk["text"], "score": round(score, 3)})
        scored.sort(key=lambda hit: hit["score"], reverse=True)
        return scored[:k]
