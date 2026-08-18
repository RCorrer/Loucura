/**
 * splitAtConnector — Reestrutura uma árvore de regras quando o usuário
 * muda o operador lógico ENTRE dois itens adjacentes.
 *
 * O modelo de dados (RegraNo) usa UM operador por nó. Para permitir que
 * o usuário defina operadores DIFERENTES entre pares de regras no mesmo
 * nível, esta função detecta a mudança e cria sub-grupos automaticamente,
 * preservando a semântica desejada.
 *
 * @param {Object} node - Nó atual { operator: 'AND'|'OR', rules: [...] }
 * @param {number} splitIndex - Índice do ÚLTIMO item do grupo esquerdo.
 *   Ex: splitIndex=1 significa que o conector entre rules[1] e rules[2] mudou.
 * @param {string} newOperator - Novo operador escolhido ('AND' ou 'OR').
 * @returns {Object} Nova árvore reestruturada (imutável — não modifica o input).
 *
 * Exemplos:
 *   Bloco AND [F1, F2, F3], splitIndex=1, newOperator='OR'
 *   → { operator: 'OR', rules: [{ operator: 'AND', rules: [F1, F2] }, F3] }
 *
 *   Bloco OR [F1, F2, F3, F4], splitIndex=2, newOperator='AND'
 *   → { operator: 'AND', rules: [{ operator: 'OR', rules: [F1, F2, F3] }, F4] }
 */
export function splitAtConnector(node, splitIndex, newOperator) {
  const { operator: oldOperator, rules } = node;

  // Se o novo operador é igual ao do nó, nada muda
  if (newOperator === oldOperator) {
    return node;
  }

  // Validações defensivas
  if (splitIndex < 0 || splitIndex >= rules.length - 1) {
    console.warn('[splitAtConnector] splitIndex fora do range:', splitIndex);
    return node;
  }

  // Divide em grupo esquerdo e direito
  const leftRules = rules.slice(0, splitIndex + 1);
  const rightRules = rules.slice(splitIndex + 1);

  // Cria sub-grupos mantendo o operador original DENTRO de cada grupo.
  // Se um grupo tem apenas 1 item, não precisa de wrapper — usa o item direto.
  const leftGroup =
    leftRules.length > 1
      ? { operator: oldOperator, rules: leftRules }
      : leftRules[0];

  const rightGroup =
    rightRules.length > 1
      ? { operator: oldOperator, rules: rightRules }
      : rightRules[0];

  // Novo nó raiz com o operador que o usuário escolheu
  return {
    operator: newOperator,
    rules: [leftGroup, rightGroup],
  };
}

/**
 * flattenSingleChildNodes — Normaliza a árvore removendo nós intermediários
 * que têm apenas 1 filho (são redundantes). Também faz merge de nós filhos
 * que têm o mesmo operador do pai (associatividade).
 *
 * Chamar após qualquer reestruturação para manter a árvore limpa.
 *
 * @param {Object} node - Nó da árvore de regras
 * @returns {Object} Árvore normalizada
 */
export function flattenTree(node) {
  // Se é folha, retorna como está
  if (!node || !node.rules) {
    return node;
  }

  // Primeiro, flatten recursivo nos filhos
  let flatRules = [];
  for (const child of node.rules) {
    const flatChild = flattenTree(child);

    // Se o filho é um nó com MESMO operador do pai, absorve seus filhos
    // (associatividade: A AND (B AND C) = A AND B AND C)
    if (flatChild.rules && flatChild.operator === node.operator) {
      flatRules.push(...flatChild.rules);
    } else {
      flatRules.push(flatChild);
    }
  }

  // Se sobrou apenas 1 filho, promove-o (remove nó intermediário)
  if (flatRules.length === 1) {
    return flatRules[0];
  }

  return { ...node, rules: flatRules };
}

/**
 * Determina os operadores VISUAIS entre cada par de rules de um nó.
 * Isso permite renderizar conectores individuais entre regras,
 * mesmo que internamente o nó tenha um único operador.
 *
 * Para um nó flat (sem sub-grupos), todos os conectores mostram o operador do nó.
 * Para renderização pós-split, o componente recursivo já mostra a árvore correta.
 *
 * @param {Object} node - Nó { operator, rules }
 * @returns {string[]} Array com (rules.length - 1) operadores.
 */
export function getVisualConnectors(node) {
  if (!node || !node.rules || node.rules.length <= 1) {
    return [];
  }
  // Todos os conectores do mesmo nó têm o mesmo operador
  return Array(node.rules.length - 1).fill(node.operator);
}
