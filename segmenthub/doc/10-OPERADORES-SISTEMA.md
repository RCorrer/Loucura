# 10. Sistema de Operadores

## Visão Geral

O sistema de operadores do SegmentHub suporta **17 operadores** para construção de regras de segmentação, divididos em categorias funcionais e otimizados por tipo de dado.

---

## Operadores Disponíveis

### Por Categoria

#### 1. Comparação Numérica (6 operadores)
```
=           igual
!=          diferente
>           maior que
<           menor que
>=          maior ou igual
<=          menor ou igual
```

**Uso:** Campos numéricos (idade, renda, score, valores, quantidades)

**Exemplo:**
```json
{
  "campo_id": "idade",
  "op": ">=",
  "value": 18
}
```

#### 2. Ranges e Listas (3 operadores)
```
between     entre dois valores (inclusivo)
in          contido em lista
not_in      não contido em lista
```

**Uso:** Filtros de faixa ou múltiplos valores

**Exemplos:**
```json
// Between
{
  "campo_id": "score",
  "op": "between",
  "value": [700, 900]
}

// In
{
  "campo_id": "estado",
  "op": "in",
  "value": ["SP", "RJ", "MG"]
}
```

#### 3. Operadores de Texto (6 operadores)
```
contains          contém substring
not_contains      não contém substring
starts_with       começa com
ends_with         termina com
not_starts_with   não começa com
not_ends_with     não termina com
```

**Uso:** Campos string (cidade, nome, email, profissão)

**Características:**
- **Case-insensitive:** "paulo" encontra "Paulo", "PAULO", "São Paulo"
- Implementado via SQL LIKE com LOWER()

**Exemplos:**
```json
// Contains
{
  "campo_id": "cidade",
  "op": "contains",
  "value": "paulo"  // Encontra: "São Paulo", "Paulo Afonso", "PAULO"
}

// Starts with
{
  "campo_id": "nome",
  "op": "starts_with",
  "value": "mar"  // Encontra: "Maria", "Marcos", "MARCELO"
}

// Ends with
{
  "campo_id": "email",
  "op": "ends_with",
  "value": "@gmail.com"  // Encontra qualquer case
}
```

#### 4. Nulidade (2 operadores)
```
is_null       é nulo
is_not_null   não é nulo
```

**Uso:** Verificar presença/ausência de valor

**Exemplo:**
```json
{
  "campo_id": "email",
  "op": "is_not_null",
  "value": null  // value ignorado
}
```

---

## Comportamento por Tipo de Dado

### Campos Numéricos (tipo_dado = 'numeric')

**Operadores disponíveis:**
- Comparação: `=`, `!=`, `>`, `<`, `>=`, `<=`
- Range: `between`
- Listas: `in`, `not_in`
- Nulidade: `is_null`, `is_not_null`

**Total: 11 operadores**

**Características:**
- Comparação direta (sem LOWER)
- Performance otimizada
- Validação de tipo numérico

**Campos exemplo:**
- idade, score, churn_score, nps
- renda_mensal, renda_comprovada, saldo_atual
- limite_total, fatura_media, ticket_medio
- qtd_cartoes, qtd_transacoes_mes

### Campos String (tipo_dado = 'string')

**Operadores disponíveis:**
- Comparação: `=`, `!=` (case-insensitive)
- Texto: `contains`, `not_contains`, `starts_with`, `ends_with`, `not_starts_with`, `not_ends_with` (case-insensitive)
- Listas: `in`, `not_in` (case-insensitive)
- Nulidade: `is_null`, `is_not_null`

**Total: 12 operadores**

**Características:**
- **Case-insensitive em todos os operadores de texto**
- Implementado via `LOWER(campo)` e `LOWER(valor)`
- User-friendly: usuário não precisa se preocupar com case

**Campos exemplo:**
- cidade, estado, bairro
- nome, email, profissao
- status_conta, segmento_cliente
- tipo_contrato, canal_origem

---

## Implementação Técnica

### Backend: Query Engine

**Arquivo:** `src/core/query_engine.py`

**Método:** `_build_folha()`

#### Detecção de Tipo
```python
def _is_string_field(self, campo_id: str) -> bool:
    """Verifica se campo é string para aplicar LOWER()."""
    info = self._cache_catalogo.get(campo_id)
    return info.get("tipo_dado") == "string"
```

