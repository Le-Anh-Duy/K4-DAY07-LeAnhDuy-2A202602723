from __future__ import annotations

import hashlib
import math
import os
import re
import time
from pathlib import Path

# Vietnamese bi-encoder (PhoBERT-base, 768 dim) trained for asymmetric retrieval
# — a better fit than a paraphrase/STS model for short query -> long policy chunk.
# The local backend remains optional; required checkpoints use MockEmbedder.
LOCAL_EMBEDDING_MODEL = "bkai-foundation-models/vietnamese-bi-encoder"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_PROVIDER_ENV = "EMBEDDING_PROVIDER"


class DailyQuotaExceeded(RuntimeError):
    """Hết hạn mức NGÀY — chờ thêm vô ích, phải sang hôm sau hoặc đổi backend."""


def _retry_delay_seconds(error: Exception, default: float = 62.0) -> float:
    """Lấy retryDelay Google gợi ý trong thông báo 429; không có thì dùng mặc định.

    Hạn mức phút thì chờ rồi chạy tiếp được, còn hạn mức ngày (quotaId chứa
    'PerDay') thì chờ 60 giây chẳng giải quyết gì — phải báo hỏng ngay.
    """
    if "PerDay" in str(error):
        raise DailyQuotaExceeded(
            "Hết hạn mức embedding trong ngày của Gemini free tier (1000 request/ngày). "
            "Chờ sang ngày mới, hoặc chạy lại với --provider local."
        ) from error
    match = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+(?:\.\d+)?)s", str(error))
    return float(match.group(1)) + 2.0 if match else default


