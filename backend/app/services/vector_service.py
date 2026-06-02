"""
Abstract Vector Service interface and factory.

Storage: ChromaDB
Embeddings: EmbeddingServiceFactory (hash / local_bge / API)
"""

from abc import ABC, abstractmethod
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.services.embedding_service import EmbeddingServiceFactory, hash_embedding

settings = get_settings()
logger = logging.getLogger(__name__)

# Backward-compatible alias
_hash_embedding = hash_embedding


class VectorService(ABC):
    @abstractmethod
    async def add_chunks(self, knowledge_base_id: int, chunks: list[dict]) -> list[str]:
        ...

    @abstractmethod
    async def search(self, knowledge_base_id: int, query: str, top_k: int = 5) -> list[dict]:
        ...

    @abstractmethod
    async def delete_document_vectors(self, knowledge_base_id: int, document_id: int) -> None:
        ...

    @abstractmethod
    async def delete_knowledge_base_collection(self, knowledge_base_id: int) -> None:
        ...


def _is_dimension_mismatch_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "dimension" in msg and ("match" in msg or "expect" in msg or "invalid" in msg)


def _raise_if_dimension_mismatch(exc: Exception) -> None:
    if _is_dimension_mismatch_error(exc):
        raise AppError(ErrorCode.VECTOR_DIMENSION_MISMATCH) from exc


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    clean = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif v is not None:
            clean[k] = str(v)
    return clean


def _with_embedding_metadata(metadata: dict[str, Any], embedding_service) -> dict[str, Any]:
    merged = dict(metadata)
    merged.update(embedding_service.metadata_fields())
    return _clean_metadata(merged)


class DeepSeekVectorService(VectorService):
    """DeepSeek embedding + Chroma storage. Reserved — not default."""

    def __init__(self):
        self.api_base = settings.DEEPSEEK_API_BASE.rstrip("/")
        self.api_key = settings.DEEPSEEK_API_KEY
        self.index_prefix = settings.DEEPSEEK_VECTOR_INDEX_PREFIX
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_base,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        client = await self._get_client()
        response = await client.post(
            "/v1/embeddings",
            json={"model": "deepseek-chat", "input": texts},
        )
        if response.status_code != 200:
            logger.error(f"DeepSeek embedding API error: {response.text}")
            raise RuntimeError(f"DeepSeek embedding failed: {response.status_code}")
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def add_chunks(self, knowledge_base_id: int, chunks: list[dict]) -> list[str]:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        if not chunks:
            return []

        texts = [c["content"] for c in chunks]
        embeddings = await self._generate_embeddings(texts)
        collection_name = f"{self.index_prefix}{knowledge_base_id}"
        chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        try:
            collection = chroma_client.get_collection(collection_name)
        except Exception:
            collection = chroma_client.create_collection(collection_name)

        ids, metadatas, documents = [], [], []
        for i, chunk in enumerate(chunks):
            vector_id = f"kb{knowledge_base_id}_doc{chunk.get('document_id')}_chunk{chunk.get('chunk_index', i)}"
            ids.append(vector_id)
            metadatas.append(_clean_metadata(chunk.get("metadata", {})))
            documents.append(chunk["content"])

        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        return ids

    async def search(self, knowledge_base_id: int, query: str, top_k: int = 5) -> list[dict]:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        query_embedding = (await self._generate_embeddings([query]))[0]
        collection_name = f"{self.index_prefix}{knowledge_base_id}"
        chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        try:
            collection = chroma_client.get_collection(collection_name)
        except Exception:
            return []
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        return _format_chroma_results(results)

    async def delete_document_vectors(self, knowledge_base_id: int, document_id: int) -> None:
        await _delete_document_vectors(knowledge_base_id, document_id, self.index_prefix)

    async def delete_knowledge_base_collection(self, knowledge_base_id: int) -> None:
        await _delete_collection(knowledge_base_id, self.index_prefix)


