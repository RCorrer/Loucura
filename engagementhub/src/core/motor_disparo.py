"""Motor de Disparo S3 (BACK-08).

Consome a fila_disparo, renderiza peças e envia via providers (email/WhatsApp).
Executado como Job (~5min) ou via API admin.

Fluxo por item da fila:
1. Re-validar governança (janela de envio)
2. Carregar peça + variáveis do cliente
3. Renderizar via render_engine
4. Disparar via provider (email/whatsapp)
5. Registrar resultado em tracking_disparo + disparo_tentativa
6. Retry com backoff se falha temporária; marcar 'falha' se permanente

Idempotência: fila_id é usado como envio_id no tracking (1:1).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.core.config import (
    TABLE_CONFIG_JANELA,
    TABLE_CONFIG_RETRY,
    TABLE_DISPARO_TENTATIVA,
    TABLE_FILA,
    TABLE_GOLDEN_RECORD,
    TABLE_PECA,
    TABLE_TRACKING,
)
from src.core.render_engine import render_preview
from src.db.databricks_client import get_client
from src.providers.base import DispatchResult
from src.providers.registry import get_provider_by_canal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gerar_id(prefixo: str) -> str:
    return f"{prefixo}_{uuid4().hex[:16]}"


# ---------------------------------------------------------------------------
# Carregar dados
# ---------------------------------------------------------------------------

def carregar_fila_pendente(batch_size: int = 200, client=None) -> list[dict[str, Any]]:
    """Busca itens prontos para disparo (pendente + agendado_para <= now)."""
    client = client or get_client()
    agora = utc_now().isoformat()
    rows = client.fetch_all(
        f"""
        SELECT fila_id, cpf_cnpj, campanha_id, jornada_id, no_id,
               peca_id, canal, destinatario, agendado_para,
               prioridade, tentativas
        FROM {TABLE_FILA}
        WHERE status = 'pendente'
          AND agendado_para <= ?
        ORDER BY prioridade ASC, agendado_para ASC
        LIMIT ?
        """,
        (agora, batch_size),
    )
    return [
        {
            "fila_id": r[0],
            "cpf_cnpj": r[1],
            "campanha_id": r[2],
            "jornada_id": r[3],
            "no_id": r[4],
            "peca_id": r[5],
            "canal": r[6],
            "destinatario": r[7],
            "agendado_para": r[8],
            "prioridade": r[9],
            "tentativas": int(r[10] or 0),
        }
        for r in (rows or [])
    ]


def carregar_peca(peca_id: str, client=None) -> dict[str, Any] | None:
    """Carrega conteúdo da peça para renderização."""
    client = client or get_client()
    row = client.fetch_one(
        f"""
        SELECT peca_id, canal, conteudo_json, html_renderizado, assunto,
               template_meta_id, variaveis_usadas
        FROM {TABLE_PECA}
        WHERE peca_id = ?
        """,
        (peca_id,),
    )
    if not row:
        return None
    return {
        "peca_id": row[0],
        "canal": row[1],
        "conteudo_json": row[2],
        "html_renderizado": row[3],
        "assunto": row[4],
        "template_meta_id": row[5],
        "variaveis_usadas": json.loads(row[6]) if row[6] else [],
    }


def carregar_variaveis_cliente(cpf_cnpj: str, client=None) -> dict[str, Any]:
    """Carrega variáveis de personalização do golden_record."""
    client = client or get_client()
    row = client.fetch_one(
        f"SELECT nome, primeiro_nome, email, telefone, agencia, conta FROM {TABLE_GOLDEN_RECORD} WHERE cpf_cnpj = ?",
        (cpf_cnpj,),
    )
    if not row:
        return {"cpf_cnpj": cpf_cnpj}
    return {
        "cpf_cnpj": cpf_cnpj,
        "nome": row[0] or "",
        "primeiro_nome": row[1] or "",
        "email": row[2] or "",
        "telefone": row[3] or "",
        "agencia": row[4] or "",
        "conta": row[5] or "",
    }


def carregar_config_janela(canal: str, client=None) -> dict[str, Any] | None:
    """Carrega janela de envio ativa para o canal."""
    client = client or get_client()
    row = client.fetch_one(
        f"""
        SELECT hora_inicio, hora_fim, dias_semana, timezone
        FROM {TABLE_CONFIG_JANELA}
        WHERE canal = ? AND ativo = 1
        """,
        (canal,),
    )
    if not row:
        return None
    return {
        "hora_inicio": int(row[0]) if row[0] is not None else 0,
        "hora_fim": int(row[1]) if row[1] is not None else 23,
        "dias_semana": row[2],
        "timezone": row[3] or "America/Sao_Paulo",
    }


def carregar_config_retry(canal: str, client=None) -> dict[str, Any]:
    """Carrega política de retry para o canal."""
    client = client or get_client()
    row = client.fetch_one(
        f"SELECT max_tentativas, backoff_minutos FROM {TABLE_CONFIG_RETRY} WHERE canal = ? AND ativo = 1",
        (canal,),
    )
    if not row:
        return {"max_tentativas": 3, "backoff_minutos": "5,15,60"}
    return {
        "max_tentativas": int(row[0]) if row[0] else 3,
        "backoff_minutos": row[1] or "5,15,60",
    }


# ---------------------------------------------------------------------------
# Validações pré-disparo
# ---------------------------------------------------------------------------

def validar_janela_envio(canal: str, client=None) -> tuple[bool, str]:
    """Verifica se o momento atual está dentro da janela de envio.

    Returns:
        (permitido, motivo)
    """
    config = carregar_config_janela(canal, client)
    if not config:
        return True, "sem_janela_configurada"  # Sem janela = sempre permitido

    agora = utc_now()
    hora_atual = agora.hour  # UTC simplificado (prod usaria pytz)

    # Verificar hora
    if not (config["hora_inicio"] <= hora_atual <= config["hora_fim"]):
        return False, f"fora_janela_horario ({hora_atual}h, permitido {config['hora_inicio']}-{config['hora_fim']})"

    # Verificar dia da semana (0=seg, 6=dom)
    dias_semana = config.get("dias_semana")
    if dias_semana:
        try:
            dias_permitidos = json.loads(dias_semana) if isinstance(dias_semana, str) else dias_semana
            dia_atual = agora.weekday()
            if dia_atual not in dias_permitidos:
                return False, f"fora_janela_dia (dia={dia_atual}, permitidos={dias_permitidos})"
        except (json.JSONDecodeError, TypeError):
            pass

    return True, "ok"


def verificar_idempotencia(fila_id: str, client=None) -> bool:
    """Retorna True se já existe tracking para este fila_id (já enviado)."""
    client = client or get_client()
    row = client.fetch_one(
        f"SELECT 1 FROM {TABLE_TRACKING} WHERE envio_id = ? LIMIT 1",
        (fila_id,),
    )
    return row is not None


# ---------------------------------------------------------------------------
# Renderização
# ---------------------------------------------------------------------------

def renderizar_peca(
    peca: dict[str, Any],
    variaveis: dict[str, Any],
) -> dict[str, Any]:
    """Renderiza peça com variáveis reais do cliente.

    Returns:
        {html, texto, assunto_renderizado} ou {erro}
    """
    canal = peca["canal"]
    conteudo_json = peca.get("conteudo_json")

    if not conteudo_json:
        # Fallback: usar html_renderizado cacheado (sem personalização dinâmica)
        html_cache = peca.get("html_renderizado")
        if html_cache:
            return {"html": html_cache, "texto": None, "assunto_renderizado": peca.get("assunto")}
        return {"erro": "Sem conteudo_json nem html_renderizado"}

    resultado = render_preview(
        conteudo_json=conteudo_json,
        canal=canal,
        variaveis_override=variaveis,
        assunto=peca.get("assunto"),
    )
    return resultado


# ---------------------------------------------------------------------------
# Disparo
# ---------------------------------------------------------------------------

def executar_disparo(
    item: dict[str, Any],
    conteudo_renderizado: dict[str, Any],
) -> DispatchResult:
    """Dispara via provider correspondente ao canal."""
    canal = item["canal"]
    provider = get_provider_by_canal(canal)

    if not provider:
        return DispatchResult(
            success=False,
            error_code="PROVIDER_NOT_FOUND",
            error_detail=f"Nenhum provider registrado para canal '{canal}'",
            retryable=False,
        )

    # Validar destinatário
    if not provider.validar_destinatario(item["destinatario"]):
        return DispatchResult(
            success=False,
            error_code="DESTINATARIO_INVALIDO",
            error_detail=f"Destinatário inválido: {item['destinatario']}",
            retryable=False,
        )

    # Disparar
    try:
        resultado = provider.disparar(
            destinatario=item["destinatario"],
            conteudo_renderizado=conteudo_renderizado,
            metadata={
                "campanha_id": item["campanha_id"],
                "jornada_id": item["jornada_id"],
                "peca_id": item["peca_id"],
                "fila_id": item["fila_id"],
            },
        )
        return resultado
    except Exception as e:
        logger.exception(f"Erro ao disparar {item['fila_id']}: {e}")
        return DispatchResult(
            success=False,
            error_code="EXCEPTION",
            error_detail=str(e)[:500],
            retryable=True,
        )


# ---------------------------------------------------------------------------
# Registro de resultados
# ---------------------------------------------------------------------------

def registrar_tracking(
    item: dict[str, Any],
    resultado: DispatchResult,
    client=None,
):
    """Insere registro no tracking_disparo."""
    client = client or get_client()
    agora = utc_now().isoformat()
    status = "enviado" if resultado.success else "falha"

    client.execute_insert(
        f"""
        INSERT INTO {TABLE_TRACKING}
        (envio_id, cpf_cnpj, campanha_id, jornada_id, peca_id, canal,
         enviado_em, entregue_em, visualizado_em, aberto_em, clicou_em,
         converteu_em, status_atual, erro_detalhe, provider_message_id, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, ?, ?, ?)
        """,
        (
            item["fila_id"],  # envio_id = fila_id (idempotência)
            item["cpf_cnpj"],
            item["campanha_id"],
            item["jornada_id"],
            item["peca_id"],
            item["canal"],
            agora if resultado.success else None,
            status,
            resultado.error_detail,
            resultado.provider_message_id,
            agora,
        ),
    )


def registrar_tentativa(
    item: dict[str, Any],
    resultado: DispatchResult,
    numero_tentativa: int,
    client=None,
):
    """Insere registro na disparo_tentativa."""
    client = client or get_client()
    agora = utc_now().isoformat()

    status_tent = "sucesso" if resultado.success else (
        "falha_temporaria" if resultado.retryable else "falha_permanente"
    )

    client.execute_insert(
        f"""
        INSERT INTO {TABLE_DISPARO_TENTATIVA}
        (tentativa_id, fila_id, cpf_cnpj, numero_tentativa,
         resultado, erro_detalhe, provider_response, executado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            gerar_id("tent"),
            item["fila_id"],
            item["cpf_cnpj"],
            numero_tentativa,
            status_tent,
            resultado.error_detail,
            resultado.provider_message_id,
            agora,
        ),
    )


