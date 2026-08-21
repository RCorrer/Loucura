"""
Repository para comentários e notificações.
"""

from src.db.databricks_client import get_client
from typing import List, Dict, Optional
import uuid


class ComentarioRepository:
    def __init__(self):
        self.client = get_client()

    def listar_comentarios(self, seg_id: str) -> List[Dict]:
        """Lista todos os comentários de uma segmentação (sem thread aninhada)."""
        sql = """
            SELECT 
                comentario_id, seg_id, versao_referencia, tipo, autor, texto,
                respondendo_a, mencoes, resolvido, criado_em, editado_em
            FROM plataforma.segmentacao.seg_comentario
            WHERE seg_id = ?
            ORDER BY criado_em ASC
        """
        rows = self.client.execute_query(sql, (seg_id,))
        columns = ["comentario_id", "seg_id", "versao_referencia", "tipo", "autor", "texto",
                   "respondendo_a", "mencoes", "resolvido", "criado_em", "editado_em"]
        return [dict(zip(columns, row)) for row in rows]

    def criar_comentario(self, dados: Dict) -> str:
        """Insere um novo comentário e retorna o ID."""
        comentario_id = f"com_{uuid.uuid4().hex[:12]}"
        sql = """
            INSERT INTO plataforma.segmentacao.seg_comentario
            (comentario_id, seg_id, versao_referencia, tipo, autor, texto, respondendo_a, mencoes, resolvido, criado_em, editado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp(), NULL)
        """
        params = (
            comentario_id,
            dados["seg_id"],
            dados.get("versao_referencia"),
            dados.get("tipo", "geral"),
            dados["autor"],
            dados["texto"],
            dados.get("respondendo_a"),
            dados.get("mencoes", []),
            dados.get("resolvido", False),
        )
        self.client.execute_insert(sql, params)
        return comentario_id

    def atualizar_comentario(self, comentario_id: str, texto: Optional[str] = None, resolvido: Optional[bool] = None) -> bool:
        """Atualiza texto e/ou resolvido de um comentário."""
        set_parts = []
        set_params = []  # SET values primeiro (ordem posicional)
        if texto is not None:
            set_parts.append("texto = ?")
            set_params.append(texto)
        if resolvido is not None:
            set_parts.append("resolvido = ?")
            set_params.append(resolvido)
        if not set_parts:
            return True
        set_parts.append("editado_em = current_timestamp()")
        sql = f"""
            UPDATE plataforma.segmentacao.seg_comentario
            SET {", ".join(set_parts)}
            WHERE comentario_id = ?
        """
        # WHERE param (comentario_id) vai no FINAL — após os SET values
        params = tuple(set_params) + (comentario_id,)
        rows = self.client.execute_insert(sql, params)
        return rows > 0

    def criar_notificacao(self, dados: Dict) -> str:
        """Insere uma notificação e retorna o ID."""
        notif_id = f"notif_{uuid.uuid4().hex[:12]}"
        sql = """
            INSERT INTO plataforma.segmentacao.seg_notificacao
            (notif_id, destinatario, tipo, seg_id, titulo, mensagem, lida, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, false, current_timestamp())
        """
        params = (
            notif_id,
            dados["destinatario"],
            dados["tipo"],
            dados.get("seg_id"),
            dados["titulo"],
            dados["mensagem"],
        )
        self.client.execute_insert(sql, params)
        return notif_id

    def listar_notificacoes(self, destinatario: str, lida: Optional[bool] = None) -> List[Dict]:
        """Lista notificações de um usuário."""
        sql = """
            SELECT notif_id, destinatario, tipo, seg_id, titulo, mensagem, lida, criado_em
            FROM plataforma.segmentacao.seg_notificacao
            WHERE destinatario = ?
        """
        params = [destinatario]
        if lida is not None:
            sql += " AND lida = ?"
            params.append(lida)
        sql += " ORDER BY criado_em DESC"
        rows = self.client.execute_query(sql, tuple(params))
        columns = ["notif_id", "destinatario", "tipo", "seg_id", "titulo", "mensagem", "lida", "criado_em"]
        return [dict(zip(columns, row)) for row in rows]

    def marcar_lida(self, notif_id: str) -> bool:
        """Marca uma notificação como lida."""
        sql = """
            UPDATE plataforma.segmentacao.seg_notificacao
            SET lida = true
            WHERE notif_id = ?
        """
        rows = self.client.execute_insert(sql, (notif_id,))
        return rows > 0

    def buscar_notificacao(self, notif_id: str) -> Optional[Dict]:
        sql = """
            SELECT notif_id, destinatario, tipo, seg_id, titulo, mensagem, lida, criado_em
            FROM plataforma.segmentacao.seg_notificacao
            WHERE notif_id = ?
        """
        rows = self.client.execute_query(sql, (notif_id,))
        if rows:
            columns = ["notif_id", "destinatario", "tipo", "seg_id", "titulo", "mensagem", "lida", "criado_em"]
            return dict(zip(columns, rows[0]))
        return None