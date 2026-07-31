"""
Service para chatbot.
Gerencia conversação, intenções e ações.
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List

from src.core.llm_client import LLMClient
from src.services.metadata_service import MetadataService
from src.services.estimativa_service import EstimativaService
from src.services.segmentacao_service import SegmentacaoService
from src.models.dto.segmentacao_dto import SegmentacaoCreateDTO
from src.models.regras import RegrasJson

logger = logging.getLogger(__name__)

# Estado de sessão em memória (POC)
_sessions = {}

class ChatService:
    def __init__(self):
        self.llm = LLMClient()
        self.metadata_service = MetadataService()
        self.estimativa_service = EstimativaService()
        self.segmentacao_service = SegmentacaoService()

    def _get_system_prompt(self) -> str:
        return """
Você é um assistente especializado em segmentação de clientes para uma plataforma de CRM.

VOCÊ PODE FAZER:
- listar temas e campos disponíveis
- estimar público de uma regra
- criar segmentações (sempre pedindo confirmação)

REGRAS:
- Sempre peça confirmação antes de criar uma segmentação.
- Use os dados reais do catálogo quando possível.
- Responda de forma clara e direta.
- Se não souber, diga que não tem essa informação.
"""

    def _build_messages(self, user_message: str, historico: Optional[List[Dict]] = None) -> List[Dict]:
        messages = [{"role": "system", "content": self._get_system_prompt()}]
        if historico:
            messages.extend(historico)
        messages.append({"role": "user", "content": user_message})
        return messages

    def _extract_tema(self, text: str) -> Optional[str]:
        """Extrai tema da mensagem (case-insensitive)."""
        # Lista de temas conhecidos (maiúsculas/minúsculas)
        temas = ["comportamento", "demográfico", "financeiro", "produtos", "cadastral"]
        for tema in temas:
            if tema in text.lower():
                return tema.capitalize()  # Retorna com primeira maiúscula
        return None

    def processar_mensagem(self, mensagem: str, session_id: str, historico: Optional[List[Dict]] = None) -> Dict[str, Any]:
        # Verifica ação pendente
        if session_id in _sessions and _sessions[session_id].get("pending_action"):
            return self._processar_confirmacao(mensagem, session_id)

        # Monta mensagens e chama LLM
        messages = self._build_messages(mensagem, historico)
        try:
            llm_response = self.llm.chat_completion(messages)
            resposta_bruta = llm_response.get("content", "")
        except Exception as e:
            logger.error(f"Erro ao chamar LLM: {e}")
            return {"resposta": "Desculpe, tive um problema ao processar sua mensagem. Tente novamente."}

        # Verifica se é um pedido de criação (contém "criar" ou "segment")
        if "criar" in mensagem.lower() or "segment" in mensagem.lower():
            # Tenta extrair regras (simplificado para POC)
            regras = self._extrair_regras(mensagem)
            if regras:
                dados = {
                    "nome": "Segmento via Chat",
                    "objetivo": "AQUISICAO",
                    "owner": "admin",
                    "publico_base_id": "pub_varejo",
                    "regras_json": regras
                }
                _sessions[session_id] = {
                    "pending_action": "criar_segmentacao",
                    "dados": dados
                }
                return {
                    "resposta": f"Vou criar um segmento com as seguintes regras:\n- Nome: {dados['nome']}\n- Objetivo: {dados['objetivo']}\n- Regras: {regras}\nConfirma a criação?",
                    "precisa_confirmacao": True,
                    "session_id": session_id
                }

        # Verifica se é pergunta sobre temas ou campos
        if "tema" in mensagem.lower() or "campo" in mensagem.lower():
            tema = self._extract_tema(mensagem)
            if tema:
                try:
                    campos = self.metadata_service.listar_campos_por_tema(tema)
                    return {
                        "resposta": self._format_campos(campos, tema),
                        "acao": "listar_campos"
                    }
                except Exception as e:
                    return {"resposta": f"Erro ao listar campos: {str(e)}"}
            else:
                temas = self.metadata_service.listar_temas()
                return {
                    "resposta": self._format_temas(temas),
                    "acao": "listar_temas"
                }

        # Verifica se é pedido de estimativa
        if "estimar" in mensagem.lower() or "quantos" in mensagem.lower():
            return {
                "resposta": "Para estimar, preciso que você me informe os critérios. Exemplo: 'estime clientes com renda > 10000'"
            }

        # Se não identificou, usa a resposta do LLM
        return {"resposta": resposta_bruta}

    def _extrair_regras(self, mensagem: str) -> Dict:
        """Extrai regras simples da mensagem (POC)."""
        # Exemplo: renda > 10000
        import re
        match = re.search(r'renda\s*>\s*(\d+)', mensagem, re.IGNORECASE)
        if match:
            valor = int(match.group(1))
            return {
                "publico_base": "pub_varejo",
                "inclusao": {
                    "operator": "AND",
                    "rules": [
                        {"campo_id": "renda_mensal", "op": ">", "value": valor}
                    ]
                }
            }
        # Fallback
        return {
            "publico_base": "pub_varejo",
            "inclusao": {
                "operator": "AND",
                "rules": []
            }
        }

    def _format_temas(self, temas):
        if not temas:
            return "Nenhum tema disponível."
        # Remove duplicatas (caso existam)
        temas_unicos = list({t["tema"] for t in temas})
        return "Temas disponíveis:\n- " + "\n- ".join(sorted(temas_unicos))

    def _format_campos(self, campos, tema):
        if not campos:
            return f"Nenhum campo encontrado para o tema '{tema}'."
        return f"Campos do tema '{tema}':\n" + "\n".join([
            f"- {c['campo_label']} ({c['caracteristica_id']}) - {c['tipo_dado']}"
            for c in campos
        ])

    def _processar_confirmacao(self, mensagem: str, session_id: str) -> Dict:
        session = _sessions.get(session_id, {})
        pending_action = session.get("pending_action")

        if not pending_action:
            return {"resposta": "Nenhuma ação pendente."}

        if mensagem.lower() in ["sim", "confirmar", "ok", "y", "yes"]:
            if pending_action == "criar_segmentacao":
                dados = session.get("dados", {})
                try:
                    # Garantir que 'owner' existe
                    if "owner" not in dados:
                        dados["owner"] = "admin"
                    create_dto = SegmentacaoCreateDTO(**dados)
                    resultado = self.segmentacao_service.criar(create_dto, "admin")
                    _sessions.pop(session_id, None)
                    return {
                        "resposta": f"✅ Segmentação criada com sucesso! ID: {resultado['seg_id']}",
                        "acao": "criar_segmentacao",
                        "regras_json": dados.get("regras_json")
                    }
                except Exception as e:
                    _sessions.pop(session_id, None)
                    return {"resposta": f"❌ Erro ao criar segmentação: {str(e)}"}
        elif mensagem.lower() in ["não", "cancelar", "no", "n"]:
            _sessions.pop(session_id, None)
            return {"resposta": "Ação cancelada."}
        else:
            return {"resposta": "Não entendi. Responda 'sim' para confirmar ou 'não' para cancelar."}