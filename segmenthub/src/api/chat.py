"""
Endpoint do chatbot.
"""

from fastapi import APIRouter, Depends, HTTPException
from src.models.chat import ChatRequest, ChatResponse
from src.services.chat_service import ChatService
from src.core.security import require_perfil
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/mensagem", response_model=dict)
async def enviar_mensagem(
    request: ChatRequest,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Envia uma mensagem para o chatbot e recebe a resposta.
    """
    service = ChatService()
    
    # Gera um session_id (simples para POC)
    session_id = request.session_id or str(uuid.uuid4())
    
    historico = None
    if request.historico:
        historico = [msg.model_dump() for msg in request.historico]
    
    try:
        resultado = service.processar_mensagem(
            mensagem=request.mensagem,
            session_id=session_id,
            historico=historico,
        )
        return {
            "resposta": resultado.get("resposta", ""),
            "regras_json": resultado.get("regras_json"),
            "acao": resultado.get("acao"),
            "precisa_confirmacao": resultado.get("precisa_confirmacao", False),
            "session_id": session_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no chat: {str(e)}")