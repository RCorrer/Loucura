"""
Service para segmentações.
Gerencia CRUD, ciclo de vida, validações e geração de IDs/slugs.
"""

import uuid
import re
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException

from src.models.regras import RegrasJson
from src.models.dto.segmentacao_dto import (
    SegmentacaoCreateDTO,
    SegmentacaoUpdateDTO,
    SegmentacaoResponseDTO,
    SegmentacaoDetalheDTO,
    TransicaoStatusDTO,
    CloneSegmentacaoDTO,
)
from src.repositories.segmentacao_repository import SegmentacaoRepository
from src.core.validator import RegraValidator
from src.core.query_engine import QueryEngine
from src.exceptions.custom_exceptions import TemaNotFoundError, CampoNotFoundError


class SegmentacaoService:
    """Serviço para operações de segmentação."""

    def __init__(self):
        self.repository = SegmentacaoRepository()
        self.validator = RegraValidator()
        self.engine = QueryEngine()

    # ==================== HELPERS ====================

    def _gerar_seg_id(self) -> str:
        """Gera um ID único para segmentação."""
        return f"seg_{uuid.uuid4().hex[:12]}"

    def _gerar_seg_codigo(self, nome: str) -> str:
        """Gera um código amigável baseado no nome."""
        # Remove acentos e caracteres especiais
        nome_limpo = re.sub(r'[^a-zA-Z0-9 ]', '', nome)
        base = nome_limpo[:20].upper().replace(' ', '-')
        # Adiciona timestamp curto para garantir unicidade
        import time
        suffix = hex(int(time.time()))[-4:]
        return f"SEG-{base}-{suffix}"

    def _gerar_seg_slug(self, nome: str) -> str:
        """Gera um slug a partir do nome."""
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', nome.lower()).strip('-')
        return slug[:50]

    def _validar_regras(self, regras_dict: Dict[str, Any]) -> List[str]:
        """Valida regras JSON usando o RegraValidator."""
        # Se regras_json estiver vazio, não valida (será preenchido depois)
        if not regras_dict or regras_dict == {}:
            return []
        
        try:
            regras = RegrasJson(**regras_dict)
            return self.validator.validar_regras(regras)
        except Exception as e:
            return [f"Erro ao validar regras: {str(e)}"]

    # ==================== CRUD ====================

    def criar(self, dados: SegmentacaoCreateDTO, usuario: str) -> Dict[str, str]:
        """Cria uma nova segmentação."""
        try:
            print(f"🔍 CRIAR: Iniciando criação")
            print(f"🔍 CRIAR: dados.regras_json = {dados.regras_json}, type = {type(dados.regras_json)}")
            
            # 1. Valida regras
            print(f"🔍 CRIAR: Validando regras...")
            erros = self._validar_regras(dados.regras_json)
            print(f"🔍 CRIAR: erros = {erros}")
            if erros:
                erro_msg = f"Regras inválidas: {erros}"
                print(f"❌ CRIAR: {erro_msg}")
                raise ValueError(erro_msg)

            # 2. Gera IDs
            print(f"🔍 CRIAR: Gerando IDs...")
            seg_id = self._gerar_seg_id()
            seg_codigo = self._gerar_seg_codigo(dados.nome)
            seg_slug = self._gerar_seg_slug(dados.nome)
            print(f"🔍 CRIAR: seg_id={seg_id}, seg_codigo={seg_codigo}")

            # 3. Prepara dados para inserção
            print(f"🔍 CRIAR: Preparando dados para inserção...")
            now = datetime.now()
            dados_insert = {
                "seg_id": seg_id,
                "seg_codigo": seg_codigo,
                "seg_slug": seg_slug,
                "nome": dados.nome,
                "descricao": dados.descricao,
                "objetivo": dados.objetivo,
                "seg_tags": dados.seg_tags or [],
                "resumo": dados.resumo,
                "objetivo_negocio": dados.objetivo_negocio,
                "publico_alvo_descricao": dados.publico_alvo_descricao,
                "observacoes": dados.observacoes,
                "documentacao_md": dados.documentacao_md,
                "owner": dados.owner,
                "area_responsavel": dados.area_responsavel,
                "email_contato": dados.email_contato,
                "criado_por": usuario,
                "publico_base_id": dados.publico_base_id,
                "regras_json": json.dumps(dados.regras_json),
                "tipo": dados.tipo or "direta",
                "status": "rascunho",
                "versao_atual": 1,
                "criado_em": now,
                "atualizado_em": now,
            }
            print(f"🔍 CRIAR: dados_insert preparados")

            # 4. Insere no banco
            print(f"🔍 CRIAR: Inserindo no banco...")
            self.repository.inserir(dados_insert)
            print(f"✅ CRIAR: Inserido com sucesso")

            # 5. Insere versão inicial
            print(f"🔍 CRIAR: Inserindo versão inicial...")
            self.repository.inserir_versao(
                seg_id=seg_id,
                versao=1,
                regras_json=dados.regras_json,
                motivo="Versão inicial",
                alterado_por=usuario,
            )
            print(f"✅ CRIAR: Versão inserida com sucesso")

            result = {"seg_id": seg_id, "seg_codigo": seg_codigo, "seg_slug": seg_slug}
            print(f"✅ CRIAR: Concluído com sucesso! result={result}")
            return result
            
        except Exception as e:
            erro = f"{type(e).__name__}: {str(e)}"
            print(f"❌ CRIAR ERROR: {erro}")
            import traceback
            print(f"❌ CRIAR TRACEBACK:\n{traceback.format_exc()}")
            raise

    def buscar_por_id(self, seg_id: str) -> Optional[Dict]:
        """Busca uma segmentação pelo ID, com detalhes completos."""
        dados = self.repository.buscar_por_id(seg_id)
        if not dados:
            return None

        # Converte regras_json de string para dict
        if dados.get("regras_json"):
            try:
                parsed = json.loads(dados["regras_json"])
                # Se for lista, converte para dict vazio
                if isinstance(parsed, list):
                    print(f"⚠️ regras_json é uma LISTA, convertendo para dict vazio")
                    dados["regras_json"] = {}
                else:
                    dados["regras_json"] = parsed
            except:
                dados["regras_json"] = {}
        return dados

    def listar(
        self,
        status: Optional[str] = None,
        objetivo: Optional[str] = None,
        owner: Optional[str] = None,
        busca: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Dict[str, Any]:
        """Lista segmentações com paginação."""
        offset = (page - 1) * size

        # 🔍 DEBUG: exibe os valores no log do app
        print(f"🔍 listar: page={page}, size={size}, offset={offset}")

        resultados = self.repository.listar(
            status=status,
            objetivo=objetivo,
            owner=owner,
            busca=busca,
            limit=size,
            offset=offset,
        )
        total = self.repository.contar(status=status, objetivo=objetivo, owner=owner, busca=busca)
        total_pages = (total + size - 1) // size if total > 0 else 0

        return {
            "data": resultados,
            "meta": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def atualizar(self, seg_id: str, dados: SegmentacaoUpdateDTO, usuario: str) -> bool:
        """Atualiza uma segmentação (cria nova versão se ativa)."""
        # 1. Busca segmentação atual
        atual = self.buscar_por_id(seg_id)
        if not atual:
            raise ValueError("Segmentação não encontrada")

        # 2. Se estiver ativa e alterar regras, criar nova versão rascunho
        if atual["status"] == "ativa" and dados.regras_json:
            # Valida novas regras
            erros = self._validar_regras(dados.regras_json)
            if erros:
                raise ValueError(f"Regras inválidas: {erros}")

            # Cria nova versão
            nova_versao = atual["versao_atual"] + 1
            self.repository.inserir_versao(
                seg_id=seg_id,
                versao=nova_versao,
                regras_json=dados.regras_json,
                motivo="Edição de segmentação ativa",
                alterado_por=usuario,
            )
            # Atualiza versão na definição
            self.repository.atualizar(seg_id, {
                "versao_atual": nova_versao,
                "status": "rascunho",  # nova versão fica como rascunho
            })

        # 3. Atualiza campos normais
        dados_update = dados.model_dump(exclude_unset=True, exclude={"regras_json"})
        if dados_update:
            self.repository.atualizar(seg_id, dados_update)

        return True

    def arquivar(self, seg_id: str) -> bool:
        """Arquiva uma segmentação (soft delete)."""
        return self.repository.arquivar(seg_id)

    # ==================== CICLO DE VIDA ====================

    def transicionar_status(self, seg_id: str, novo_status: str, motivo: Optional[str] = None) -> bool:
        """Transiciona status validando regras de negócio."""
        atual = self.buscar_por_id(seg_id)
        if not atual:
            raise ValueError("Segmentação não encontrada")

        status_atual = atual["status"]

        # Valida transições permitidas
        transicoes = {
            "rascunho": ["em_aprovacao", "arquivada"],
            "em_aprovacao": ["aprovada", "rascunho"],
            "aprovada": ["ativa", "arquivada"],
            "ativa": ["pausada", "encerrada", "arquivada"],
            "pausada": ["ativa", "encerrada"],
            "encerrada": ["ativa", "arquivada"],  # reativar via endpoint específico
        }
        if novo_status not in transicoes.get(status_atual, []):
            raise ValueError(f"Transição de '{status_atual}' para '{novo_status}' não permitida")

        # Validações específicas
        if novo_status == "em_aprovacao" and status_atual == "rascunho":
            # Pode adicionar validação extra (ex: regras obrigatórias)
            pass

        if novo_status == "aprovada" and status_atual == "em_aprovacao":
            # Verifica se há checklist? (será feito no aprovar)
            pass

        if novo_status == "ativa" and status_atual == "aprovada":
            # Ao ativar, poderia disparar recálculo imediato (Job)
            pass

        # Realiza transição
        return self.repository.atualizar_status(seg_id, novo_status, motivo)

    def aprovar(self, seg_id: str, checklist: Dict[str, Any], usuario: str) -> bool:
        """Aprova uma segmentação e dispara Job (simulado)."""
        atual = self.buscar_por_id(seg_id)
        if not atual:
            raise ValueError("Segmentação não encontrada")
        if atual["status"] != "em_aprovacao":
            raise ValueError(f"Segmentação '{seg_id}' não está em aprovação (status atual: {atual['status']})")

        # 1. Valida checklist (simples)
        if not checklist or not checklist.get("aprovado"):
            raise ValueError("Checklist de aprovação não preenchido")

        # 2. Atualiza status para 'aprovada'
        self.repository.atualizar_status(seg_id, "aprovada", motivo="Aprovado com checklist")

        # 3. Registra aprovado_por e aprovado_em
        self.repository.atualizar(seg_id, {
            "aprovado_por": usuario,
            "aprovado_em": datetime.now(),
            "checklist_validacao_json": checklist,
        })

        # 4. Dispara Job (na POC, apenas registra)
        # Em produção, isso chamaria o Job S1-JOB-01
        # Por enquanto, apenas registramos
        self.repository.executar_segmentacao(seg_id, f"exec_{seg_id}_{datetime.now().strftime('%Y%m%d_%H%M')}")

        # 5. Emite evento (será implementado em S1-JOB-01)
        # self._emitir_evento(seg_id, 'aprovada')

        return True

    def executar(self, seg_id: str, origem: str = "manual") -> str:
        """Executa manualmente uma segmentação."""
        atual = self.buscar_por_id(seg_id)
        if not atual:
            raise ValueError("Segmentação não encontrada")
        if atual["status"] not in ["ativa", "aprovada"]:
            raise ValueError(f"Segmentação '{seg_id}' não está ativa ou aprovada")

        exec_id = f"exec_{seg_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.repository.executar_segmentacao(seg_id, exec_id)
        # Em produção, aqui chamaria o Job
        return exec_id

    # ==================== DESTINO E VIGÊNCIA ====================

    def atualizar_destino(self, seg_id: str, destinos: List[Dict]) -> bool:
        """Atualiza a natureza do segmento (humano/digital)."""
        for item in destinos:
            if item["destino"] not in ["sistema2", "sistema3"]:
                raise ValueError(f"Destino inválido: {item['destino']}")
            self.repository.upsert_destino(seg_id, item["destino"], item["habilitado"])
        return True

    def buscar_destinos(self, seg_id: str) -> List[Dict]:
        """Busca destinos configurados."""
        return self.repository.buscar_destinos(seg_id)

    def atualizar_vigencia(self, seg_id: str, dados: Dict) -> bool:
        """Atualiza vigência e agendamento."""
        # Validar cron se fornecido
        if dados.get("agendamento_cron"):
            # validação simples
            pass
        return self.repository.atualizar_vigencia(seg_id, dados)

    # ==================== CLONAR ====================

    def clonar(self, seg_id: str, dados: CloneSegmentacaoDTO, usuario: str) -> Dict[str, str]:
        """Clona uma segmentação existente."""
        try:
            print(f"🔍 CLONE: Iniciando clone de {seg_id}")
            
            original = self.buscar_por_id(seg_id)
            if not original:
                raise ValueError("Segmentação original não encontrada")
            
            print(f"🔍 CLONE: Original encontrado: {original.get('nome')}")

            # Garante que regras_json seja um dict válido
            regras_json = original.get("regras_json")
            print(f"🔍 CLONE: regras_json = {regras_json}, type = {type(regras_json)}")
            
            # Se for lista ou None ou não for dict, usa dict vazio
            if isinstance(regras_json, list):
                print(f"⚠️ CLONE: regras_json é LISTA, convertendo para dict vazio")
                regras_json = {}
            elif not regras_json or not isinstance(regras_json, dict):
                print(f"🔍 CLONE: regras_json não é dict, usando dict vazio")
                regras_json = {}

            # Prepara dados do clone
            nome_clone = dados.nome or f"{original['nome']} (Clone)"
            print(f"🔍 CLONE: Criando DTO com nome={nome_clone}")
            
            create_dto = SegmentacaoCreateDTO(
                nome=nome_clone,
                descricao=dados.descricao or original.get("descricao"),
                objetivo=original["objetivo"],
                seg_tags=original.get("seg_tags"),
                resumo=original.get("resumo"),
                objetivo_negocio=original.get("objetivo_negocio"),
                publico_alvo_descricao=original.get("publico_alvo_descricao"),
                observacoes=original.get("observacoes"),
                documentacao_md=original.get("documentacao_md"),
                owner=dados.owner or usuario,
                area_responsavel=dados.area_responsavel or original.get("area_responsavel"),
                email_contato=original.get("email_contato"),
                publico_base_id=original["publico_base_id"],
                regras_json=regras_json,
                tipo="clone",
            )
            
            print(f"🔍 CLONE: DTO criado, chamando criar()")
            result = self.criar(create_dto, usuario)
            print(f"🔍 CLONE: Sucesso! seg_id={result.get('seg_id')}")
            return result
            
        except Exception as e:
            erro = f"{type(e).__name__}: {str(e)}"
            print(f"❌ CLONE ERROR: {erro}")
            import traceback
            print(f"❌ CLONE TRACEBACK:\n{traceback.format_exc()}")
            raise

    def listar_versoes(self, seg_id: str) -> List[Dict]:
        return self.repository.listar_versoes(seg_id)

    def obter_versao(self, seg_id: str, versao: int) -> Optional[Dict]:
        return self.repository.obter_versao(seg_id, versao)

    def listar_execucoes(self, seg_id: str) -> List[Dict]:
        return self.repository.listar_execucoes(seg_id)

    def listar_estados(self, seg_id: str) -> List[Dict]:
        return self.repository.listar_estados(seg_id)

    def obter_timeline(self, seg_id: str) -> List[Dict]:
        """Mescla versões, execuções e estados em uma única timeline ordenada."""
        versoes = self.repository.listar_versoes(seg_id)
        execucoes = self.repository.listar_execucoes(seg_id)
        estados = self.repository.listar_estados(seg_id)

        timeline = []
        for v in versoes:
            timeline.append({
                "tipo": "versao",
                "data": v["alterado_em"],
                "detalhe": f"Versão {v['versao']}",
                "motivo": v["motivo"],
                "alterado_por": v["alterado_por"],
                "dados": v
            })
        for e in execucoes:
            timeline.append({
                "tipo": "execucao",
                "data": e["executado_em"],
                "detalhe": f"Execução {e['exec_id']}",
                "status": e["status"],
                "dados": e
            })
        for est in estados:
            timeline.append({
                "tipo": "estado",
                "data": est["alterado_em"],
                "detalhe": f"{est['estado_anterior']} -> {est['estado_novo']}",
                "motivo": est["motivo"],
                "alterado_por": est["alterado_por"],
                "dados": est
            })

        # Ordena por data (mais recente primeiro)
        timeline.sort(key=lambda x: x["data"], reverse=True)
        return timeline