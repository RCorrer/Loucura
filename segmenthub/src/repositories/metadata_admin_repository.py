"""
Repository para administração de catálogo (governança).
Gerencia flags e histórico.
"""

import json
from typing import List, Dict, Optional, Any
from src.db.databricks_client import get_client


class MetadataAdminRepository:
    """Acesso a dados para governança de catálogo."""

    def __init__(self):
        self.client = get_client()

    # ============================================================
    # CATÁLOGO
    # ============================================================

    def listar_campos(
        self,
        tema: Optional[str] = None,
        sistema: Optional[str] = None,
        status: Optional[str] = None,
        busca: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """Lista características com filtros (inclui inativas)."""
        conditions = ["1=1"]
        params = {}

        if tema:
            conditions.append("tema = :tema")
            params["tema"] = tema
        if sistema == "s2":
            conditions.append("usavel_em_visao360 = true")
        elif sistema == "s3":
            conditions.append("usavel_em_peca = true")
        if status == "ativo":
            conditions.append("ativo = true")
        elif status == "inativo":
            conditions.append("ativo = false")
        if busca:
            conditions.append("(campo_label LIKE :busca OR caracteristica_id LIKE :busca OR descricao LIKE :busca)")
            params["busca"] = f"%{busca}%"

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT 
                caracteristica_id, campo_label, tema, tipo_dado, sensibilidade,
                ativo, usavel_em_visao360, usavel_em_peca, bloco_visao360,
                tabela_fisica, campo_fisico, operadores, valores_dominio, descricao
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE {where_clause}
            ORDER BY tema, campo_label
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset
        results = self.client.execute_query(sql, params)

        # Converte arrays para listas Python
        for row in results:
            if "operadores" in row and hasattr(row["operadores"], "tolist"):
                row["operadores"] = row["operadores"].tolist()
            if "valores_dominio" in row and hasattr(row["valores_dominio"], "tolist"):
                row["valores_dominio"] = row["valores_dominio"].tolist()
        return results

    def contar_campos(
        self,
        tema: Optional[str] = None,
        sistema: Optional[str] = None,
        status: Optional[str] = None,
        busca: Optional[str] = None,
    ) -> int:
        """Conta características com filtros."""
        conditions = ["1=1"]
        params = {}

        if tema:
            conditions.append("tema = :tema")
            params["tema"] = tema
        if sistema == "s2":
            conditions.append("usavel_em_visao360 = true")
        elif sistema == "s3":
            conditions.append("usavel_em_peca = true")
        if status == "ativo":
            conditions.append("ativo = true")
        elif status == "inativo":
            conditions.append("ativo = false")
        if busca:
            conditions.append("(campo_label LIKE :busca OR caracteristica_id LIKE :busca OR descricao LIKE :busca)")
            params["busca"] = f"%{busca}%"

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT COUNT(*) as total
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE {where_clause}
        """
        result = self.client.execute_query(sql, params)
        return result[0]["total"] if result else 0

    def buscar_campo_por_id(self, caracteristica_id: str) -> Optional[Dict]:
        """Busca uma característica por ID (inclui inativas)."""
        sql = """
            SELECT 
                caracteristica_id, campo_label, tema, tipo_dado, sensibilidade,
                ativo, usavel_em_visao360, usavel_em_peca, bloco_visao360,
                tabela_fisica, campo_fisico, operadores, valores_dominio, descricao
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE caracteristica_id = ?
        """
        results = self.client.execute_query(sql, (caracteristica_id,))
        if results:
            row = results[0]
            if "operadores" in row and hasattr(row["operadores"], "tolist"):
                row["operadores"] = row["operadores"].tolist()
            if "valores_dominio" in row and hasattr(row["valores_dominio"], "tolist"):
                row["valores_dominio"] = row["valores_dominio"].tolist()
            return row
        return None

    def atualizar_flags(
        self,
        caracteristica_id: str,
        usavel_em_visao360: Optional[bool] = None,
        usavel_em_peca: Optional[bool] = None,
        bloco_visao360: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Atualiza flags de uma característica.
        Retorna dicionário com valores anteriores e novos para cada flag alterada.
        """
        # Busca estado atual
        atual = self.buscar_campo_por_id(caracteristica_id)
        if not atual:
            raise ValueError(f"Característica '{caracteristica_id}' não encontrada")

        alteracoes = {}
        updates = []
        params = {"caracteristica_id": caracteristica_id}

        if usavel_em_visao360 is not None and atual["usavel_em_visao360"] != usavel_em_visao360:
            alteracoes["usavel_em_visao360"] = {"de": atual["usavel_em_visao360"], "para": usavel_em_visao360}
            updates.append("usavel_em_visao360 = :usavel_em_visao360")
            params["usavel_em_visao360"] = usavel_em_visao360

        if usavel_em_peca is not None and atual["usavel_em_peca"] != usavel_em_peca:
            alteracoes["usavel_em_peca"] = {"de": atual["usavel_em_peca"], "para": usavel_em_peca}
            updates.append("usavel_em_peca = :usavel_em_peca")
            params["usavel_em_peca"] = usavel_em_peca

        if bloco_visao360 is not None and atual["bloco_visao360"] != bloco_visao360:
            alteracoes["bloco_visao360"] = {"de": atual["bloco_visao360"], "para": bloco_visao360}
            updates.append("bloco_visao360 = :bloco_visao360")
            params["bloco_visao360"] = bloco_visao360

        if not alteracoes:
            return {"alteracoes": {}}

        # Valida regra: bloco_visao360 só pode ser setado se usavel_em_visao360=true
        novo_v360 = alteracoes.get("usavel_em_visao360", {}).get("para", atual["usavel_em_visao360"])
        if bloco_visao360 is not None and not novo_v360:
            raise ValueError("Não é possível definir bloco_visao360 sem usavel_em_visao360=true")

        # Executa UPDATE
        set_clause = ", ".join(updates)
        sql = f"""
            UPDATE plataforma.metadata.catalogo_caracteristicas
            SET {set_clause}
            WHERE caracteristica_id = :caracteristica_id
        """
        self.client.execute_insert(sql, params)

        return {
            "alteracoes": alteracoes,
            "estado_atual": {
                "usavel_em_visao360": novo_v360,
                "usavel_em_peca": alteracoes.get("usavel_em_peca", {}).get("para", atual["usavel_em_peca"]),
                "bloco_visao360": alteracoes.get("bloco_visao360", {}).get("para", atual["bloco_visao360"]),
            },
        }

    def atualizar_status(self, caracteristica_id: str, ativo: bool) -> Dict[str, Any]:
        """Atualiza o status ativo/inativo de uma característica."""
        atual = self.buscar_campo_por_id(caracteristica_id)
        if not atual:
            raise ValueError(f"Característica '{caracteristica_id}' não encontrada")

        if atual["ativo"] == ativo:
            return {"alteracao": None}  # sem mudança

        sql = """
            UPDATE plataforma.metadata.catalogo_caracteristicas
            SET ativo = :ativo
            WHERE caracteristica_id = :caracteristica_id
        """
        self.client.execute_insert(sql, {"caracteristica_id": caracteristica_id, "ativo": ativo})

        return {
            "alteracao": {"de": atual["ativo"], "para": ativo}
        }

    # ============================================================
    # HISTÓRICO
    # ============================================================

    def inserir_historico(self, dados: Dict) -> str:
        """Insere um registro de histórico (append-only)."""
        sql = """
            INSERT INTO plataforma.metadata.catalogo_governanca_hist (
                hist_id, caracteristica_id, campo_label,
                flag_alterada, sistema_alvo, valor_anterior, valor_novo,
                acao, alterado_por, alterado_em
            ) VALUES (
                :hist_id, :caracteristica_id, :campo_label,
                :flag_alterada, :sistema_alvo, :valor_anterior, :valor_novo,
                :acao, :alterado_por, current_timestamp()
            )
        """
        self.client.execute_insert(sql, dados)
        return dados["hist_id"]

    def listar_historico(
        self,
        caracteristica_id: Optional[str] = None,
        sistema_alvo: Optional[str] = None,
        acao: Optional[str] = None,
        alterado_por: Optional[str] = None,
        de: Optional[str] = None,
        ate: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """Lista histórico de governança com filtros."""
        conditions = ["1=1"]
        params = {}

        if caracteristica_id:
            conditions.append("caracteristica_id = :caracteristica_id")
            params["caracteristica_id"] = caracteristica_id
        if sistema_alvo:
            conditions.append("sistema_alvo = :sistema_alvo")
            params["sistema_alvo"] = sistema_alvo
        if acao:
            conditions.append("acao = :acao")
            params["acao"] = acao
        if alterado_por:
            conditions.append("alterado_por = :alterado_por")
            params["alterado_por"] = alterado_por
        if de:
            conditions.append("alterado_em >= :de")
            params["de"] = de
        if ate:
            conditions.append("alterado_em <= :ate")
            params["ate"] = ate

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT 
                hist_id, caracteristica_id, campo_label,
                flag_alterada, sistema_alvo, valor_anterior, valor_novo,
                acao, alterado_por, alterado_em
            FROM plataforma.metadata.catalogo_governanca_hist
            WHERE {where_clause}
            ORDER BY alterado_em DESC
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset
        return self.client.execute_query(sql, params)

    def contar_historico(
        self,
        caracteristica_id: Optional[str] = None,
        sistema_alvo: Optional[str] = None,
        acao: Optional[str] = None,
        alterado_por: Optional[str] = None,
        de: Optional[str] = None,
        ate: Optional[str] = None,
    ) -> int:
        """Conta registros de histórico com filtros."""
        conditions = ["1=1"]
        params = {}

        if caracteristica_id:
            conditions.append("caracteristica_id = :caracteristica_id")
            params["caracteristica_id"] = caracteristica_id
        if sistema_alvo:
            conditions.append("sistema_alvo = :sistema_alvo")
            params["sistema_alvo"] = sistema_alvo
        if acao:
            conditions.append("acao = :acao")
            params["acao"] = acao
        if alterado_por:
            conditions.append("alterado_por = :alterado_por")
            params["alterado_por"] = alterado_por
        if de:
            conditions.append("alterado_em >= :de")
            params["de"] = de
        if ate:
            conditions.append("alterado_em <= :ate")
            params["ate"] = ate

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT COUNT(*) as total
            FROM plataforma.metadata.catalogo_governanca_hist
            WHERE {where_clause}
        """
        result = self.client.execute_query(sql, params)
        return result[0]["total"] if result else 0