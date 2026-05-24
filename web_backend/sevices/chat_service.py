from services.mock_rag import mock_answer


def generate_answer(question: str):
    return mock_answer(question)