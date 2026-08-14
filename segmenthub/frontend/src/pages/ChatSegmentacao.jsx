import React, { useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { PageHeader, ChatPanel } from '@shared';
import { useChat } from '@shared/hooks/useChat';
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import RuleIcon from '@mui/icons-material/Rule';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';

const SUGESTOES_INICIAIS = [
  'Crie uma segmentação de clientes com renda acima de 10.000',
  'Quais segmentações estão ativas?',
  'Sugira regras para clientes jovens com alto engajamento digital',
  'Estime o público de clientes PJ com faturamento > 500k',
];

/**
 * ChatSegmentacao — S1-FRONT-09
 *
 * Página de chatbot assistente para segmentações.
 * Rota: /chat
 *
 * Funcionalidades:
 * - Chat com backend LLM (POST /api/chat/mensagem)
 * - Histórico de mensagens (session)
 * - Sugere regras (regras_json na resposta)
 * - Integra com contexto de segmentação (via query param ?seg_id=)
 * - Confirmação de ações (precisa_confirmacao)
 */
export default function ChatSegmentacao() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const segIdContexto = searchParams.get('seg_id');

  const { messages, sendMessage, clearMessages, loading } = useChat('/api/chat/mensagem');

  const [snackbar, setSnackbar] = useState({ open: false, message: '' });
  const [regrasDialog, setRegrasDialog] = useState({ open: false, regras: null });
  const [confirmDialog, setConfirmDialog] = useState({ open: false, msg: null });

  // Envia mensagem com contexto (se houver seg aberta)
  const handleSendMessage = useCallback(async (content) => {
    const response = await sendMessage(content);

    // Se retornou regras, mostra botão para visualizar/aplicar
    if (response?.regras_json) {
      setRegrasDialog({ open: false, regras: response.regras_json });
    }

    // Se precisa confirmação, abre dialog
    if (response?.precisa_confirmacao) {
      setConfirmDialog({ open: true, msg: response });
    }
  }, [sendMessage]);

  // Aplica regras sugeridas — navega para builder com regras
  const handleAplicarRegras = () => {
    const regras = regrasDialog.regras;
    // Codifica e navega para o builder com as regras como state
    navigate('/segmentacoes/nova', { state: { regrasImportadas: regras } });
    setRegrasDialog({ open: false, regras: null });
  };

  // Copia regras para clipboard
  const handleCopiarRegras = () => {
    navigator.clipboard.writeText(JSON.stringify(regrasDialog.regras, null, 2));
    setSnackbar({ open: true, message: 'Regras copiadas para a área de transferência' });
  };

  // Confirma ação pendente
  const handleConfirmar = async () => {
    await sendMessage('Sim, confirmo');
    setConfirmDialog({ open: false, msg: null });
  };

  const handleCancelarConfirmacao = async () => {
    await sendMessage('Não, cancelar');
    setConfirmDialog({ open: false, msg: null });
  };

  // Mensagens enriquecidas (adiciona botão de "Ver Regras" quando há regras_json)
  const messagesEnriquecidas = messages.map((msg) => {
    if (msg.role === 'assistant' && msg.regras_json) {
      return {
        ...msg,
        content: `${msg.content}\n\n📜 Regras sugeridas disponíveis — use o botão abaixo para visualizar.`,
      };
    }
    return msg;
  });

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader
        title="Assistente de Segmentação"
        subtitle={segIdContexto ? `Contexto: ${segIdContexto.slice(0, 12)}...` : 'Chat livre'}
      >
        <Button
          variant="outlined"
          startIcon={<DeleteSweepIcon />}
          onClick={clearMessages}
          disabled={messages.length === 0}
        >
          Limpar Chat
        </Button>
      </PageHeader>

      {/* Conteúdo principal */}
      <Box sx={{ flex: 1, display: 'flex', gap: 2, overflow: 'hidden' }}>
        {/* Painel de chat */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <ChatPanel
            messages={messagesEnriquecidas}
            onSendMessage={handleSendMessage}
            loading={loading}
            placeholder="Pergunte sobre segmentações, peça para criar regras..."
          />
        </Box>

        {/* Painel lateral */}
        <Box sx={{ width: 280, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Sugestões */}
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <SmartToyIcon fontSize="small" /> Sugestões
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              {SUGESTOES_INICIAIS.map((s, i) => (
                <Chip
                  key={i}
                  label={s}
                  size="small"
                  variant="outlined"
                  onClick={() => handleSendMessage(s)}
                  sx={{
                    height: 'auto',
                    '& .MuiChip-label': { whiteSpace: 'normal', py: 0.5, fontSize: '0.75rem' },
                    cursor: 'pointer',
                  }}
                />
              ))}
            </Box>
          </Paper>

          {/* Regras sugeridas (quando disponíveis) */}
          {regrasDialog.regras && (
            <Paper sx={{ p: 2, border: '2px solid', borderColor: 'primary.main' }}>
              <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <RuleIcon fontSize="small" color="primary" /> Regras Sugeridas
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                Público: {regrasDialog.regras.publico_base || 'N/A'}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  size="small"
                  variant="contained"
                  onClick={handleAplicarRegras}
                >
                  Aplicar no Builder
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<ContentCopyIcon />}
                  onClick={handleCopiarRegras}
                >
                  Copiar JSON
                </Button>
              </Box>
            </Paper>
          )}

          {/* Contexto ativo */}
          {segIdContexto && (
            <Paper sx={{ p: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
              <Typography variant="caption">Contexto ativo:</Typography>
              <Typography variant="body2" fontFamily="monospace" noWrap>
                {segIdContexto}
              </Typography>
              <Button
                size="small"
                sx={{ mt: 1 }}
                onClick={() => navigate(`/segmentacoes/${segIdContexto}`)}
              >
                Ver segmentação
              </Button>
            </Paper>
          )}
        </Box>
      </Box>

      {/* Dialog de confirmação */}
      <Dialog open={confirmDialog.open} onClose={handleCancelarConfirmacao}>
        <DialogTitle>Confirmar Ação</DialogTitle>
        <DialogContent>
          <Typography>
            O assistente precisa da sua confirmação para prosseguir.
          </Typography>
          {confirmDialog.msg?.acao && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Ação: <strong>{confirmDialog.msg.acao}</strong>
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelarConfirmacao}>Cancelar</Button>
          <Button onClick={handleConfirmar} variant="contained">Confirmar</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
}
