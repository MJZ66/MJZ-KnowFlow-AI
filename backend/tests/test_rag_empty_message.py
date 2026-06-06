"""RAG empty-retrieval user messaging."""

from app.rag.rag_service import _empty_retrieval_message


def test_empty_message_when_docs_processing():
    msg, reason = _empty_retrieval_message(
        "zh", pending=2, completed=0, raw_count=0, valid_count=0,
    )
    assert reason == "processing"
    assert "处理" in msg


def test_empty_message_when_no_documents():
    msg, reason = _empty_retrieval_message(
        "zh", pending=0, completed=0, raw_count=0, valid_count=0,
    )
    assert reason == "no_documents"
    assert "上传" in msg


def test_empty_message_when_no_match():
    msg, reason = _empty_retrieval_message(
        "zh", pending=0, completed=3, raw_count=0, valid_count=0,
    )
    assert reason == "no_match"
    assert "未找到" in msg
