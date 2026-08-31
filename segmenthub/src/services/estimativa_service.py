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

        Estratégia:
          - Sempre roda query de inclusão-only (sem exclusão) → contagem bruta
          - Se há regras de exclusão, roda query líquida (inclusão AND NOT exclusão)
          - Deriva exclusão = inclusão_bruta − líquida
        """
        start_time = time.time()

        # 1. Valida as regras
        erros = self.validator.validar_regras(regras)
        if erros:
            raise ValueError(f"Regras inválidas: {erros}")

        # 2. Contagem só com inclusão (sem exclusão)
        sql_inclusao, params_inc = self.engine.generate_inclusao_only_query(regras)
        contagem_inclusao = self.repository.executar_estimativa(sql_inclusao, tuple(params_inc))

        # 3. Se há exclusão, calcula líquido e deriva o delta
        contagem_liquida = contagem_inclusao
        contagem_exclusao = 0

        if regras.exclusao and regras.exclusao.rules:
            sql_liquida, params_liq = self.engine.generate_estimativa_query(regras)
            contagem_liquida = self.repository.executar_estimativa(sql_liquida, tuple(params_liq))
            contagem_exclusao = max(0, contagem_inclusao - contagem_liquida)

        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "estimativa": contagem_liquida,
            "inclusao": contagem_inclusao,
            "exclusao": contagem_exclusao,
            "tempo_ms": elapsed_ms,
        }