def atualizar_fila(
    fila_id: str,
    novo_status: str,
    tentativas: int,
    client=None,
):
    """Atualiza status e tentativas na fila_disparo."""
    client = client or get_client()
    agora = utc_now().isoformat()
    client.execute_insert(
        f"""
        UPDATE {TABLE_FILA}
        SET status = ?, tentativas = ?, atualizado_em = ?
        WHERE fila_id = ?
        """,
        (novo_status, tentativas, agora, fila_id),
    )


def agendar_retry(item: dict[str, Any], config_retry: dict, client=None):
    """Reagenda o item na fila com backoff."""
    client = client or get_client()
    backoff_str = config_retry.get("backoff_minutos", "5,15,60")
    backoffs = [int(x.strip()) for x in backoff_str.split(",")]

    tentativa_atual = item["tentativas"]
    idx = min(tentativa_atual, len(backoffs) - 1)
    minutos = backoffs[idx]

    from datetime import timedelta
    proximo = (utc_now() + timedelta(minutes=minutos)).isoformat()

    client.execute_insert(
        f"""
        UPDATE {TABLE_FILA}
        SET status = 'pendente', tentativas = ?, agendado_para = ?, atualizado_em = ?
        WHERE fila_id = ?
        """,
        (tentativa_atual + 1, proximo, utc_now().isoformat(), item["fila_id"]),
    )