class MockEmbedder:
    """Deterministic embedding backend used by tests and default classroom runs."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim
        self._backend_name = "mock embeddings fallback"

    def __call__(self, text: str) -> list[float]:
        digest = hashlib.md5(text.encode()).hexdigest()
        seed = int(digest, 16)
        vector = []
        for _ in range(self.dim):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            vector.append((seed / 0xFFFFFFFF) * 2 - 1)
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class LocalEmbedder:
    """Sentence Transformers-backed local embedder."""

    def __init__(self, model_name: str = LOCAL_EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._backend_name = model_name
        self.model = SentenceTransformer(model_name)
        # PhoBERT was pretrained on word-segmented Vietnamese; skip this and
        # "trả hàng" is read as two unrelated tokens. Not needed for non-PhoBERT models.
        self._segment = None
        if "phobert" in model_name.lower() or "vietnamese-bi-encoder" in model_name.lower():
            from pyvi import ViTokenizer

            self._segment = ViTokenizer.tokenize

    def __call__(self, text: str) -> list[float]:
        if self._segment is not None:
            text = self._segment(text)
        embedding = self.model.encode(text, normalize_embeddings=True)
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return [float(value) for value in embedding]


class OpenAIEmbedder:
    """OpenAI embeddings API-backed embedder."""

    def __init__(self, model_name: str = OPENAI_EMBEDDING_MODEL) -> None:
        from openai import OpenAI

        self.model_name = model_name
        self._backend_name = model_name
        self.client = OpenAI()

    def __call__(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model_name, input=text)
        return [float(value) for value in response.data[0].embedding]


class GeminiEmbedder:
    """Google Gemini embeddings API-backed embedder (google-genai SDK).

    Free-tier alternative to OpenAI for students without an OpenAI key —
    a Gemini API key (aistudio.google.com) has a free quota, no billing card needed.
    """

    DEFAULT_CACHE_PATH = "data/embedding_cache.npz"

    def __init__(
        self,
        model_name: str = GEMINI_EMBEDDING_MODEL,
        dimensions: int = 768,
        cache_path: str | None = DEFAULT_CACHE_PATH,
    ) -> None:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required for GeminiEmbedder")
        self.model_name = model_name
        self.dimensions = dimensions
        self._backend_name = f"{model_name} ({dimensions}d)"
        self.client = genai.Client(api_key=api_key)
        # Cache khoá theo băm của (task_type, nội dung) — gọi lại API là mất tiền
        # và mất 5 phút chờ hạn mức, nên phải giữ lại được qua các lần chạy.
        self._cache: dict[str, list[float]] = {}
        self._cache_path = Path(cache_path) if cache_path else None
        self.load_cache()

    def _key(self, task_type: str, text: str) -> str:
        return hashlib.sha256(f"{task_type}\x00{text}".encode()).hexdigest()

    def load_cache(self) -> int:
        """Nạp embedding đã lưu. Khác model/số chiều thì bỏ qua, không trộn lẫn."""
        if not self._cache_path or not self._cache_path.exists():
            return 0
        import numpy as np

        data = np.load(self._cache_path, allow_pickle=False)
        if str(data["model"]) != self.model_name or int(data["dimensions"]) != self.dimensions:
            return 0
        self._cache = {str(k): v.tolist() for k, v in zip(data["keys"], data["vectors"])}
        return len(self._cache)

    def save_cache(self) -> int:
        """Ghi toàn bộ embedding ra .npz nén."""
        if not self._cache_path or not self._cache:
            return 0
        import numpy as np

        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            self._cache_path,
            keys=np.array(list(self._cache.keys())),
            vectors=np.array(list(self._cache.values()), dtype=np.float32),
            model=np.array(self.model_name),
            dimensions=np.array(self.dimensions),
        )
        return len(self._cache)

    def embed(self, text: str, task_type: str = "RETRIEVAL_QUERY") -> list[float]:
        """Bài này là retrieval bất đối xứng: câu hỏi ngắn tìm điều khoản dài.
        Chunk phải embed bằng RETRIEVAL_DOCUMENT, câu hỏi bằng RETRIEVAL_QUERY.
        """
        from google.genai import types

        key = self._key(task_type, text)
        if key not in self._cache:
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self.dimensions,
                ),
            )
            self._cache[key] = [float(value) for value in response.embeddings[0].values]
        return self._cache[key]

    def embed_document(self, text: str) -> list[float]:
        return self.embed(text, task_type="RETRIEVAL_DOCUMENT")

    def _embed_batch(self, batch: list[str], task_type: str) -> None:
        from google.genai import types

        response = self.client.models.embed_content(
            model=self.model_name,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.dimensions,
            ),
        )
        for text, embedding in zip(batch, response.embeddings):
            self._cache[self._key(task_type, text)] = [float(value) for value in embedding.values]

    def warm(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: int = 90,
        cooldown: float = 62.0,
        verbose: bool = True,
    ) -> None:
        """Nạp sẵn cache theo lô, có điều tiết theo rate limit.

        Free tier tính quota theo SỐ VĂN BẢN chứ không theo số lời gọi: một lô 100
        chunk ăn trọn hạn mức 100 request/phút. Vì vậy phải nghỉ giữa các lô.
        """
        pending = [t for t in dict.fromkeys(texts) if self._key(task_type, t) not in self._cache]
        if not pending:
            if verbose:
                print(f"  {len(set(texts))} embedding đã có sẵn trong cache, không gọi API", flush=True)
            return
        batches = [pending[i : i + batch_size] for i in range(0, len(pending), batch_size)]
        for index, batch in enumerate(batches):
            if index:
                if verbose:
                    print(f"  nghỉ {cooldown:.0f}s cho hạn mức reset...", flush=True)
                time.sleep(cooldown)
            try:
                self._embed_batch(batch, task_type)
            except Exception as error:  # 429 RESOURCE_EXHAUSTED -> chờ rồi thử lại một lần
                delay = _retry_delay_seconds(error, default=cooldown)
                if verbose:
                    print(f"  bị giới hạn tốc độ, chờ {delay:.0f}s rồi thử lại...", flush=True)
                time.sleep(delay)
                self._embed_batch(batch, task_type)
            self.save_cache()  # lưu sau MỖI lô: đứt giữa chừng vẫn không mất công đã làm
            if verbose:
                done = min((index + 1) * batch_size, len(pending))
                print(f"  đã embed {done}/{len(pending)} ({task_type})", flush=True)

    def __call__(self, text: str) -> list[float]:
        return self.embed(text, task_type="RETRIEVAL_QUERY")


_mock_embed = MockEmbedder()
