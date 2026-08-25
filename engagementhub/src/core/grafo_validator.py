"""Validador de Grafo de Jornada (S3-BACK-05-B).

Valida estrutura, conectividade, tipos de nó e dados obrigatórios
do grafo React Flow (nodes + edges) antes de ativar uma jornada.

Retorna ValidationResult com listas de erros (bloqueantes) e avisos.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Set
from collections import deque

logger = logging.getLogger(__name__)

# Tipos de nó válidos
TIPOS_NO_VALIDOS = {"entrada", "enviar_peca", "esperar", "condicao", "ab_split", "acao", "saida"}

# Dados obrigatórios por tipo de nó
DADOS_OBRIGATORIOS = {
    "entrada": [],  # seg_id é opcional (pode vir da jornada.seg_entrada_id)
    "enviar_peca": ["peca_id"],
    "esperar": [],  # pelo menos 1 de: dias, horas, ate_evento
    "condicao": ["campo", "op"],
    "ab_split": ["variantes"],
    "acao": ["tipo_acao"],
    "saida": [],
}

# Operações válidas para nó condição
OPS_VALIDAS = {"=", "!=", ">", ">=", "<", "<=", "in", "not_in", "contains", "exists"}


@dataclass
class ValidationResult:
    """Resultado da validação do grafo."""
    valido: bool = True
    erros: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def erro(self, msg: str):
        self.erros.append(msg)
        self.valido = False

    def aviso(self, msg: str):
        self.avisos.append(msg)


def validar_grafo(grafo_json: Optional[str], peca_ids_existentes: Optional[Set[str]] = None) -> ValidationResult:
    """Validação completa do grafo de jornada.

    Args:
        grafo_json: String JSON do grafo (nodes + edges)
        peca_ids_existentes: Set de peca_ids válidos no BD (opcional, para validação cruzada)

    Returns:
        ValidationResult com erros, avisos e stats
    """
    result = ValidationResult()

    # --- 1. Parse básico ---
    if not grafo_json:
        result.erro("grafo_json está vazio ou nulo")
        return result

    try:
        grafo = json.loads(grafo_json) if isinstance(grafo_json, str) else grafo_json
    except (json.JSONDecodeError, TypeError) as e:
        result.erro(f"grafo_json não é um JSON válido: {e}")
        return result

    if not isinstance(grafo, dict):
        result.erro("grafo_json deve ser um objeto (dict)")
        return result

    nodes = grafo.get("nodes", [])
    edges = grafo.get("edges", [])

    if not isinstance(nodes, list):
        result.erro("'nodes' deve ser uma lista")
        return result
    if not isinstance(edges, list):
        result.erro("'edges' deve ser uma lista")
        return result

    if not nodes:
        result.erro("Grafo não contém nós")
        return result

    # --- 2. Validação estrutural dos nós ---
    node_ids = set()
    node_types = {}  # id -> type
    node_data = {}   # id -> data dict
    entradas = []
    saidas = []

    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            result.erro(f"Nó [{i}] não é um objeto")
            continue

        node_id = node.get("id")
        if not node_id:
            result.erro(f"Nó [{i}] não tem 'id'")
            continue

        if node_id in node_ids:
            result.erro(f"ID duplicado: '{node_id}'")
            continue
        node_ids.add(node_id)

        tipo = node.get("type")
        if not tipo:
            result.erro(f"Nó '{node_id}' não tem 'type'")
            continue
        if tipo not in TIPOS_NO_VALIDOS:
            result.erro(f"Nó '{node_id}': tipo '{tipo}' inválido. Válidos: {sorted(TIPOS_NO_VALIDOS)}")
            continue

        node_types[node_id] = tipo
        node_data[node_id] = node.get("data", {})

        if tipo == "entrada":
            entradas.append(node_id)
        elif tipo == "saida":
            saidas.append(node_id)

    # --- 3. Regras de entrada/saída ---
    if len(entradas) == 0:
        result.erro("Grafo deve ter exatamente 1 nó 'entrada'. Encontrado: 0")
    elif len(entradas) > 1:
        result.erro(f"Grafo deve ter exatamente 1 nó 'entrada'. Encontrado: {len(entradas)} ({entradas})")

    if len(saidas) == 0:
        result.erro("Grafo deve ter pelo menos 1 nó 'saida'")

    # --- 4. Validação das arestas ---
    adjacencia = {nid: [] for nid in node_ids}  # outgoing
    entrada_de = {nid: [] for nid in node_ids}  # incoming

    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            result.erro(f"Aresta [{i}] não é um objeto")
            continue

        source = edge.get("source")
        target = edge.get("target")

        if not source or not target:
            result.erro(f"Aresta [{i}] falta 'source' ou 'target'")
            continue

        if source not in node_ids:
            result.erro(f"Aresta [{i}]: source '{source}' não é um nó válido")
            continue
        if target not in node_ids:
            result.erro(f"Aresta [{i}]: target '{target}' não é um nó válido")
            continue

        if source == target:
            result.erro(f"Aresta [{i}]: self-loop (source == target = '{source}')")
            continue

        adjacencia[source].append(target)
        entrada_de[target].append(source)

    # Entrada não deve ter arestas chegando
    for nid in entradas:
        if nid in entrada_de and entrada_de[nid]:
            result.erro(f"Nó entrada '{nid}' não pode ter arestas de entrada")

    # Saída não deve ter arestas saindo
    for nid in saidas:
        if nid in adjacencia and adjacencia[nid]:
            result.aviso(f"Nó saída '{nid}' tem arestas de saída (serão ignoradas)")

    # --- 5. Conectividade (BFS a partir da entrada) ---
    if entradas and not result.erros:  # só faz sentido se tem entrada válida
        alcancaveis = _bfs(entradas[0], adjacencia)
        desconectados = node_ids - alcancaveis
        if desconectados:
            result.erro(
                f"{len(desconectados)} nó(s) desconectado(s) da entrada: "
                f"{sorted(desconectados)[:5]}{'...' if len(desconectados) > 5 else ''}"
            )

    # --- 6. Detecção de loops ---
    ciclos = _detectar_ciclos(node_ids, adjacencia)
    if ciclos:
        for ciclo in ciclos:
            # Verifica se algum nó do ciclo tem max_iteracoes definido
            tem_limite = False
            for nid in ciclo:
                data = node_data.get(nid, {})
                if "max_iteracoes" in data and data["max_iteracoes"] is not None:
                    tem_limite = True
                    break
            if not tem_limite:
                result.erro(
                    f"Loop detectado ({' → '.join(ciclo[:4])}{'...' if len(ciclo) > 4 else ''}) "
                    f"sem 'max_iteracoes' definido. Adicione max_iteracoes em um nó do loop."
                )
            else:
                result.aviso(f"Loop controlado detectado ({' → '.join(ciclo[:4])}) com max_iteracoes")

    # --- 7. Dados obrigatórios por tipo ---
    peca_ids_referenciados = set()

    for nid, tipo in node_types.items():
        data = node_data.get(nid, {})
        if not isinstance(data, dict):
            result.erro(f"Nó '{nid}': 'data' deve ser um objeto")
            continue

        campos_req = DADOS_OBRIGATORIOS.get(tipo, [])
        for campo in campos_req:
            if not data.get(campo):
                result.erro(f"Nó '{nid}' (tipo={tipo}): campo obrigatório 'data.{campo}' ausente")

        # Validações específicas por tipo
        if tipo == "enviar_peca":
            pid = data.get("peca_id")
            if pid:
                peca_ids_referenciados.add(pid)

        elif tipo == "esperar":
            if not any(data.get(k) for k in ("dias", "horas", "ate_evento")):
                result.erro(f"Nó '{nid}' (esperar): deve ter 'dias', 'horas' ou 'ate_evento'")

        elif tipo == "condicao":
            op = data.get("op")
            if op and op not in OPS_VALIDAS:
                result.aviso(f"Nó '{nid}' (condicao): operador '{op}' não padrão. Válidos: {sorted(OPS_VALIDAS)}")
            # Condição deve ter pelo menos 2 saídas (true/false)
            out_count = len(adjacencia.get(nid, []))
            if out_count < 2:
                result.aviso(f"Nó '{nid}' (condicao): recomenda-se 2 arestas de saída (true/false), tem {out_count}")

        elif tipo == "ab_split":
            variantes = data.get("variantes", [])
            if not isinstance(variantes, list):
                result.erro(f"Nó '{nid}' (ab_split): 'variantes' deve ser uma lista, recebido: {type(variantes).__name__}")
            elif len(variantes) < 2:
                result.erro(f"Nó '{nid}' (ab_split): 'variantes' deve ter pelo menos 2 itens")
            else:
                out_count = len(adjacencia.get(nid, []))
                if out_count < len(variantes):
                    result.aviso(
                        f"Nó '{nid}' (ab_split): {len(variantes)} variantes mas só {out_count} arestas de saída"
                    )

    # --- 8. Validação cruzada de peças (se fornecido) ---
    if peca_ids_existentes is not None and peca_ids_referenciados:
        pecas_invalidas = peca_ids_referenciados - peca_ids_existentes
        if pecas_invalidas:
            result.erro(
                f"Peça(s) referenciada(s) não encontrada(s): {sorted(pecas_invalidas)}"
            )

    # --- Stats ---
    result.stats = {
        "total_nos": len(node_ids),
        "total_arestas": len(edges),
        "tipos": {tipo: sum(1 for t in node_types.values() if t == tipo) for tipo in TIPOS_NO_VALIDOS if any(t == tipo for t in node_types.values())},
        "pecas_referenciadas": sorted(peca_ids_referenciados),
        "tem_loops": len(ciclos) > 0,
    }

    return result


def _bfs(start: str, adjacencia: dict) -> Set[str]:
    """BFS para determinar nós alcançáveis a partir do start."""
    visitados = set()
    fila = deque([start])
    while fila:
        atual = fila.popleft()
        if atual in visitados:
            continue
        visitados.add(atual)
        for vizinho in adjacencia.get(atual, []):
            if vizinho not in visitados:
                fila.append(vizinho)
    return visitados


def _detectar_ciclos(node_ids: Set[str], adjacencia: dict) -> list:
    """Detecta ciclos no grafo dirigido via DFS (coloração branco/cinza/preto).

    Retorna lista de ciclos encontrados (cada ciclo é lista de node_ids).
    """
    BRANCO, CINZA, PRETO = 0, 1, 2
    cor = {nid: BRANCO for nid in node_ids}
    pai = {}  # para reconstruir o ciclo
    ciclos = []

    def dfs(nid, caminho):
        cor[nid] = CINZA
        caminho.append(nid)

        for vizinho in adjacencia.get(nid, []):
            if cor[vizinho] == CINZA:  # back-edge = ciclo
                # Extrai o ciclo do caminho
                idx = caminho.index(vizinho)
                ciclo = caminho[idx:] + [vizinho]
                ciclos.append(ciclo)
            elif cor[vizinho] == BRANCO:
                dfs(vizinho, caminho)

        caminho.pop()
        cor[nid] = PRETO

    for nid in node_ids:
        if cor[nid] == BRANCO:
            dfs(nid, [])

    return ciclos
