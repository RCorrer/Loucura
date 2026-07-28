-- s0_comum/02 - Governança transversal: RBAC + consentimento

CREATE TABLE IF NOT EXISTS plataforma.governanca.usuarios_perfil (
  usuario_id     STRING   NOT NULL,
  nome           STRING,
  sistema        STRING   NOT NULL COMMENT 'segmenthub/clientview360/engagement/analytics',
  perfil         STRING   NOT NULL COMMENT 'admin/analista/gerente/vendedor/viewer',
  ativo          BOOLEAN  DEFAULT true,
  concedido_por  STRING,
  concedido_em   TIMESTAMP DEFAULT current_timestamp(),
  revogado_por   STRING,
  revogado_em    TIMESTAMP
) USING DELTA
COMMENT 'RBAC unificado dos 4 sistemas (1 usuário = N linhas, granular por sistema)';

CREATE TABLE IF NOT EXISTS plataforma.governanca.consentimento (
  cpf_cnpj       STRING   NOT NULL,
  canal          STRING   NOT NULL COMMENT 'email/whatsapp/push/todos',
  status         STRING   COMMENT 'opt_in/opt_out',
  base_legal     STRING   COMMENT 'consentimento/legitimo_interesse/solicitacao_titular',
  origem         STRING   COMMENT 'quem/qual sistema alterou',
  atualizado_em  TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
COMMENT 'Consentimento por canal. Escrito pelo S2 (não-perturbe); aplicado pelo S3 (filtro de disp';