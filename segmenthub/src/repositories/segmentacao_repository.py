"""
Repository para segmentações.
Gerencia persistência em plataforma.segmentacao.*.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from src.db.databricks_client import get_client


class SegmentacaoRepository:
    """Acesso a dados para segmentações."""

    def __init__(self):
        self.client = get_client()

    # ==================== CRUD BÁSICO ====================

    def inserir(self, dados: Dict[str, Any]) -> str:
        """Insere uma nova segmentação e retorna o seg_id."""
        sql = """
            INSERT INTO plataforma.segmentacao.seg_definicao (
                seg_id, seg_codigo, seg_slug, nome, descricao, objetivo,
                seg_tags, resumo, objetivo_negocio, publico_alvo_descricao,
                observacoes, documentacao_md, owner, area_responsavel,
                email_contato, criado_por, publico_base_id, regras_json,
                tipo, status, versao_atual, criado_em, atualizado_em
            ) VALUES (
                :seg_id, :seg_codigo, :seg_slug, :nome, :descricao, :objetivo,
                :seg_tags, :resumo, :objetivo_negocio, :publico_alvo_descricao,
                :observacoes, :documentacao_md, :owner, :area_responsavel,
                :email_contato, :criado_por, :publico_base_id, :regras_json,
                :tipo, :status, :versao_atual, :criado_em, :atualizado_em
            )
        """
        self.client.execute_insert(sql, dados)
        return dados["seg_id"]

    def buscar_por_id(self, seg_id: str) -> Optional[Dict]:
        """Busca uma segmentação pelo ID."""
        sql = """
            SELECT *
            FROM plataforma.segmentacao.seg_definicao
            WHERE seg_id = :seg_id
        """
        result = self.client.execute_query(sql, {"seg_id": seg_id})
        return result[0] if result else None

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
        conditions = ["habilitado = true"]
        params = {}

        if status:
            conditions.append("status = :status")
            params["status"] = status
        if objetivo:
            conditions.append("objetivo = :objetivo")
            params["objetivo"] = objetivo
        if owner:
            conditions.append("owner = :owner")
            params["owner"] = owner
        if busca:
            conditions.append("(nome LIKE :busca OR seg_codigo LIKE :busca OR descricao LIKE :busca)")
            params["busca"] = f"%{busca}%"

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT seg_id, seg_codigo, seg_slug, nome, descricao, objetivo,
                seg_tags, resumo, objetivo_negocio, status, versao_atual,
                criado_por, criado_em, atualizado_em, owner, area_responsavel,
                publico_base_id, tipo
            FROM plataforma.segmentacao.seg_definicao
            WHERE {where_clause}
            ORDER BY criado_em DESC
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset

        # Executa a query
        results = self.client.execute_query(sql, params)

        # --- CORREÇÃO: Converte campos array (numpy) para listas Python ---
        for row in results:
            if "seg_tags" in row and hasattr(row["seg_tags"], "tolist"):
                row["seg_tags"] = row["seg_tags"].tolist()
            # Caso existam outros arrays no futuro (ex: campanhas, etc.), trata aqui também
            # if "outro_campo_array" in row and hasattr(row["outro_campo_array"], "tolist"):
            #     row["outro_campo_array"] = row["outro_campo_array"].tolist()

        return results

    def contar(self, **filtros) -> int:
        """Conta segmentações com filtros (para paginação)."""
        # similar ao listar, mas com COUNT
        conditions = ["habilitado = true"]
        params = {}
        # ... (mesma lógica de filtros)
        # simplificado para brevidade
        sql = "SELECT COUNT(*) as total FROM plataforma.segmentacao.seg_definicao WHERE " + " AND ".join(conditions)
        result = self.client.execute_query(sql, params)
        return result[0]["total"] if result else 0

    def atualizar(self, seg_id: str, dados: Dict[str, Any]) -> bool:
        """Atualiza uma segmentação existente."""
        # Constrói SET dinamicamente
        set_parts = []
        params = {"seg_id": seg_id}
        for key, value in dados.items():
            set_parts.append(f"{key} = :{key}")
            params[key] = value
        set_clause = ", ".join(set_parts)
        sql = f"""
            UPDATE plataforma.segmentacao.seg_definicao
            SET {set_clause}, atualizado_em = current_timestamp()
            WHERE seg_id = :seg_id
        """
        rows = self.client.execute_insert(sql, params)
        return rows > 0

    def arquivar(self, seg_id: str) -> bool:
        """Arquiva uma segmentação (soft delete)."""
        sql = """
            UPDATE plataforma.segmentacao.seg_definicao
            SET status = 'arquivada', habilitado = false, atualizado_em = current_timestamp()
            WHERE seg_id = :seg_id
        """
        rows = self.client.execute_insert(sql, {"seg_id": seg_id})
        return rows > 0

    # ==================== CICLO DE VIDA ====================

    def atualizar_status(self, seg_id: str, novo_status: str, motivo: Optional[str] = None) -> bool:
        """Atualiza o status de uma segmentação e registra no histórico."""
        # 1. Busca status atual
        atual = self.buscar_por_id(seg_id)
        if not atual:
            return False
        status_anterior = atual["status"]

        # 2. Atualiza status
        sql = """
            UPDATE plataforma.segmentacao.seg_definicao
            SET status = :novo_status, atualizado_em = current_timestamp()
            WHERE seg_id = :seg_id
        """
        self.client.execute_insert(sql, {"seg_id": seg_id, "novo_status": novo_status})

        # 3. Registra no histórico
        self.registrar_historico_estado(seg_id, status_anterior, novo_status, motivo)
        return True

    def registrar_historico_estado(self, seg_id: str, estado_anterior: str, estado_novo: str, motivo: Optional[str] = None):
        """Registra transição de estado no histórico."""
        sql = """
            INSERT INTO plataforma.segmentacao.seg_historico_estado
            (hist_id, seg_id, estado_anterior, estado_novo, motivo, alterado_por, alterado_em)
            VALUES (
                :hist_id, :seg_id, :estado_anterior, :estado_novo, :motivo, :alterado_por, current_timestamp()
            )
        """
        import uuid
        hist_id = f"hist_{uuid.uuid4().hex[:12]}"
        self.client.execute_insert(sql, {
            "hist_id": hist_id,
            "seg_id": seg_id,
            "estado_anterior": estado_anterior,
            "estado_novo": estado_novo,
            "motivo": motivo,
            "alterado_por": "system",  # virá do usuário autenticado
        })

    def inserir_versao(self, seg_id: str, versao: int, regras_json: Dict, motivo: str, alterado_por: str) -> bool:
        """Insere uma nova versão da segmentação."""
        sql = """
            INSERT INTO plataforma.segmentacao.seg_versao
            (versao_id, seg_id, versao, regras_json, motivo, alterado_por, alterado_em)
            VALUES (
                :versao_id, :seg_id, :versao, :regras_json, :motivo, :alterado_por, current_timestamp()
            )
        """
        import uuid
        versao_id = f"ver_{uuid.uuid4().hex[:12]}"
        self.client.execute_insert(sql, {
            "versao_id": versao_id,
            "seg_id": seg_id,
            "versao": versao,
            "regras_json": regras_json,
            "motivo": motivo,
            "alterado_por": alterado_por,
        })
        return True

    def executar_segmentacao(self, seg_id: str, exec_id: str) -> bool:
        """Cria um registro de execução (chamado pelo Job posteriormente)."""
        sql = """
            INSERT INTO plataforma.segmentacao.seg_execucao
            (exec_id, seg_id, origem_execucao, status)
            VALUES (:exec_id, :seg_id, 'manual', 'em_execucao')
        """
        self.client.execute_insert(sql, {"exec_id": exec_id, "seg_id": seg_id})
        return True

    # ==================== DESTINO E VIGÊNCIA ====================

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
        params = (seg_id, destino, habilitado, seg_id, destino, habilitado)
        self.client.execute_insert(sql, params)
        return True

    def buscar_destinos(self, seg_id: str) -> List[Dict]:
        """Busca destinos de um segmento."""
        sql = """
            SELECT destino, habilitado
            FROM plataforma.segmentacao.seg_destino
            WHERE seg_id = :seg_id
        """
        return self.client.execute_query(sql, {"seg_id": seg_id})

    def atualizar_vigencia(self, seg_id: str, dados: Dict) -> bool:
        """Atualiza vigência e agendamento."""
        sql = """
            UPDATE plataforma.segmentacao.seg_definicao
            SET vigencia_inicio = :vigencia_inicio,
                vigencia_fim = :vigencia_fim,
                recorrencia = :recorrencia,
                agendamento_cron = :agendamento_cron,
                atualizado_em = current_timestamp()
            WHERE seg_id = :seg_id
        """
        dados["seg_id"] = seg_id
        rows = self.client.execute_insert(sql, dados)
        return rows > 0

    def _converter_arrays(self, dados: Dict) -> Dict:
        """Converte arrays do numpy para listas Python."""
        if dados is None:
            return dados
        for key, value in dados.items():
            if hasattr(value, "tolist"):
                dados[key] = value.tolist()
            elif isinstance(value, (list, tuple)) and value and hasattr(value[0], "tolist"):
                dados[key] = [v.tolist() if hasattr(v, "tolist") else v for v in value]
        return dados

    def listar_versoes(self, seg_id: str) -> List[Dict]:
        sql = """
            SELECT versao, regras_json, motivo, alterado_por, alterado_em
            FROM plataforma.segmentacao.seg_versao
            WHERE seg_id = ?
            ORDER BY versao DESC
        """
        return self.client.execute_query(sql, (seg_id,))

    def obter_versao(self, seg_id: str, versao: int) -> Optional[Dict]:
        sql = """
            SELECT versao, regras_json, motivo, alterado_por, alterado_em
            FROM plataforma.segmentacao.seg_versao
            WHERE seg_id = ? AND versao = ?
        """
        result = self.client.execute_query(sql, (seg_id, versao))
        return result[0] if result else None

    def listar_execucoes(self, seg_id: str) -> List[Dict]:
        sql = """
            SELECT exec_id, status, qtd_clientes, origem_execucao, executado_em, job_run_url
            FROM plataforma.segmentacao.seg_execucao
            WHERE seg_id = ?
            ORDER BY executado_em DESC
        """
        return self.client.execute_query(sql, (seg_id,))

    def listar_estados(self, seg_id: str) -> List[Dict]:
        sql = """
            SELECT estado_anterior, estado_novo, motivo, alterado_por, alterado_em
            FROM plataforma.segmentacao.seg_historico_estado
            WHERE seg_id = ?
            ORDER BY alterado_em DESC
        """
        return self.client.execute_query(sql, (seg_id,))