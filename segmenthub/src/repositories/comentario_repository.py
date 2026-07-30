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
            SELECT *
            FROM plataforma.segmentacao.seg_comentario
            WHERE seg_id = ?
            ORDER BY criado_em ASC
        """
        return self.client.execute_query(sql, (seg_id,))

    def criar_comentario(self, dados: Dict) -> str:
        """Insere um novo comentário e retorna o ID."""
        comentario_id = f"com_{uuid.uuid4().hex[:12]}"
        dados["comentario_id"] = comentario_id
        sql = """
            INSERT INTO plataforma.segmentacao.seg_comentario
            (comentario_id, seg_id, versao_referencia, tipo, autor, texto, respondendo_a, mencoes, resolvido, criado_em, editado_em)
            VALUES (
                :comentario_id, :seg_id, :versao_referencia, :tipo, :autor, :texto, :respondendo_a, :mencoes, :resolvido, current_timestamp(), NULL
            )
        """
        self.client.execute_insert(sql, dados)
        return comentario_id

    def atualizar_comentario(self, comentario_id: str, texto: Optional[str] = None, resolvido: Optional[bool] = None) -> bool:
        """Atualiza texto e/ou resolvido de um comentário."""
        set_parts = []
        params = {"comentario_id": comentario_id}
        if texto is not None:
            set_parts.append("texto = :texto")
            params["texto"] = texto
        if resolvido is not None:
            set_parts.append("resolvido = :resolvido")
            params["resolvido"] = resolvido
        if not set_parts:
            return True  # nada a atualizar
        set_parts.append("editado_em = current_timestamp()")
        sql = f"""
            UPDATE plataforma.segmentacao.seg_comentario
            SET {", ".join(set_parts)}
            WHERE comentario_id = :comentario_id
        """
        rows = self.client.execute_insert(sql, params)
        return rows > 0

    def criar_notificacao(self, dados: Dict) -> str:
        """Insere uma notificação e retorna o ID."""
        notif_id = f"notif_{uuid.uuid4().hex[:12]}"
        dados["notif_id"] = notif_id
        sql = """
            INSERT INTO plataforma.segmentacao.seg_notificacao
            (notif_id, destinatario, tipo, seg_id, titulo, mensagem, lida, criado_em)
            VALUES (
                :notif_id, :destinatario, :tipo, :seg_id, :titulo, :mensagem, false, current_timestamp()
            )
        """
        self.client.execute_insert(sql, dados)
        return notif_id

    def listar_notificacoes(self, destinatario: str, lida: Optional[bool] = None) -> List[Dict]:
        """Lista notificações de um usuário."""
        sql = """
            SELECT * FROM plataforma.segmentacao.seg_notificacao
            WHERE destinatario = ?
        """
        params = [destinatario]
        if lida is not None:
            sql += " AND lida = ?"
            params.append(lida)
        sql += " ORDER BY criado_em DESC"
        return self.client.execute_query(sql, tuple(params))

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
        sql = "SELECT * FROM plataforma.segmentacao.seg_notificacao WHERE notif_id = ?"
        result = self.client.execute_query(sql, (notif_id,))
        return result[0] if result else None