class ChromaVectorService(VectorService):
    """ChromaDB + pluggable embedding service (default: hash)."""

    def __init__(self):
        self.index_prefix = settings.DEEPSEEK_VECTOR_INDEX_PREFIX
        self.embedding_service = EmbeddingServiceFactory.get_service()

    def _client(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        return chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _collection_name(self, knowledge_base_id: int) -> str:
        return f"{self.index_prefix}{knowledge_base_id}"

    async def add_chunks(self, knowledge_base_id: int, chunks: list[dict]) -> list[str]:
        if not chunks:
            return []

        chroma_client = self._client()
        collection_name = self._collection_name(knowledge_base_id)
        try:
            collection = chroma_client.get_collection(collection_name)
        except Exception:
            collection = chroma_client.create_collection(collection_name)

        documents = [c["content"] for c in chunks]
        embeddings = await self.embedding_service.embed_documents(documents)

        ids, metadatas = [], []
        for i, chunk in enumerate(chunks):
            chunk_index = chunk.get("chunk_index", i)
            document_id = chunk.get("document_id")
            vector_id = f"kb{knowledge_base_id}_doc{document_id}_chunk{chunk_index}"
            base_meta = chunk.get("metadata", {})
            ids.append(vector_id)
            metadatas.append(_with_embedding_metadata(base_meta, self.embedding_service))

        try:
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
        except AppError:
            raise
        except Exception as e:
            _raise_if_dimension_mismatch(e)
            raise
        logger.info(f"Added {len(chunks)} chunks to '{collection_name}' via {self.embedding_service.provider_name}")
        return ids

    async def search(self, knowledge_base_id: int, query: str, top_k: int = 5) -> list[dict]:
        chroma_client = self._client()
        collection_name = self._collection_name(knowledge_base_id)
        try:
            collection = chroma_client.get_collection(collection_name)
        except Exception:
            logger.warning(f"Collection '{collection_name}' not found")
            return []

        query_embedding = await self.embedding_service.embed_query(query)
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        except AppError:
            raise
        except Exception as e:
            _raise_if_dimension_mismatch(e)
            raise
        return _format_chroma_results(results)

    async def delete_document_vectors(self, knowledge_base_id: int, document_id: int) -> None:
        await _delete_document_vectors(knowledge_base_id, document_id, self.index_prefix)

    async def delete_knowledge_base_collection(self, knowledge_base_id: int) -> None:
        await _delete_collection(knowledge_base_id, self.index_prefix)


def _format_chroma_results(results: dict) -> list[dict]:
    output = []
    if not results.get("ids") or not results["ids"][0]:
        return output

    for i, vector_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
        distance = results["distances"][0][i] if results.get("distances") else 1.0
        score = 1.0 - min(float(distance), 2.0) / 2.0
        output.append({
            "chunk_id": metadata.get("chunk_id") or metadata.get("id") or metadata.get("chunk_index", i),
            "content": results["documents"][0][i] if results.get("documents") else "",
            "score": round(score, 4),
            "metadata": {
                "document_id": metadata.get("document_id"),
                "knowledge_base_id": metadata.get("knowledge_base_id"),
                "filename": metadata.get("filename"),
                "page_number": metadata.get("page_number"),
                "section_title": metadata.get("section_title"),
                "chunk_index": metadata.get("chunk_index"),
                "embedding_provider": metadata.get("embedding_provider"),
                "embedding_model": metadata.get("embedding_model"),
                "embedding_dim": metadata.get("embedding_dim"),
            },
        })
    return output


async def _delete_document_vectors(knowledge_base_id: int, document_id: int, index_prefix: str) -> None:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    chroma_client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection_name = f"{index_prefix}{knowledge_base_id}"
    try:
        collection = chroma_client.get_collection(collection_name)
        collection.delete(where={"document_id": document_id})
    except Exception as e:
        logger.warning(f"Failed to delete vectors for doc {document_id}: {e}")


async def _delete_collection(knowledge_base_id: int, index_prefix: str) -> None:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    chroma_client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection_name = f"{index_prefix}{knowledge_base_id}"
    try:
        chroma_client.delete_collection(collection_name)
    except Exception as e:
        logger.warning(f"Failed to delete collection '{collection_name}': {e}")


class VectorServiceFactory:
    _instance: VectorService | None = None
    _provider: str | None = None

    @classmethod
    def get_service(cls) -> VectorService:
        current_settings = get_settings()
        provider = current_settings.VECTOR_PROVIDER
        # chroma is legacy alias for chroma_hash
        if provider in ("chroma", "chroma_hash"):
            provider_key = "chroma_hash"
        else:
            provider_key = provider

        if cls._instance is None or cls._provider != provider_key:
            if provider_key == "chroma_hash":
                cls._instance = ChromaVectorService()
            elif provider == "deepseek":
                cls._instance = DeepSeekVectorService()
            else:
                raise ValueError(f"Unsupported VECTOR_PROVIDER: {provider}")
            cls._provider = provider_key
        return cls._instance