#### Aplicação Case-Insensitive
```python
# Operadores de texto
if op == "contains":
    sql = f"LOWER({campo}) LIKE LOWER({self._get_param()})"
    params.append(f"%{valor}%")

# Igualdade em strings
if op == "=" and is_string:
    sql = f"LOWER({campo}) = LOWER({self._get_param()})"
    params.append(valor)

# Listas em strings
if op == "in" and is_string:
    lower_placeholders = ", ".join([f"LOWER({self._get_param()})" for _ in valor])
    sql = f"LOWER({campo}) IN ({lower_placeholders})"
```

#### SQL Gerado

**Antes (case-sensitive):**
```sql
WHERE cidade LIKE '%paulo%'  -- ❌ Não encontra "Paulo"
```

**Agora (case-insensitive):**
```sql
WHERE LOWER(cidade) LIKE LOWER('%paulo%')  -- ✅ Encontra "Paulo", "PAULO", "São Paulo"
```

### Frontend: Componentes

**Arquivo:** `frontend/src/components/RuleNode.jsx` (componente ativo)

**Linha 19:**
```javascript
const DEFAULT_OPS = [
  '=', '!=', '>', '<', '>=', '<=',
  'between', 'in', 'not_in',
  'contains', 'not_contains',
  'starts_with', 'ends_with',
  'not_starts_with', 'not_ends_with',
  'is_null', 'is_not_null'
];
```

**Dropdown de operadores:** Todos os 17 operadores disponíveis

---

## Catálogo de Características

**Tabela:** `plataforma.metadata.catalogo_caracteristicas`

**Coluna:** `operadores` (ARRAY<STRING>)

### Configuração por Tipo

#### Campos Numéricos (20 campos)
```sql
operadores = [
  '=', '!=', '>', '<', '>=', '<=',
  'between', 'in', 'not_in',
  'is_null', 'is_not_null'
]
```

#### Campos String (29 campos)
```sql
operadores = [
  '=', '!=',
  'contains', 'not_contains',
  'starts_with', 'ends_with',
  'not_starts_with', 'not_ends_with',
  'in', 'not_in',
  'is_null', 'is_not_null'
]
```

### Validação

**Arquivo:** `src/core/validator.py`

**Linha 102:**
```python
if folha.op not in campo["operadores"]:
    erros.append(
        f"operador '{folha.op}' não permitido para campo '{folha.campo_id}'"
    )
```

---

## Casos de Uso

### 1. Filtro de Idade
```json
{
  "campo_id": "idade",
  "op": ">=",
  "value": 18
}
```
**SQL:** `WHERE customer_features_wide.idade >= 18`

### 2. Busca de Cidade (Case-Insensitive)
```json
{
  "campo_id": "cidade",
  "op": "contains",
  "value": "paulo"
}
```
**SQL:** `WHERE LOWER(customer_features_wide.cidade) LIKE LOWER('%paulo%')`
**Resultado:** "São Paulo", "Paulo Afonso", "PAULO"

### 3. Estados Específicos (Case-Insensitive)
```json
{
  "campo_id": "estado",
  "op": "in",
  "value": ["sp", "RJ", "mg"]
}
```
**SQL:** `WHERE LOWER(customer_features_wide.estado) IN (LOWER('sp'), LOWER('RJ'), LOWER('mg'))`
**Resultado:** Encontra "SP", "sp", "RJ", "rj", "MG", "mg"

### 4. Score em Faixa
```json
{
  "campo_id": "score",
  "op": "between",
  "value": [700, 900]
}
```
**SQL:** `WHERE customer_features_wide.score BETWEEN 700 AND 900`

### 5. Email Gmail
```json
{
  "campo_id": "email",
  "op": "ends_with",
  "value": "@gmail.com"
}
```
**SQL:** `WHERE LOWER(customer_features_wide.email) LIKE LOWER('%@gmail.com')`
**Resultado:** Encontra qualquer case (@gmail.com, @GMAIL.COM, @Gmail.com)

