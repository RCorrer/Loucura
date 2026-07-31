"""
Service para saúde e overlap.
"""

from typing import List, Dict, Optional
from src.repositories.saude_repository import SaudeRepository

class SaudeService:
    """Serviço para operações de saúde e overlap."""

    def __init__(self):
        self.repository = SaudeRepository()

    def dashboard(self) -> Dict:
        """Retorna dashboard consolidado de saúde."""
        saudavel = self.repository.listar_saude()
        contagem = self.repository.contar_por_status()
        ultima = self.repository.ultima_atualizacao()

        total = len(saudavel)

        detalhes = [
            {
                "seg_id": row["seg_id"],
                "health_status": row.get("health_status"),
                "ultima_verificacao": row.get("ultima_verificacao"),
                "variacao_publico_pct": row.get("variacao_publico_pct"),
                "taxa_sucesso_exec": row.get("taxa_sucesso_exec"),
                "tempo_medio_exec_seg": row.get("tempo_medio_exec_seg"),
                "alertas_json": row.get("alertas_json"),
                "publico_atual": row.get("publico_atual"),
            }
            for row in saudavel
        ]

        return {
            "total_segmentacoes": total,
            "verde": contagem.get("verde", 0),
            "amarelo": contagem.get("amarelo", 0),
            "vermelho": contagem.get("vermelho", 0),
            "sem_dados": contagem.get("sem_dados", 0),
            "ultima_atualizacao": ultima.get("ultima_atualizacao") if ultima else None,
            "detalhes": detalhes,
        }

    def detalhe_saude(self, seg_id: str) -> Optional[Dict]:
        """Retorna saúde detalhada de uma segmentação."""
        dados = self.repository.buscar_saude_por_seg_id(seg_id)
        if dados:
            # Converte alertas_json de string para dict se for string
            if dados.get("alertas_json") and isinstance(dados["alertas_json"], str):
                import json
                try:
                    dados["alertas_json"] = json.loads(dados["alertas_json"])
                except:
                    pass
            return dados
        return None

    def listar_overlaps(self, seg_id: str) -> List[Dict]:
        """Retorna sobreposições de um segmento."""
        return self.repository.listar_overlaps(seg_id)