# ---------------------------------------------------------------------------
# Processar um item
# ---------------------------------------------------------------------------

def processar_item(item: dict[str, Any], client=None) -> dict[str, Any]:
    """Processa um único item da fila de disparo.

    Returns:
        {status, detalhe}
    """
    client = client or get_client()

    # 1. Idempotência: já enviado?
    if verificar_idempotencia(item["fila_id"], client):
        atualizar_fila(item["fila_id"], "enviado", item["tentativas"], client)
        return {"status": "skip", "detalhe": "ja_enviado (idempotencia)"}

    # 2. Validar janela de envio
    janela_ok, motivo_janela = validar_janela_envio(item["canal"], client)
    if not janela_ok:
        # Não suprimir — apenas adiar (volta pra fila)
        return {"status": "adiado", "detalhe": motivo_janela}

    # 3. Carregar peça
    peca = carregar_peca(item["peca_id"], client) if item["peca_id"] else None
    if not peca:
        atualizar_fila(item["fila_id"], "falha", item["tentativas"], client)
        return {"status": "falha", "detalhe": f"peca_id={item['peca_id']} nao encontrada"}

    # 4. Carregar variáveis do cliente
    variaveis = carregar_variaveis_cliente(item["cpf_cnpj"], client)

    # 5. Renderizar
    conteudo = renderizar_peca(peca, variaveis)
    if conteudo.get("erro"):
        atualizar_fila(item["fila_id"], "falha", item["tentativas"], client)
        return {"status": "falha", "detalhe": f"render_erro: {conteudo['erro']}"}

    # 6. Disparar
    resultado = executar_disparo(item, conteudo)
    numero_tentativa = item["tentativas"] + 1

    # 7. Registrar tentativa
    registrar_tentativa(item, resultado, numero_tentativa, client)

    # 8. Tratar resultado
    if resultado.success:
        atualizar_fila(item["fila_id"], "enviado", numero_tentativa, client)
        registrar_tracking(item, resultado, client)
        return {"status": "enviado", "detalhe": f"provider_msg={resultado.provider_message_id}"}
    else:
        # Verificar retry
        config_retry = carregar_config_retry(item["canal"], client)
        max_tent = config_retry["max_tentativas"]

        if resultado.retryable and numero_tentativa < max_tent:
            agendar_retry(item, config_retry, client)
            return {"status": "retry", "detalhe": f"tentativa {numero_tentativa}/{max_tent}: {resultado.error_detail}"}
        else:
            # Falha permanente ou max tentativas atingido
            atualizar_fila(item["fila_id"], "falha", numero_tentativa, client)
            registrar_tracking(item, resultado, client)
            return {"status": "falha", "detalhe": f"permanente: {resultado.error_code} - {resultado.error_detail}"}


