from pydantic import BaseModel
from typing import List


class ChatRequest(BaseModel):
    question: str


class Reference(BaseModel):
    title: str
    content: str


class ChatResponse(BaseModel):
    answer: str
    references: List[Reference]