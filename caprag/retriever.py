from collections.abc import Iterable
from typing import Any

from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_classic.storage import LocalFileStore
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from caprag.config import settings

_retriever = None
_vectorstore = None
_docstore = None


CHROMA_BATCH_LIMIT = 100


class BatchedChroma(Chroma):
    """Chroma subclass that auto-splits add_texts into sub-batches
    to stay within SQLite's MAX_VARIABLE_NUMBER limit."""

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        texts_list = list(texts)
        if not texts_list:
            return []

        if len(texts_list) <= CHROMA_BATCH_LIMIT:
            return super().add_texts(texts_list, metadatas=metadatas, ids=ids, **kwargs)

        all_ids: list[str] = []
        for i in range(0, len(texts_list), CHROMA_BATCH_LIMIT):
            batch_texts = texts_list[i : i + CHROMA_BATCH_LIMIT]
            batch_metadatas = metadatas[i : i + CHROMA_BATCH_LIMIT] if metadatas else None
            batch_ids = ids[i : i + CHROMA_BATCH_LIMIT] if ids else None
            result = super().add_texts(
                batch_texts, metadatas=batch_metadatas, ids=batch_ids, **kwargs
            )
            all_ids.extend(result)
        return all_ids


def get_vectorstore() -> BatchedChroma:
    global _vectorstore
    if _vectorstore is None:
        embeddings = OpenAIEmbeddings(model=settings.embedding_model)
        _vectorstore = BatchedChroma(
            collection_name="caprag",
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
        )
    return _vectorstore


def get_docstore() -> LocalFileStore:
    global _docstore
    if _docstore is None:
        _docstore = LocalFileStore(root_path=settings.docstore_dir)
    return _docstore


def get_retriever() -> ParentDocumentRetriever:
    global _retriever
    if _retriever is not None:
        return _retriever

    vectorstore = get_vectorstore()

    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200, chunk_overlap=40, add_start_index=True
    )
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, chunk_overlap=400, add_start_index=True
    )

    _retriever = ParentDocumentRetriever(
        vectorstore=vectorstore,
        byte_store=get_docstore(),
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )
    return _retriever
