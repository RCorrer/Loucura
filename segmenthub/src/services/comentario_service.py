"""
Service para comentários e notificações.
"""

from typing import List, Dict, Optional
from src.repositories.comentario_repository import ComentarioRepository


class ComentarioService:
    def __init__(self):
        self.repository = ComentarioRepository()

    # ========== COMENTÁRIOS ==========

    def listar_comentarios(self, seg_id: str) -> List[Dict]:
        """Lista comentários em thread aninhada."""
        comentarios = self.repository.listar_comentarios(seg_id)

        # Converte arrays (ex: mencoes) para listas Python
        for c in comentarios:
            if "mencoes" in c and hasattr(c["mencoes"], "tolist"):
                c["mencoes"] = c["mencoes"].tolist()

        # Constrói a árvore de respostas
        comentarios_por_id = {c["comentario_id"]: c for c in comentarios}
        raizes = []
        for c in comentarios:
            c["respostas"] = []
            if c.get("respondendo_a") and c["respondendo_a"] in comentarios_por_id:
                pai = comentarios_por_id[c["respondendo_a"]]
                pai["respostas"].append(c)
            else:
                raizes.append(c)
        return raizes

    def criar_comentario(
        self,
        seg_id: str,
        texto: str,
        autor: str,
        tipo: str = "geral",
        versao_referencia: Optional[int] = None,
        respondendo_a: Optional[str] = None,
        mencoes: Optional[List[str]] = None,
    ) -> Dict:
        """Cria um comentário e gera notificações para menções."""
        dados = {
            "seg_id": seg_id,
            "versao_referencia": versao_referencia,
            "tipo": tipo,
            "autor": autor,
            "texto": texto,
            "respondendo_a": respondendo_a,
            "mencoes": mencoes or [],
            "resolvido": False,
        }
        comentario_id = self.repository.criar_comentario(dados)

        # Gera notificações para menções
        if mencoes:
            for usuario in mencoes:
                if usuario != autor:  # não notificar a si mesmo
                    self.repository.criar_notificacao({
                        "destinatario": usuario,
                        "tipo": "mencao",
                        "seg_id": seg_id,
                        "titulo": "Menção em comentário",
                        "mensagem": f"{autor} mencionou você em um comentário: {texto[:80]}...",
                    })

        return {"comentario_id": comentario_id}

    def editar_comentario(self, comentario_id: str, texto: Optional[str] = None, resolvido: Optional[bool] = None) -> bool:
        """Edita texto ou marca resolvido."""
        return self.repository.atualizar_comentario(comentario_id, texto, resolvido)

    # ========== NOTIFICAÇÕES ==========

    def listar_notificacoes(self, destinatario: str, lida: Optional[bool] = None) -> List[Dict]:
        return self.repository.listar_notificacoes(destinatario, lida)

    def marcar_lida(self, notif_id: str) -> bool:
        return self.repository.marcar_lida(notif_id)