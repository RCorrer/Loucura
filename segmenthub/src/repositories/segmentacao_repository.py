"""
Repository para segmentações.
Gerencia persistência em plataforma.segmentacao.*.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from src.db.databricks_client import get_client
import uuid


class SegmentacaoRepository:
    """Acesso a dados para segmentações."""

    def __init__(self):
        self.client = get_client()

    # ============================================================
    # HELPERS
    # ============================================================

    def _rows_to_dicts(self, rows: List[List], columns: List[str]) -> List[Dict]:
        """Converte lista de listas em lista de dicionários."""
        return [dict(zip(columns, row)) for row in rows]

    def _row_to_dict(self, row: List, columns: List[str]) -> Optional[Dict]:
        """Converte uma lista em dicionário."""
        return dict(zip(columns, row)) if row else None

    def _flatten_params(self, params: Dict) -> tuple:
        """Converte dicionário de parâmetros para tupla na ordem dos placeholders."""
        # Para queries com placeholders posicionais, precisamos garantir a ordem
        return tuple(params.values())

    # ============================================================
    # CRUD BÁSICO
    # ============================================================

    def inserir(self, dados: Dict[str, Any]) -> str:
        """Insere uma nova segmentação e retorna o seg_id."""
        sql = """
            INSERT INTO plataforma.segmentacao.seg_definicao (
                seg_id, seg_codigo, seg_slug, nome, descricao, objetivo,
                seg_tags, resumo, objetivo_negocio, publico_alvo_descricao,
                observacoes, documentacao_md, owner, area_responsavel,
                email_contato, criado_por, publico_base_id, regras_json,
                tipo, status, versao_atual, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        # Converte regras_json para string se for dict
        regras_json = dados.get("regras_json")
        if isinstance(regras_json, dict):
            import json
            regras_json = json.dumps(regras_json)

        params = (
            dados["seg_id"],
            dados["seg_codigo"],
            dados["seg_slug"],
            dados["nome"],
            dados.get("descricao"),
            dados["objetivo"],
            dados.get("seg_tags", []),
            dados.get("resumo"),
            dados.get("objetivo_negocio"),
            dados.get("publico_alvo_descricao"),
            dados.get("observacoes"),
            dados.get("documentacao_md"),
            dados["owner"],
            dados.get("area_responsavel"),
            dados.get("email_contato"),
            dados["criado_por"],
            dados["publico_base_id"],
            regras_json,
            dados.get("tipo", "direta"),
            dados.get("status", "rascunho"),
            dados.get("versao_atual", 1),
            dados.get("criado_em", datetime.now()),
            dados.get("atualizado_em", datetime.now()),
        )
        self.client.execute_insert(sql, params)
        return dados["seg_id"]

    def buscar_por_id(self, seg_id: str) -> Optional[Dict]:
        """Busca uma segmentação pelo ID."""
        sql = """
            SELECT 
                seg_id, seg_codigo, seg_slug, nome, descricao, objetivo,
                seg_tags, resumo, objetivo_negocio, publico_alvo_descricao,
                observacoes, documentacao_md, owner, area_responsavel,
                email_contato, criado_por, criado_em, seg_origem_id,
                tipo_origem, tipo, publico_base_id, regras_json, status,
                vigencia_inicio, vigencia_fim, agendamento_cron, recorrencia,
                aprovado_por, aprovado_em, checklist_validacao_json,
                versao_atual, atualizado_em, habilitado
            FROM plataforma.segmentacao.seg_definicao
            WHERE seg_id = ?
        """
        rows = self.client.execute_query(sql, (seg_id,))
        columns = [
            "seg_id", "seg_codigo", "seg_slug", "nome", "descricao", "objetivo",
            "seg_tags", "resumo", "objetivo_negocio", "publico_alvo_descricao",
            "observacoes", "documentacao_md", "owner", "area_responsavel",
            "email_contato", "criado_por", "criado_em", "seg_origem_id",
            "tipo_origem", "tipo", "publico_base_id", "regras_json", "status",
            "vigencia_inicio", "vigencia_fim", "agendamento_cron", "recorrencia",
            "aprovado_por", "aprovado_em", "checklist_validacao_json",
            "versao_atual", "atualizado_em", "habilitado"
        ]
        if rows:
            row = list(rows[0])
            # Converte seg_tags de array para lista Python se necessário
            idx = columns.index("seg_tags")
            if len(row) > idx and hasattr(row[idx], "tolist"):
                row[idx] = row[idx].tolist()
            # Converte regras_json de string para dict
            idx_regras = columns.index("regras_json")
            if len(row) > idx_regras and row[idx_regras]:
                import json
                try:
                    row[idx_regras] = json.loads(row[idx_regras])
                except:
                    pass
            return dict(zip(columns, row))
        return None

    def listar(
        self,
        status: Optional[str] = None,
        objetivo: Optional[str] = None,
        owner: Optional[str] = None,
        busca: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """Lista segmentações com filtros opcionais."""
        sql = """
            SELECT 
                seg_id, seg_codigo, seg_slug, nome, descricao, objetivo,
                seg_tags, resumo, objetivo_negocio, status, versao_atual,
                criado_por, criado_em, atualizado_em, owner, area_responsavel,
                publico_base_id, tipo
            FROM plataforma.segmentacao.seg_definicao
            WHERE habilitado = true
        """
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status)
        if objetivo:
            sql += " AND objetivo = ?"
            params.append(objetivo)
        if owner:
            sql += " AND owner = ?"
            params.append(owner)
        if busca:
            sql += " AND (LOWER(nome) LIKE ? OR LOWER(seg_codigo) LIKE ? OR LOWER(descricao) LIKE ?)"
            busca_param = f"%{busca.lower()}%"
            params.extend([busca_param, busca_param, busca_param])

        sql += " ORDER BY criado_em DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.client.execute_query(sql, tuple(params))
        columns = [
            "seg_id", "seg_codigo", "seg_slug", "nome", "descricao", "objetivo",
            "seg_tags", "resumo", "objetivo_negocio", "status", "versao_atual",
            "criado_por", "criado_em", "atualizado_em", "owner", "area_responsavel",
            "publico_base_id", "tipo"
        ]
        results = []
        for row in rows:
            row_list = list(row)
            idx = columns.index("seg_tags")
            if len(row_list) > idx and hasattr(row_list[idx], "tolist"):
                row_list[idx] = row_list[idx].tolist()
            results.append(dict(zip(columns, row_list)))
        return results

    def contar(self, **filtros) -> int:
        """Conta segmentações com filtros (para paginação)."""
        sql = "SELECT COUNT(*) FROM plataforma.segmentacao.seg_definicao WHERE habilitado = true"
        params = []

        if filtros.get("status"):
            sql += " AND status = ?"
            params.append(filtros["status"])
        if filtros.get("objetivo"):
            sql += " AND objetivo = ?"
            params.append(filtros["objetivo"])
        if filtros.get("owner"):
            sql += " AND owner = ?"
            params.append(filtros["owner"])
        if filtros.get("busca"):
            sql += " AND (LOWER(nome) LIKE ? OR LOWER(seg_codigo) LIKE ? OR LOWER(descricao) LIKE ?)"
            busca_param = f"%{filtros['busca'].lower()}%"
            params.extend([busca_param, busca_param, busca_param])

        result = self.client.execute_query(sql, tuple(params))
        return result[0][0] if result else 0

    # Sentinel para diferenciar "não passou o campo" de "quer setar NULL"
    _UNSET = object()

    def atualizar(self, seg_id: str, dados: Dict[str, Any]) -> bool:
        """Atualiza uma segmentação existente.
        
        Aceita None nos valores — seta o campo para NULL no banco.
        Apenas chaves ausentes do dict são ignoradas.
        """
        # Constrói SET dinamicamente
        set_parts = []
        set_params = []  # valores dos SET (antes do WHERE)
        for key, value in dados.items():
            set_parts.append(f"{key} = ?")
            set_params.append(value)
        if not set_parts:
            return False

        set_parts.append("atualizado_em = current_timestamp()")
        # seg_id vai no FINAL (WHERE é o último placeholder)
        params = tuple(set_params) + (seg_id,)
        sql = f"""
            UPDATE plataforma.segmentacao.seg_definicao
            SET {", ".join(set_parts)}
            WHERE seg_id = ?
        """
        rows = self.client.execute_insert(sql, params)
        return rows > 0

    def arquivar(self, seg_id: str) -> bool:
        """Arquiva uma segmentação (soft delete)."""
        sql = """
            UPDATE plataforma.segmentacao.seg_definicao
            SET status = 'arquivada', habilitado = false, atualizado_em = current_timestamp()
            WHERE seg_id = ?
        """
        rows = self.client.execute_insert(sql, (seg_id,))
        return rows > 0

    # ============================================================
    # CICLO DE VIDA
    # ============================================================

    def atualizar_status(self, seg_id: str, novo_status: str, motivo: Optional[str] = None, usuario: str = "system") -> bool:
        """Atualiza o status de uma segmentação e registra no histórico."""
        atual = self.buscar_por_id(seg_id)
        if not atual:
            return False
        status_anterior = atual["status"]

        sql = """
            UPDATE plataforma.segmentacao.seg_definicao
            SET status = ?, atualizado_em = current_timestamp()
            WHERE seg_id = ?
        """
        self.client.execute_insert(sql, (novo_status, seg_id))
        self.registrar_historico_estado(seg_id, status_anterior, novo_status, motivo, usuario)
        return True

    def registrar_historico_estado(self, seg_id: str, estado_anterior: str, estado_novo: str, motivo: Optional[str] = None, usuario: str = "system"):
        """Registra transição de estado no histórico."""
        hist_id = f"hist_{uuid.uuid4().hex[:12]}"
        sql = """
            INSERT INTO plataforma.segmentacao.seg_historico_estado
            (hist_id, seg_id, estado_anterior, estado_novo, motivo, alterado_por, alterado_em)
            VALUES (?, ?, ?, ?, ?, ?, current_timestamp())
        """
        self.client.execute_insert(sql, (hist_id, seg_id, estado_anterior, estado_novo, motivo, usuario))

    def inserir_versao(self, seg_id: str, versao: int, regras_json: Dict, motivo: str, alterado_por: str) -> bool:
        """Insere uma nova versão da segmentação."""
        versao_id = f"ver_{uuid.uuid4().hex[:12]}"
        sql = """
            INSERT INTO plataforma.segmentacao.seg_versao
            (versao_id, seg_id, versao, regras_json, motivo, alterado_por, alterado_em)
            VALUES (?, ?, ?, ?, ?, ?, current_timestamp())
        """
        import json
        self.client.execute_insert(sql, (
            versao_id, seg_id, versao, json.dumps(regras_json), motivo, alterado_por
        ))
        return True

    def executar_segmentacao(self, seg_id: str, exec_id: str) -> bool:
        """Cria um registro de execução (chamado pelo Job posteriormente)."""
        sql = """
            INSERT INTO plataforma.segmentacao.seg_execucao
            (exec_id, seg_id, origem_execucao, status)
            VALUES (?, ?, 'manual', 'em_execucao')
        """
        self.client.execute_insert(sql, (exec_id, seg_id))
        return True

    # ============================================================
    # DESTINO E VIGÊNCIA
    # ============================================================

    def upsert_destino(self, seg_id: str, destino: str, habilitado: bool) -> bool:
        sql = """
            MERGE INTO plataforma.segmentacao.seg_destino AS target
            USING (SELECT ? AS seg_id, ? AS destino) AS source
            ON target.seg_id = source.seg_id AND target.destino = source.destino
            WHEN MATCHED THEN
                UPDATE SET habilitado = ?
            WHEN NOT MATCHED THEN
                INSERT (seg_id, destino, habilitado, criado_em)
                VALUES (?, ?, ?, current_timestamp())
        """
        self.client.execute_insert(sql, (seg_id, destino, habilitado, seg_id, destino, habilitado))
        return True

    def buscar_destinos(self, seg_id: str) -> List[Dict]:
        """Busca destinos de um segmento."""
        sql = "SELECT destino, habilitado FROM plataforma.segmentacao.seg_destino WHERE seg_id = ?"
        rows = self.client.execute_query(sql, (seg_id,))
        columns = ["destino", "habilitado"]
        return [dict(zip(columns, row)) for row in rows]

    def atualizar_vigencia(self, seg_id: str, dados: Dict) -> bool:
        """Atualiza vigência e agendamento."""
        sql = """
            UPDATE plataforma.segmentacao.seg_definicao
            SET vigencia_inicio = ?,
                vigencia_fim = ?,
                recorrencia = ?,
                agendamento_cron = ?,
                atualizado_em = current_timestamp()
            WHERE seg_id = ?
        """
        params = (
            dados.get("vigencia_inicio"),
            dados.get("vigencia_fim"),
            dados.get("recorrencia"),
            dados.get("agendamento_cron"),
            seg_id,
        )
        rows = self.client.execute_insert(sql, params)
        return rows > 0

    # ============================================================
    # VERSÕES / EXECUÇÕES / ESTADOS
    # ============================================================

    def listar_versoes(self, seg_id: str) -> List[Dict]:
        sql = """
            SELECT versao, regras_json, motivo, alterado_por, alterado_em
            FROM plataforma.segmentacao.seg_versao
            WHERE seg_id = ?
            ORDER BY versao DESC
        """
        rows = self.client.execute_query(sql, (seg_id,))
        columns = ["versao", "regras_json", "motivo", "alterado_por", "alterado_em"]
        results = []
        for row in rows:
            row_list = list(row)
            # regras_json está na posição 1
            if len(row_list) > 1 and row_list[1]:
                import json
                try:
                    row_list[1] = json.loads(row_list[1])
                except:
                    pass
            results.append(dict(zip(columns, row_list)))
        return results

    def obter_versao(self, seg_id: str, versao: int) -> Optional[Dict]:
        sql = """
            SELECT versao, regras_json, motivo, alterado_por, alterado_em
            FROM plataforma.segmentacao.seg_versao
            WHERE seg_id = ? AND versao = ?
        """
        rows = self.client.execute_query(sql, (seg_id, versao))
        if rows:
            columns = ["versao", "regras_json", "motivo", "alterado_por", "alterado_em"]
            row = list(rows[0])
            if len(row) > 1 and row[1]:
                import json
                try:
                    row[1] = json.loads(row[1])
                except:
                    pass
            return dict(zip(columns, row))
        return None

    def listar_execucoes(self, seg_id: str) -> List[Dict]:
        sql = """
            SELECT exec_id, status, qtd_clientes, origem_execucao, executado_em, job_run_url
            FROM plataforma.segmentacao.seg_execucao
            WHERE seg_id = ?
            ORDER BY executado_em DESC
        """
        rows = self.client.execute_query(sql, (seg_id,))
        columns = ["exec_id", "status", "qtd_clientes", "origem_execucao", "executado_em", "job_run_url"]
        return [dict(zip(columns, row)) for row in rows]

    def listar_estados(self, seg_id: str) -> List[Dict]:
        sql = """
            SELECT estado_anterior, estado_novo, motivo, alterado_por, alterado_em
            FROM plataforma.segmentacao.seg_historico_estado
            WHERE seg_id = ?
            ORDER BY alterado_em DESC
        """
        rows = self.client.execute_query(sql, (seg_id,))
        columns = ["estado_anterior", "estado_novo", "motivo", "alterado_por", "alterado_em"]
        return [dict(zip(columns, row)) for row in rows]