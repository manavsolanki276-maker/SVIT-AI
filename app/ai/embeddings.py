import os
from typing import List

# Configure cache directories for serverless environments
if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    os.environ.setdefault('HF_HOME', '/tmp/huggingface')
    os.environ.setdefault('TRANSFORMERS_CACHE', '/tmp/huggingface')
    os.environ.setdefault('TORCH_HOME', '/tmp/torch')


class LightweightFallbackEmbeddings:
    """Lightweight serverless embedding fallback using normalized token vectors."""
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._vectorize(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._vectorize(text)

    def _vectorize(self, text: str, dim: int = 384) -> List[float]:
        import hashlib
        import math
        vec = [0.0] * dim
        words = text.lower().split()
        if not words:
            return vec
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
            idx = h % dim
            weight = 1.0 / (math.log(i + 2))
            vec[idx] += weight
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec


def get_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """
    Returns HuggingFace Embeddings model with automatic lightweight fallback for testing and serverless.
    """
    if os.environ.get('FAST_EMBEDDINGS') or os.environ.get('TEST_MODE') or os.environ.get('TESTING'):
        return LightweightFallbackEmbeddings()

    try:
        from flask import current_app
        if current_app and current_app.config.get('TESTING'):
            return LightweightFallbackEmbeddings()
    except Exception:
        pass

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        cache_dir = '/tmp/huggingface' if (os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')) else None
        return HuggingFaceEmbeddings(
            model_name=model_name,
            cache_folder=cache_dir,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    except Exception:
        return LightweightFallbackEmbeddings()