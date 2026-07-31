"""
Service para administração de catálogo (governança).
Gerencia flags, histórico e regras de negócio.
"""

import uuid
from typing import List, Dict, Optional, Any
from fastapi import HTTPException

from src.models.dto.metadata_admin_dto import (
    FlagUpdateDTO,
    StatusUpdateDTO,
    CampoAdminDTO,
    CampoAdminDetalheDTO,
    HistoricoGovernancaDTO,
)
from src.repositories.metadata_admin_repository import MetadataAdminRepository
from src.core.security import get_current_user


class MetadataAdminService:
    """Serviço para governança de catálogo."""

    def __init__(self):
        self.repository = MetadataAdminRepository()

    def _gerar_hist_id(self) -> str:
        return f"hist_{uuid.uuid4().hex[:12]}"

    def _determinar_sistema_alvo(self, flag: str) -> str:
        """Deriva sistema_alvo com base na flag."""
        mapping = {
            "usavel_em_visao360": "s2",
            "usavel_em_peca": "s3",
            "bloco_visao360": "s2",
            "ativo": "global",
        }
        return mapping.get(flag, "global")

    def _determinar_acao(self, flag: str, de: Any, para: Any) -> str:
        """Determina a ação com base na mudança de valor."""
        if flag == "bloco_visao360":
            return "alterou_bloco"
        # Para booleanos: false->true = liberou, true->false = retirou
        if de is False and para is True:
            return "liberou"
        if de is True and para is False:
            return "retirou"
        return "alterou"  # fallback

    def _gravar_historico(
        self,
        caracteristica_id: str,
        campo_label: str,
        flag: str,
        de: Any,
        para: Any,
        alterado_por: str,
    ) -> None:
        """Grava um registro de histórico para uma flag alterada."""
        sistema_alvo = self._determinar_sistema_alvo(flag)
        acao = self._determinar_acao(flag, de, para)

        # Converte valores para string (para compatibilidade)
        valor_anterior = str(de) if de is not None else None
        valor_novo = str(para) if para is not None else None

        dados = {
            "hist_id": self._gerar_hist_id(),
            "caracteristica_id": caracteristica_id,
            "campo_label": campo_label,
            "flag_alterada": flag,
            "sistema_alvo": sistema_alvo,
            "valor_anterior": valor_anterior,
            "valor_novo": valor_novo,
            "acao": acao,
            "alterado_por": alterado_por,
        }
        self.repository.inserir_historico(dados)

    # ============================================================
    # CAMPOS
    # ============================================================

    def listar_campos(
        self,
        tema: Optional[str] = None,
        sistema: Optional[str] = None,
        status: Optional[str] = None,
        busca: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Dict:
        """Lista características com paginação e filtros."""
        offset = (page - 1) * size
        dados = self.repository.listar_campos(
            tema=tema, sistema=sistema, status=status, busca=busca,
            limit=size, offset=offset,
        )
        total = self.repository.contar_campos(tema=tema, sistema=sistema, status=status, busca=busca)
        total_pages = (total + size - 1) // size if total > 0 else 0

        # Converte para DTO
        itens = [
            CampoAdminDTO(
                caracteristica_id=row["caracteristica_id"],
                campo_label=row["campo_label"],
                tema=row["tema"],
                tipo_dado=row["tipo_dado"],
                sensibilidade=row["sensibilidade"],
                ativo=row["ativo"],
                usavel_em_visao360=row["usavel_em_visao360"],
                usavel_em_peca=row["usavel_em_peca"],
                bloco_visao360=row.get("bloco_visao360"),
            )
            for row in dados
        ]

        return {
            "data": [item.model_dump() for item in itens],
            "meta": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def obter_campo(self, caracteristica_id: str) -> Optional[Dict]:
        """Obtém detalhe completo de uma característica."""
        row = self.repository.buscar_campo_por_id(caracteristica_id)
        if not row:
            return None
        return CampoAdminDetalheDTO(
            caracteristica_id=row["caracteristica_id"],
            campo_label=row["campo_label"],
            tema=row["tema"],
            tipo_dado=row["tipo_dado"],
            sensibilidade=row["sensibilidade"],
            ativo=row["ativo"],
            usavel_em_visao360=row["usavel_em_visao360"],
            usavel_em_peca=row["usavel_em_peca"],
            bloco_visao360=row.get("bloco_visao360"),
            tabela_fisica=row["tabela_fisica"],
            campo_fisico=row["campo_fisico"],
            operadores=row.get("operadores", []),
            valores_dominio=row.get("valores_dominio"),
            descricao=row.get("descricao"),
        ).model_dump()

    def atualizar_flags(
        self,
        caracteristica_id: str,
        flags: FlagUpdateDTO,
        alterado_por: str,
    ) -> Dict:
        """
        Atualiza flags de uma característica e grava histórico.
        """
        # Busca estado atual para obter o campo_label
        atual = self.repository.buscar_campo_por_id(caracteristica_id)
        if not atual:
            raise ValueError(f"Característica '{caracteristica_id}' não encontrada")

        # Aplica alterações
        resultado = self.repository.atualizar_flags(
            caracteristica_id,
            usavel_em_visao360=flags.usavel_em_visao360,
            usavel_em_peca=flags.usavel_em_peca,
            bloco_visao360=flags.bloco_visao360,
        )

        # Grava histórico para cada flag alterada
        alteracoes = resultado.get("alteracoes", {})
        for flag, valores in alteracoes.items():
            self._gravar_historico(
                caracteristica_id=caracteristica_id,
                campo_label=atual["campo_label"],
                flag=flag,
                de=valores["de"],
                para=valores["para"],
                alterado_por=alterado_por,
            )

        return {
            "ok": True,
            "alteracoes": [
                {"flag": k, "de": v["de"], "para": v["para"]}
                for k, v in alteracoes.items()
            ],
            "estado_atual": resultado.get("estado_atual", {}),
        }

    def atualizar_status(
        self,
        caracteristica_id: str,
        status: StatusUpdateDTO,
        alterado_por: str,
    ) -> Dict:
        """
        Atualiza status ativo/inativo de uma característica e grava histórico.
        """
        atual = self.repository.buscar_campo_por_id(caracteristica_id)
        if not atual:
            raise ValueError(f"Característica '{caracteristica_id}' não encontrada")

        resultado = self.repository.atualizar_status(caracteristica_id, status.ativo)
        alteracao = resultado.get("alteracao")

        if alteracao:
            self._gravar_historico(
                caracteristica_id=caracteristica_id,
                campo_label=atual["campo_label"],
                flag="ativo",
                de=alteracao["de"],
                para=alteracao["para"],
                alterado_por=alterado_por,
            )
            return {"ok": True, "alteracao": alteracao}
        else:
            return {"ok": True, "alteracao": None}

    # ============================================================
    # HISTÓRICO
    # ============================================================

    def listar_historico(
        self,
        caracteristica_id: Optional[str] = None,
        sistema_alvo: Optional[str] = None,
        acao: Optional[str] = None,
        alterado_por: Optional[str] = None,
        de: Optional[str] = None,
        ate: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Dict:
        """Lista histórico de governança com paginação."""
        offset = (page - 1) * size
        dados = self.repository.listar_historico(
            caracteristica_id=caracteristica_id,
            sistema_alvo=sistema_alvo,
            acao=acao,
            alterado_por=alterado_por,
            de=de,
            ate=ate,
            limit=size,
            offset=offset,
        )
        total = self.repository.contar_historico(
            caracteristica_id=caracteristica_id,
            sistema_alvo=sistema_alvo,
            acao=acao,
            alterado_por=alterado_por,
            de=de,
            ate=ate,
        )
        total_pages = (total + size - 1) // size if total > 0 else 0

        return {
            "data": dados,
            "meta": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
            },
        }