### 6. Exclusão de Gerentes
```json
{
  "campo_id": "profissao",
  "op": "not_contains",
  "value": "gerente"
}
```
**SQL:** `WHERE LOWER(customer_features_wide.profissao) NOT LIKE LOWER('%gerente%')`
**Resultado:** Exclui "Gerente", "GERENTE", "Subgerente", "gerente de vendas"

---

## Performance

### Otimizações

1. **LOWER() aplicado apenas em strings**
   - Campos numéricos mantêm comparação direta
   - Performance preservada em queries numéricas

2. **Cache do catálogo**
   - `tipo_dado` carregado em memória
   - Decisão de LOWER() sem query extra

3. **Parametrização**
   - Query Engine usa placeholders (`?`)
   - Proteção contra SQL injection
   - Reuso de plano de execução

### Recomendações

1. **Índices em campos string frequentemente filtrados:**
   ```sql
   -- Considere índices funcionais
   CREATE INDEX idx_cidade_lower ON customer_features_wide (LOWER(cidade));
   ```

2. **Evite LIKE '%...%' em campos grandes**
   - Prefira `starts_with` quando possível
   - Mais eficiente que contains

3. **Use operadores específicos**
   - `=` mais rápido que `contains` para match exato
   - `in` mais eficiente que múltiplos `OR`

---

## Histórico de Mudanças

### v1.2.0 (2026-08-17)

**Implementado:**
- Case-insensitive para operadores de texto em campos string
- Detecção automática de tipo via `_is_string_field()`
- LOWER() aplicado em operadores: `=`, `!=`, `in`, `not_in`, `contains`, `starts_with`, `ends_with`, `not_contains`, `not_starts_with`, `not_ends_with`

**Commits:**
- 1e1e5ce: Adicionar operadores de texto completos
- 33f271e: Implementar case-insensitive backend
- c20f6cf: Atualizar RuleGroup.jsx
- 3cbf162: Atualizar RuleNode.jsx (componente ativo)

### v1.1.0 (2026-08-17)

**Implementado:**
- Novos operadores de texto: `ends_with`, `not_contains`, `not_starts_with`, `not_ends_with`
- Padronização de operadores no catálogo (português → inglês)
- Frontend expõe todos os 17 operadores

**Commits:**
- 1e1e5ce: Backend + frontend + catálogo

### v1.0.0 (2026-08-17)

**Corrigido:**
- 20 campos numéricos com `tipo_dado='numeric'`
- Operadores numéricos: `>=`, `>`, `<`, `<=`, `between`
- Problema: erro 422 "operador '>=' não permitido para campo 'idade'"

**Arquivo:**
- fix_catalog_operators.sql

---

## Referências

- [02-SCHEMAS-TABELAS.md](./02-SCHEMAS-TABELAS.md): Estrutura da tabela `catalogo_caracteristicas`
- [03-ARQUITETURA-BACKEND.md](./03-ARQUITETURA-BACKEND.md): Validação de operadores
- [06-API-ENDPOINTS.md](./06-API-ENDPOINTS.md): Formato de regras JSON
- [07-INTEGRACAO-CONTRATOS.md](./07-INTEGRACAO-CONTRATOS.md): Engines (seg_exec vs query_engine)

---

## FAQ

### Por que case-insensitive?

**Problema:** Usuários digitavam "são paulo" mas banco tinha "São Paulo", resultando em 0 matches.

**Solução:** LOWER() em ambos os lados da comparação.

**Benefício:** User-friendly, não requer uppercase manual.

### Posso desabilitar case-insensitive?

Não. É comportamento padrão para strings. Para match exato case-sensitive, armazene dados em lowercase no banco.

### Como adicionar novo operador?

1. **Backend:** Implementar em `query_engine.py` (`_build_folha`)
2. **Frontend:** Adicionar em `RuleNode.jsx` (`DEFAULT_OPS`)
3. **Catálogo:** Atualizar coluna `operadores` dos campos relevantes
4. **Validação:** Atualizar `validator.py` se necessário
5. **Documentação:** Atualizar este arquivo

### Operadores funcionam em exclusão?

Sim! As regras de exclusão usam os mesmos operadores, mas o SQL final usa `AND NOT (...)` ao redor da condição.

---

**Última atualização:** 2026-08-17  
**Versão:** 1.2.0