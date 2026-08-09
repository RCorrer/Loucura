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
        sql = """
            SELECT 
                caracteristica_id, campo_label, tema, tipo_dado, sensibilidade,
                ativo, usavel_em_visao360, usavel_em_peca, bloco_visao360,
                tabela_fisica, campo_fisico, operadores, valores_dominio, descricao
            FROM plataforma.metadata.catalogo_caracteristicas
            WHERE 1=1
        """
        params = []

        if tema:
            sql += " AND tema = ?"
            params.append(tema)
        if sistema == "s2":
            sql += " AND usavel_em_visao360 = true"
        elif sistema == "s3":
            sql += " AND usavel_em_peca = true"
        if status == "ativo":
            sql += " AND ativo = true"
        elif status == "inativo":
            sql += " AND ativo = false"
        if busca:
            sql += " AND (campo_label LIKE ? OR caracteristica_id LIKE ? OR descricao LIKE ?)"
            busca_param = f"%{busca}%"
            params.extend([busca_param, busca_param, busca_param])

        sql += " ORDER BY tema, campo_label LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.client.execute_query(sql, tuple(params))
        columns = [
            "caracteristica_id", "campo_label", "tema", "tipo_dado", "sensibilidade",
            "ativo", "usavel_em_visao360", "usavel_em_peca", "bloco_visao360",
            "tabela_fisica", "campo_fisico", "operadores", "valores_dominio", "descricao"
        ]
        results = []
        for row in rows:
            # Converte arrays para listas Python se necessário
            row_list = list(row)
            # operadores está na posição 11 (índice 11)
            if len(row_list) > 11 and hasattr(row_list[11], "tolist"):
                row_list[11] = row_list[11].tolist()
            # valores_dominio está na posição 12 (índice 12)
            if len(row_list) > 12 and hasattr(row_list[12], "tolist"):
                row_list[12] = row_list[12].tolist()
            results.append(dict(zip(columns, row_list)))
        return results

    def contar_campos(
        self,
        tema: Optional[str] = None,
        sistema: Optional[str] = None,
        status: Optional[str] = None,
        busca: Optional[str] = None,
    ) -> int:
        """Conta características com filtros."""
        sql = "SELECT COUNT(*) FROM plataforma.metadata.catalogo_caracteristicas WHERE 1=1"
        params = []

        if tema:
            sql += " AND tema = ?"
            params.append(tema)
        if sistema == "s2":
            sql += " AND usavel_em_visao360 = true"
        elif sistema == "s3":
            sql += " AND usavel_em_peca = true"
        if status == "ativo":
            sql += " AND ativo = true"
        elif status == "inativo":
            sql += " AND ativo = false"
        if busca:
            sql += " AND (campo_label LIKE ? OR caracteristica_id LIKE ? OR descricao LIKE ?)"
            busca_param = f"%{busca}%"
            params.extend([busca_param, busca_param, busca_param])

        result = self.client.execute_query(sql, tuple(params))
        return result[0][0] if result else 0

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
        rows = self.client.execute_query(sql, (caracteristica_id,))
        if rows:
            columns = [
                "caracteristica_id", "campo_label", "tema", "tipo_dado", "sensibilidade",
                "ativo", "usavel_em_visao360", "usavel_em_peca", "bloco_visao360",
                "tabela_fisica", "campo_fisico", "operadores", "valores_dominio", "descricao"
            ]
            row = list(rows[0])
            if len(row) > 11 and hasattr(row[11], "tolist"):
                row[11] = row[11].tolist()
            if len(row) > 12 and hasattr(row[12], "tolist"):
                row[12] = row[12].tolist()
            return dict(zip(columns, row))
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
        params = [caracteristica_id]  # primeiro parâmetro: WHERE

        if usavel_em_visao360 is not None and atual["usavel_em_visao360"] != usavel_em_visao360:
            alteracoes["usavel_em_visao360"] = {"de": atual["usavel_em_visao360"], "para": usavel_em_visao360}
            updates.append("usavel_em_visao360 = ?")
            params.append(usavel_em_visao360)

        if usavel_em_peca is not None and atual["usavel_em_peca"] != usavel_em_peca:
            alteracoes["usavel_em_peca"] = {"de": atual["usavel_em_peca"], "para": usavel_em_peca}
            updates.append("usavel_em_peca = ?")
            params.append(usavel_em_peca)

        if bloco_visao360 is not None and atual["bloco_visao360"] != bloco_visao360:
            alteracoes["bloco_visao360"] = {"de": atual["bloco_visao360"], "para": bloco_visao360}
            updates.append("bloco_visao360 = ?")
            params.append(bloco_visao360)

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
            WHERE caracteristica_id = ?
        """
        self.client.execute_insert(sql, tuple(params))

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
            return {"alteracao": None}

        sql = """
            UPDATE plataforma.metadata.catalogo_caracteristicas
            SET ativo = ?
            WHERE caracteristica_id = ?
        """
        self.client.execute_insert(sql, (ativo, caracteristica_id))

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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp())
        """
        params = (
            dados["hist_id"],
            dados["caracteristica_id"],
            dados.get("campo_label"),
            dados["flag_alterada"],
            dados.get("sistema_alvo"),
            dados.get("valor_anterior"),
            dados["valor_novo"],
            dados["acao"],
            dados["alterado_por"],
        )
        self.client.execute_insert(sql, params)
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
        sql = """
            SELECT 
                hist_id, caracteristica_id, campo_label,
                flag_alterada, sistema_alvo, valor_anterior, valor_novo,
                acao, alterado_por, alterado_em
            FROM plataforma.metadata.catalogo_governanca_hist
            WHERE 1=1
        """
        params = []

        if caracteristica_id:
            sql += " AND caracteristica_id = ?"
            params.append(caracteristica_id)
        if sistema_alvo:
            sql += " AND sistema_alvo = ?"
            params.append(sistema_alvo)
        if acao:
            sql += " AND acao = ?"
            params.append(acao)
        if alterado_por:
            sql += " AND alterado_por = ?"
            params.append(alterado_por)
        if de:
            sql += " AND alterado_em >= ?"
            params.append(de)
        if ate:
            sql += " AND alterado_em <= ?"
            params.append(ate)

        sql += " ORDER BY alterado_em DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.client.execute_query(sql, tuple(params))
        columns = [
            "hist_id", "caracteristica_id", "campo_label",
            "flag_alterada", "sistema_alvo", "valor_anterior", "valor_novo",
            "acao", "alterado_por", "alterado_em"
        ]
        return [dict(zip(columns, row)) for row in rows]

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
        sql = "SELECT COUNT(*) FROM plataforma.metadata.catalogo_governanca_hist WHERE 1=1"
        params = []

        if caracteristica_id:
            sql += " AND caracteristica_id = ?"
            params.append(caracteristica_id)
        if sistema_alvo:
            sql += " AND sistema_alvo = ?"
            params.append(sistema_alvo)
        if acao:
            sql += " AND acao = ?"
            params.append(acao)
        if alterado_por:
            sql += " AND alterado_por = ?"
            params.append(alterado_por)
        if de:
            sql += " AND alterado_em >= ?"
            params.append(de)
        if ate:
            sql += " AND alterado_em <= ?"
            params.append(ate)

        result = self.client.execute_query(sql, tuple(params))
        return result[0][0] if result else 0