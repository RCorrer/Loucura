"""Multi-Armed Bandit — Thompson Sampling (BACK-11).

Otimização automática de variantes em nós ab_split:
- Recalcula pesos via Thompson Sampling (Beta distribution)
- Respeita tráfego mínimo antes de convergir
- Permite pausar variante e fixar vencedora

Executado pelo JOB-04 (otimizador_mab) ou via API admin.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.core.config import (
    TABLE_CONFIG_OTIMIZACAO,
    TABLE_OTIMIZACAO_HISTORICO,
    TABLE_OTIMIZACAO_RESULTADO,
    TABLE_OTIMIZACAO_VARIANTE,
)
from src.db.databricks_client import get_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _beta_sample(alpha: float, beta_param: float) -> float:
    """Amostra de distribuição Beta(alpha, beta).

    Para Thompson Sampling:
    - alpha = sucessos + 1 (prior)
    - beta  = fracassos + 1 (prior)
    """
    # Prior fraco: Beta(1,1) = Uniforme
    a = max(alpha, 0.01)
    b = max(beta_param, 0.01)
    return random.betavariate(a, b)


# ---------------------------------------------------------------------------
# Carregar dados
# ---------------------------------------------------------------------------

def carregar_config_otimizacao(escopo: str = "global", client=None) -> dict[str, Any]:
    """Carrega configuração de otimização."""
    client = client or get_client()
    row = client.fetch_one(
        f"""
        SELECT metrica_alvo, janela_avaliacao_horas, trafego_minimo_pct,
               min_amostras_por_variante, frequencia_recalculo, otimizacao_ativa
        FROM {TABLE_CONFIG_OTIMIZACAO}
        WHERE escopo = ? AND ativo = 1
        """,
        (escopo,),
    )
    if not row:
        # Defaults conservadores
        return {
            "metrica_alvo": "aberturas",
            "janela_avaliacao_horas": 72,
            "trafego_minimo_pct": 10.0,
            "min_amostras_por_variante": 100,
            "frequencia_recalculo": "diario",
            "otimizacao_ativa": True,
        }
    return {
        "metrica_alvo": row[0] or "aberturas",
        "janela_avaliacao_horas": int(row[1] or 72),
        "trafego_minimo_pct": float(row[2] or 10.0),
        "min_amostras_por_variante": int(row[3] or 100),
        "frequencia_recalculo": row[4] or "diario",
        "otimizacao_ativa": bool(row[5]),
    }


def carregar_variantes(jornada_id: str | None = None, client=None) -> list[dict[str, Any]]:
    """Carrega variantes ativas, opcionalmente filtradas por jornada."""
    client = client or get_client()
    if jornada_id:
        rows = client.fetch_all(
            f"""
            SELECT variante_id, jornada_id, no_id, peca_id, rotulo, peso_atual, ativo
            FROM {TABLE_OTIMIZACAO_VARIANTE}
            WHERE jornada_id = ? AND ativo = 1
            """,
            (jornada_id,),
        )
    else:
        rows = client.fetch_all(
            f"SELECT variante_id, jornada_id, no_id, peca_id, rotulo, peso_atual, ativo FROM {TABLE_OTIMIZACAO_VARIANTE} WHERE ativo = 1"
        )
    return [
        {
            "variante_id": r[0], "jornada_id": r[1], "no_id": r[2],
            "peca_id": r[3], "rotulo": r[4], "peso_atual": float(r[5] or 0.5),
            "ativo": bool(r[6]),
        }
        for r in (rows or [])
    ]


def carregar_resultados(variante_id: str, client=None) -> dict[str, int]:
    """Carrega resultados agregados de uma variante (soma de todas as janelas)."""
    client = client or get_client()
    row = client.fetch_one(
        f"""
        SELECT COALESCE(SUM(envios), 0), COALESCE(SUM(aberturas), 0),
               COALESCE(SUM(cliques), 0), COALESCE(SUM(conversoes), 0)
        FROM {TABLE_OTIMIZACAO_RESULTADO}
        WHERE variante_id = ?
        """,
        (variante_id,),
    )
    if not row:
        return {"envios": 0, "aberturas": 0, "cliques": 0, "conversoes": 0}
    return {
        "envios": int(row[0]),
        "aberturas": int(row[1]),
        "cliques": int(row[2]),
        "conversoes": int(row[3]),
    }


# ---------------------------------------------------------------------------
# Thompson Sampling
# ---------------------------------------------------------------------------

def calcular_pesos_thompson(
    variantes: list[dict[str, Any]],
    config: dict[str, Any],
    client=None,
) -> list[dict[str, Any]]:
    """Recalcula pesos de variantes via Thompson Sampling.

    Para cada variante:
    1. Carrega resultados (envios, métrica-alvo)
    2. Calcula alpha (sucessos) e beta (fracassos)
    3. Amostra N vezes da distribuição Beta
    4. Peso = proporção de vitórias no sampling

    Returns:
        Lista com {variante_id, peso_anterior, peso_novo, motivo}
    """
    client = client or get_client()
    metrica = config["metrica_alvo"]  # aberturas, cliques, conversoes
    min_amostras = config["min_amostras_por_variante"]
    trafego_min_pct = config["trafego_minimo_pct"] / 100.0

    N_SIMULACOES = 10000
    n_variantes = len(variantes)

    if n_variantes < 2:
        return []  # Precisa de pelo menos 2 variantes para otimizar

    # Coletar resultados de cada variante
    dados = []
    todas_prontas = True
    for v in variantes:
        resultados = carregar_resultados(v["variante_id"], client)
        envios = resultados["envios"]
        sucessos = resultados.get(metrica, resultados["aberturas"])

        # Verificar tráfego mínimo
        if envios < min_amostras:
            todas_prontas = False

        dados.append({
            "variante_id": v["variante_id"],
            "jornada_id": v["jornada_id"],
            "peso_anterior": v["peso_atual"],
            "envios": envios,
            "sucessos": sucessos,
            "fracassos": max(envios - sucessos, 0),
        })

    # Se nenhuma variante tem amostras suficientes, manter pesos uniformes
    if not todas_prontas:
        peso_uniforme = round(1.0 / n_variantes, 4)
        return [
            {
                "variante_id": d["variante_id"],
                "peso_anterior": d["peso_anterior"],
                "peso_novo": peso_uniforme,
                "motivo": f"trafego_insuficiente (envios={d['envios']}, min={min_amostras})",
            }
            for d in dados
        ]

    # Thompson Sampling: simular N_SIMULACOES rodadas
    vitorias = [0] * n_variantes
    for _ in range(N_SIMULACOES):
        amostras = []
        for d in dados:
            alpha = d["sucessos"] + 1  # Prior Beta(1,1)
            beta_param = d["fracassos"] + 1
            amostras.append(_beta_sample(alpha, beta_param))

        # Quem ganhou esta simulação?
        vencedor_idx = amostras.index(max(amostras))
        vitorias[vencedor_idx] += 1

    # Pesos = proporção de vitórias
    resultados_calc = []
    for i, d in enumerate(dados):
        peso_bruto = vitorias[i] / N_SIMULACOES

        # Garantir tráfego mínimo: nenhuma variante pode ter menos que trafego_min_pct
        peso_novo = max(peso_bruto, trafego_min_pct)
        peso_novo = round(peso_novo, 4)

        resultados_calc.append({
            "variante_id": d["variante_id"],
            "peso_anterior": d["peso_anterior"],
            "peso_novo": peso_novo,
            "motivo": f"thompson (vitorias={vitorias[i]}/{N_SIMULACOES}, taxa={d['sucessos']}/{d['envios']})",
        })

    # Normalizar pesos para somar 1.0
    soma = sum(r["peso_novo"] for r in resultados_calc)
    if soma > 0:
        for r in resultados_calc:
            r["peso_novo"] = round(r["peso_novo"] / soma, 4)

    return resultados_calc


# ---------------------------------------------------------------------------
# Aplicar pesos
# ---------------------------------------------------------------------------

def aplicar_pesos(
    resultados: list[dict[str, Any]],
    client=None,
):
    """Atualiza pesos no banco e registra histórico."""
    client = client or get_client()
    agora = _utc_now()

    for r in resultados:
        # Atualizar peso na variante
        client.execute_insert(
            f"UPDATE {TABLE_OTIMIZACAO_VARIANTE} SET peso_atual = ? WHERE variante_id = ?",
            (r["peso_novo"], r["variante_id"]),
        )

        # Registrar histórico
        client.execute_insert(
            f"""
            INSERT INTO {TABLE_OTIMIZACAO_HISTORICO}
            (hist_id, variante_id, jornada_id, peso_anterior, peso_novo, motivo, recalculado_em)
            VALUES (?, ?, NULL, ?, ?, ?, ?)
            """,
            (
                f"mab_{uuid4().hex[:12]}",
                r["variante_id"],
                r["peso_anterior"],
                r["peso_novo"],
                r["motivo"],
                agora,
            ),
        )


# ---------------------------------------------------------------------------
# Ações administrativas
# ---------------------------------------------------------------------------

def pausar_variante(variante_id: str, motivo: str = "pausada_manual", client=None):
    """Pausa uma variante (peso=0, ativo=0). Redistribui peso para as demais."""
    client = client or get_client()
    agora = _utc_now()

    # Buscar variante
    row = client.fetch_one(
        f"SELECT jornada_id, peso_atual FROM {TABLE_OTIMIZACAO_VARIANTE} WHERE variante_id = ?",
        (variante_id,),
    )
    if not row:
        return {"erro": "Variante não encontrada"}

    jornada_id, peso_antigo = row[0], float(row[1] or 0)

    # Desativar
    client.execute_insert(
        f"UPDATE {TABLE_OTIMIZACAO_VARIANTE} SET ativo = 0, peso_atual = 0 WHERE variante_id = ?",
        (variante_id,),
    )

    # Redistribuir peso entre as restantes
    restantes = carregar_variantes(jornada_id, client)
    if restantes:
        redistribuir = peso_antigo / len(restantes)
        for v in restantes:
            novo_peso = round(v["peso_atual"] + redistribuir, 4)
            client.execute_insert(
                f"UPDATE {TABLE_OTIMIZACAO_VARIANTE} SET peso_atual = ? WHERE variante_id = ?",
                (novo_peso, v["variante_id"]),
            )

    # Histórico
    client.execute_insert(
        f"""
        INSERT INTO {TABLE_OTIMIZACAO_HISTORICO}
        (hist_id, variante_id, jornada_id, peso_anterior, peso_novo, motivo, recalculado_em)
        VALUES (?, ?, ?, ?, 0, ?, ?)
        """,
        (f"mab_{uuid4().hex[:12]}", variante_id, jornada_id, peso_antigo, motivo, agora),
    )

    return {"variante_id": variante_id, "status": "pausada", "peso_redistribuido": peso_antigo}


def fixar_vencedora(variante_id: str, client=None) -> dict[str, Any]:
    """Fixa uma variante como vencedora (peso=1.0, demais=0).

    Desativa otimização para esta jornada/nó (congela pesos).
    """
    client = client or get_client()
    agora = _utc_now()

    # Buscar variante
    row = client.fetch_one(
        f"SELECT jornada_id, no_id, peso_atual FROM {TABLE_OTIMIZACAO_VARIANTE} WHERE variante_id = ?",
        (variante_id,),
    )
    if not row:
        return {"erro": "Variante não encontrada"}

    jornada_id, no_id, peso_antigo = row[0], row[1], float(row[2] or 0)

    # Buscar todas as variantes do mesmo nó
    todas = client.fetch_all(
        f"SELECT variante_id, peso_atual FROM {TABLE_OTIMIZACAO_VARIANTE} WHERE jornada_id = ? AND no_id = ?",
        (jornada_id, no_id),
    )

    # Zerar todas e colocar 1.0 na vencedora
    for v_row in (todas or []):
        vid = v_row[0]
        peso_ant = float(v_row[1] or 0)
        novo_peso = 1.0 if vid == variante_id else 0.0
        ativo = 1 if vid == variante_id else 0

        client.execute_insert(
            f"UPDATE {TABLE_OTIMIZACAO_VARIANTE} SET peso_atual = ?, ativo = ? WHERE variante_id = ?",
            (novo_peso, ativo, vid),
        )

        client.execute_insert(
            f"""
            INSERT INTO {TABLE_OTIMIZACAO_HISTORICO}
            (hist_id, variante_id, jornada_id, peso_anterior, peso_novo, motivo, recalculado_em)
            VALUES (?, ?, ?, ?, ?, 'fixar_vencedora', ?)
            """,
            (f"mab_{uuid4().hex[:12]}", vid, jornada_id, peso_ant, novo_peso, agora),
        )

    return {
        "variante_id": variante_id,
        "status": "fixada",
        "peso": 1.0,
        "demais_desativadas": len([v for v in (todas or []) if v[0] != variante_id]),
    }


# ---------------------------------------------------------------------------
# EXECUTOR PRINCIPAL (chamado pelo JOB-04)
# ---------------------------------------------------------------------------

def executar_otimizador_mab(client=None) -> dict[str, Any]:
    """Executa recalculo MAB para todas as jornadas ativas.

    Returns:
        Métricas consolidadas.
    """
    client = client or get_client()
    config = carregar_config_otimizacao("global", client)

    if not config["otimizacao_ativa"]:
        return {"status": "desativada", "recalculos": 0}

    # Buscar todas as variantes ativas, agrupar por jornada+nó
    todas_variantes = carregar_variantes(client=client)

    # Agrupar por (jornada_id, no_id)
    grupos: dict[tuple, list] = {}
    for v in todas_variantes:
        key = (v["jornada_id"], v["no_id"])
        grupos.setdefault(key, []).append(v)

    metricas = {
        "grupos_processados": 0,
        "variantes_atualizadas": 0,
        "grupos_insuficientes": 0,
    }

    for (jornada_id, no_id), variantes in grupos.items():
        if len(variantes) < 2:
            continue  # Precisa de 2+ variantes

        resultados = calcular_pesos_thompson(variantes, config, client)

        if resultados:
            # Checar se houve mudança significativa (> 1%)
            mudou = any(
                abs(r["peso_novo"] - r["peso_anterior"]) > 0.01
                for r in resultados
            )
            if mudou:
                aplicar_pesos(resultados, client)
                metricas["variantes_atualizadas"] += len(resultados)

            if "trafego_insuficiente" in (resultados[0].get("motivo", "")):
                metricas["grupos_insuficientes"] += 1

        metricas["grupos_processados"] += 1

    logger.info(
        f"✓ MAB: {metricas['grupos_processados']} grupos, "
        f"{metricas['variantes_atualizadas']} variantes atualizadas"
    )
    return metricas
