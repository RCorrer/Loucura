/**
 * RuleViewer — FX-09
 *
 * Visualizador read-only da árvore de regras (formato RegraNo).
 * Usado em DetalheSegmentacao para exibir as regras sem precisar ir ao Builder.
 */
import React from 'react';
import { Box, Chip, Typography, Paper } from '@mui/material';
import AccountTreeIcon from '@mui/icons-material/AccountTree';

const OP_LABELS = {
  '=': '=', '!=': '≠', '>': '>', '<': '<', '>=': '≥', '<=': '≤',
  in: 'em', not_in: 'não em', like: 'contém', not_like: 'não contém',
  between: 'entre', is_null: 'é nulo', is_not_null: 'não é nulo',
  starts_with: 'inicia com', ends_with: 'termina com',
};

function formatValue(value, op) {
  if (op === 'is_null' || op === 'is_not_null') return '';
  if (Array.isArray(value)) return value.join(', ');
  return String(value ?? '');
}

function RuleLeaf({ rule, depth }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.5, pl: depth * 2 }}>
      <Typography variant="body2" fontFamily="monospace" color="text.secondary" sx={{ minWidth: 140 }}>
        {rule.campo_id?.length > 20 ? `${rule.campo_id.slice(0, 20)}...` : rule.campo_id}
      </Typography>
      <Chip label={OP_LABELS[rule.op] || rule.op} size="small" variant="outlined" />
      {formatValue(rule.value, rule.op) && (
        <Typography variant="body2" fontWeight="medium">
          {formatValue(rule.value, rule.op)}
        </Typography>
      )}
    </Box>
  );
}

function RuleGroup({ node, depth = 0 }) {
  if (!node || !node.rules) return null;

  return (
    <Box sx={{ pl: depth > 0 ? 2 : 0, borderLeft: depth > 0 ? '2px solid' : 'none', borderColor: 'divider', ml: depth > 0 ? 1 : 0 }}>
      {depth > 0 && (
        <Chip
          icon={<AccountTreeIcon />}
          label={node.operator || 'AND'}
          size="small"
          color={node.operator === 'OR' ? 'warning' : 'info'}
          sx={{ mb: 0.5 }}
        />
      )}
      {node.rules.map((item, idx) => {
        if (item.rules) {
          return <RuleGroup key={idx} node={item} depth={depth + 1} />;
        }
        return (
          <Box key={idx}>
            {idx > 0 && depth === 0 && (
              <Typography variant="caption" color="text.secondary" sx={{ pl: depth * 2 }}>
                {node.operator || 'AND'}
              </Typography>
            )}
            <RuleLeaf rule={item} depth={depth} />
          </Box>
        );
      })}
    </Box>
  );
}

export default function RuleViewer({ regrasJson, compact = false }) {
  if (!regrasJson) {
    return <Typography variant="body2" color="text.secondary">Nenhuma regra definida</Typography>;
  }

  const { inclusao, exclusao } = regrasJson;

  const countRules = (node) => {
    if (!node?.rules) return 0;
    return node.rules.reduce((acc, r) => acc + (r.rules ? countRules(r) : 1), 0);
  };

  if (compact) {
    const inc = countRules(inclusao);
    const exc = countRules(exclusao);
    return (
      <Typography variant="body2">
        {inc} regra(s) de inclusão{exc > 0 ? `, ${exc} de exclusão` : ''}
      </Typography>
    );
  }

  return (
    <Box>
      {inclusao && inclusao.rules?.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" color="success.main" gutterBottom>
            Inclusão ({countRules(inclusao)} regras) — {inclusao.operator || 'AND'}
          </Typography>
          <Paper variant="outlined" sx={{ p: 1.5 }}>
            <RuleGroup node={inclusao} />
          </Paper>
        </Box>
      )}
      {exclusao && exclusao.rules?.length > 0 && (
        <Box>
          <Typography variant="subtitle2" color="error.main" gutterBottom>
            Exclusão ({countRules(exclusao)} regras) — {exclusao.operator || 'OR'}
          </Typography>
          <Paper variant="outlined" sx={{ p: 1.5 }}>
            <RuleGroup node={exclusao} />
          </Paper>
        </Box>
      )}
    </Box>
  );
}