# ---------------------------------------------------------------------------
# EXECUTOR PRINCIPAL
# ---------------------------------------------------------------------------

def executar_motor_disparo(batch_size: int = 200, client=None) -> dict[str, Any]:
    """Executa o motor de disparo: consome fila e envia.

    Returns:
        Métricas consolidadas.
    """
    client = client or get_client()

    fila = carregar_fila_pendente(batch_size, client)

    metricas = {
        "total_fila": len(fila),
        "enviados": 0,
        "falhas": 0,
        "retries": 0,
        "adiados": 0,
        "skips": 0,
        "erros_detalhe": [],
    }

    for item in fila:
        try:
            resultado = processar_item(item, client)
            status = resultado["status"]

            if status == "enviado":
                metricas["enviados"] += 1
            elif status == "falha":
                metricas["falhas"] += 1
                metricas["erros_detalhe"].append({
                    "fila_id": item["fila_id"],
                    "detalhe": resultado["detalhe"],
                })
            elif status == "retry":
                metricas["retries"] += 1
            elif status == "adiado":
                metricas["adiados"] += 1
            elif status == "skip":
                metricas["skips"] += 1

        except Exception as e:
            logger.exception(f"Erro inesperado processando {item['fila_id']}: {e}")
            metricas["falhas"] += 1
            metricas["erros_detalhe"].append({
                "fila_id": item["fila_id"],
                "detalhe": f"exception: {str(e)[:200]}",
            })

    # Limitar detalhes no retorno
    metricas["erros_detalhe"] = metricas["erros_detalhe"][:20]

    logger.info(
        f"✓ Motor Disparo: {metricas['total_fila']} na fila, "
        f"{metricas['enviados']} enviados, {metricas['falhas']} falhas, "
        f"{metricas['retries']} retries, {metricas['adiados']} adiados"
    )
    return metricas
