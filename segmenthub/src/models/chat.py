"""
Schemas para o chatbot (S1-BACK-10).
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """Mensagem do chat."""
    role: str  # user / assistant / system
    content: str


class ChatRequest(BaseModel):
    """Requisição para o endpoint de chat."""
    mensagem: str
    historico: Optional[List[ChatMessage]] = None
    contexto: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None  


class ChatResponse(BaseModel):
    """Resposta do chat."""
    resposta: str
    regras_json: Optional[Dict[str, Any]] = None
    acao: Optional[str] = None  # 'estimar', 'criar', 'confirmar', 'listar'
    precisa_confirmacao: bool = False
    acao_pendente: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None