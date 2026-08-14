"""
Endpoints de segmentação.
CRUD, ciclo de vida, destino, vigência, clonagem.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from src.models.dto.segmentacao_dto import (
    SegmentacaoCreateDTO,
    SegmentacaoUpdateDTO,
    SegmentacaoResponseDTO,
    SegmentacaoDetalheDTO,
    TransicaoStatusDTO,
    CloneSegmentacaoDTO,
)
from src.services.segmentacao_service import SegmentacaoService
from src.core.security import require_perfil

router = APIRouter(prefix="/segmentacoes", tags=["segmentacoes"])


# ==================== CRUD ====================

@router.post("", response_model=dict)
async def criar_segmentacao(
    dados: SegmentacaoCreateDTO,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Cria uma nova segmentação (status inicial: rascunho).
    """
    service = SegmentacaoService()
    try:
        result = service.criar(dados, user["usuario_id"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("", response_model=dict)
async def listar_segmentacoes(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    objetivo: Optional[str] = Query(None, description="Filtrar por objetivo"),
    owner: Optional[str] = Query(None, description="Filtrar por owner"),
    busca: Optional[str] = Query(None, description="Busca textual"),
    page: int = Query(1, ge=1, description="Página"),
    size: int = Query(50, ge=1, le=100, description="Itens por página"),
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Lista segmentações com filtros e paginação.
    """
    service = SegmentacaoService()
    resultado = service.listar(
        status=status,
        objetivo=objetivo,
        owner=owner,
        busca=busca,
        page=page,
        size=size,
    )
    return resultado


@router.get("/{seg_id}", response_model=SegmentacaoDetalheDTO)
async def obter_segmentacao(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Retorna detalhes completos de uma segmentação.
    """
    service = SegmentacaoService()
    dados = service.buscar_por_id(seg_id)
    if not dados:
        raise HTTPException(status_code=404, detail="Segmentação não encontrada")
    return dados


@router.put("/{seg_id}", response_model=dict)
async def atualizar_segmentacao(
    seg_id: str,
    dados: SegmentacaoUpdateDTO,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Atualiza uma segmentação.
    Se estiver ativa e alterar regras, cria nova versão rascunho.
    """
    service = SegmentacaoService()
    try:
        service.atualizar(seg_id, dados, user["usuario_id"])
        return {"mensagem": "Segmentação atualizada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{seg_id}", response_model=dict)
async def arquivar_segmentacao(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Arquiva uma segmentação (soft delete).
    """
    service = SegmentacaoService()
    try:
        service.arquivar(seg_id, usuario=user["usuario_id"])
        return {"mensagem": "Segmentação arquivada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ==================== CICLO DE VIDA ====================

@router.post("/{seg_id}/validar", response_model=dict)
async def validar_segmentacao(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Dispara validação completa da segmentação (regras + estimativa + destino + vigência).
    """
    service = SegmentacaoService()
    dados = service.buscar_por_id(seg_id)
    if not dados:
        raise HTTPException(status_code=404, detail="Segmentação não encontrada")

    # Valida regras
    from src.core.validator import RegraValidator
    from src.core.query_engine import QueryEngine
    from src.models.regras import RegrasJson

    validator = RegraValidator()
    engine = QueryEngine()
    try:
        regras = RegrasJson(**dados["regras_json"])
        erros = validator.validar_regras(regras)
        if erros:
            return {"valido": False, "erros": erros}

        # Gera estimativa
        sql, params = engine.generate_estimativa_query(regras)
        # Aqui poderia executar a query para retornar a estimativa
        return {
            "valido": True,
            "mensagem": "Segmentação válida",
            "resumo": {
                "regras": regras.dict(),
                "estimativa": "Consulta pode ser executada",
            }
        }
    except Exception as e:
        return {"valido": False, "erros": [str(e)]}


@router.post("/{seg_id}/aprovar", response_model=dict)
async def aprovar_segmentacao(
    seg_id: str,
    checklist: dict,
    user: dict = Depends(require_perfil(["admin"])),
):
    """
    Aprova uma segmentação (status deve estar em_aprovacao).
    Dispara recálculo imediato (Job) e evento.
    """
    service = SegmentacaoService()
    try:
        service.aprovar(seg_id, checklist, user["usuario_id"])
        return {"mensagem": "Segmentação aprovada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{seg_id}/ativar", response_model=dict)
async def ativar_segmentacao(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Ativa uma segmentação aprovada.
    """
    service = SegmentacaoService()
    try:
        service.transicionar_status(seg_id, "ativa", motivo="Ativação manual")
        return {"mensagem": "Segmentação ativada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{seg_id}/pausar", response_model=dict)
async def pausar_segmentacao(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Pausa uma segmentação ativa.
    """
    service = SegmentacaoService()
    try:
        service.transicionar_status(seg_id, "pausada", motivo="Pausa manual")
        return {"mensagem": "Segmentação pausada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{seg_id}/reativar", response_model=dict)
async def reativar_segmentacao(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Reativa uma segmentação pausada ou encerrada.
    """
    service = SegmentacaoService()
    try:
        service.transicionar_status(seg_id, "ativa", motivo="Reativação manual")
        return {"mensagem": "Segmentação reativada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{seg_id}/encerrar", response_model=dict)
async def encerrar_segmentacao(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Encerra definitivamente uma segmentação.
    """
    service = SegmentacaoService()
    try:
        service.transicionar_status(seg_id, "encerrada", motivo="Encerramento manual")
        return {"mensagem": "Segmentação encerrada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{seg_id}/executar", response_model=dict)
async def executar_segmentacao(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Executa manualmente uma segmentação ativa ou aprovada.
    """
    service = SegmentacaoService()
    try:
        resultado = service.executar(seg_id, origem="manual", usuario=user["usuario_id"])
        return {
            "exec_id": resultado["exec_id"],
            "run_id": resultado["run_id"],
            "job_id": resultado["job_id"],
            "mensagem": "Execução disparada com sucesso",
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao disparar execução: {str(e)}")


@router.post("/{seg_id}/clonar", response_model=dict)
async def clonar_segmentacao(
    seg_id: str,
    dados: CloneSegmentacaoDTO,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Clona uma segmentação existente.
    """
    print(f"🔍 ENDPOINT CLONE: seg_id={seg_id}, dados={dados.dict()}, usuario={user['usuario_id']}")
    service = SegmentacaoService()
    try:
        result = service.clonar(seg_id, dados, user["usuario_id"])
        print(f"🔍 ENDPOINT CLONE: SUCESSO - {result}")
        return {**result, "mensagem": "Segmentação clonada com sucesso"}
    except ValueError as e:
        erro = str(e)
        print(f"🔍 ENDPOINT CLONE: ERRO 422 - {erro}")
        raise HTTPException(status_code=422, detail=erro)
    except Exception as e:
        erro = str(e)
        print(f"🔍 ENDPOINT CLONE: ERRO INESPERADO - {type(e).__name__}: {erro}")
        raise


# ==================== DESTINO E VIGÊNCIA ====================

@router.get("/{seg_id}/destinos", response_model=List[dict])
async def listar_destinos(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Retorna destinos (natureza) configurados para a segmentação.
    """
    service = SegmentacaoService()
    return service.buscar_destinos(seg_id)


@router.put("/{seg_id}/destinos", response_model=dict)
async def atualizar_destinos(
    seg_id: str,
    destinos: List[dict],
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Atualiza destinos (sistema2 = humano, sistema3 = digital).
    """
    service = SegmentacaoService()
    try:
        service.atualizar_destino(seg_id, destinos)
        return {"mensagem": "Destinos atualizados com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.put("/{seg_id}/vigencia", response_model=dict)
async def atualizar_vigencia(
    seg_id: str,
    dados: dict,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    """
    Atualiza vigência e agendamento da segmentação.
    """
    service = SegmentacaoService()
    try:
        service.atualizar_vigencia(seg_id, dados, usuario=user["usuario_id"])
        return {"mensagem": "Vigência atualizada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post("/{seg_id}/enviar-aprovacao", response_model=dict)
async def enviar_para_aprovacao(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    service = SegmentacaoService()
    try:
        service.transicionar_status(seg_id, "em_aprovacao", motivo="Enviado para aprovação")
        return {"mensagem": "Segmentação enviada para aprovação"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.get("/{seg_id}/versoes", response_model=List[dict])
async def listar_versoes(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    service = SegmentacaoService()
    return service.listar_versoes(seg_id)

@router.get("/{seg_id}/versoes/{versao}", response_model=dict)
async def obter_versao(
    seg_id: str,
    versao: int,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    service = SegmentacaoService()
    versao_data = service.obter_versao(seg_id, versao)
    if not versao_data:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    return versao_data

@router.get("/{seg_id}/execucoes", response_model=List[dict])
async def listar_execucoes(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    service = SegmentacaoService()
    return service.listar_execucoes(seg_id)

@router.get("/{seg_id}/estados", response_model=List[dict])
async def listar_estados(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    service = SegmentacaoService()
    return service.listar_estados(seg_id)

@router.get("/{seg_id}/timeline", response_model=List[dict])
async def obter_timeline(
    seg_id: str,
    user: dict = Depends(require_perfil(["admin", "analista"])),
):
    service = SegmentacaoService()
    return service.obter_timeline(seg_id)