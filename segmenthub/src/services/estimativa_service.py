"""
Service para estimativa de público.
Valida regras, gera SQL de estimativa e executa a contagem.
"""

import time
from typing import Dict, Any
from src.models.regras import RegrasJson
from src.core.validator import RegraValidator
from src.core.query_engine import QueryEngine
from src.repositories.estimativa_repository import EstimativaRepository
from src.exceptions.custom_exceptions import TemaNotFoundError, CampoNotFoundError


class EstimativaService:
    """Serviço para cálculo de estimativa de público."""

    def __init__(self):
        self.validator = RegraValidator()
        self.engine = QueryEngine()
        self.repository = EstimativaRepository()

    def calcular_estimativa(self, regras: RegrasJson) -> Dict[str, Any]:
        """
        Calcula a estimativa de público para as regras fornecidas.
        Retorna: { estimativa, inclusao, exclusao, tempo_ms }
        """
        start_time = time.time()

        # 1. Valida as regras
        erros = self.validator.validar_regras(regras)
        if erros:
            raise ValueError(f"Regras inválidas: {erros}")

        # 2. Gera SQL para estimativa (approx_count_distinct)
        sql_estimativa, params = self.engine.generate_estimativa_query(regras)
        estimativa = self.repository.executar_estimativa(sql_estimativa, tuple(params))

        # 3. (Opcional) Calcula contagem de inclusão e exclusão separadamente
        # Para simplificar, vamos retornar a estimativa total
        # Em uma versão mais completa, poderíamos calcular inclusão e exclusão separadamente

        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "estimativa": estimativa,
            "inclusao": estimativa,  # Simplificado: a estimativa total é a inclusão
            "exclusao": 0,           # Simplificado
            "tempo_ms": elapsed_ms,
        }