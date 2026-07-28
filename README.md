# Plataforma CDP

Projeto composto por 4 sistemas independentes (Databricks Apps):
- **S1 - SegmentHub**: gestão de segmentações
- **S3 - EngagementHub**: campanhas, jornadas, disparos
- **S2 - ClientView 360**: visão unificada do cliente + OBO/RLS
- **S4 - CompassHub**: analytics, KPIs, OKRs, relatórios

## Setup rápido

1. Execute `python setup_projeto.py` para criar a estrutura (já feito)
2. Sincronize o shared-ui: `./scripts/sync-shared-ui.sh`
3. Instale dependências de cada app (cd app/ && pip install -r requirements.txt)
4. Execute a Fase 0 (DDLs, seeds, RBAC) conforme COMO-PROSSEGUIR.md

## Documentação

- COMO-PROSSEGUIR.md - guia operacional
- ESTRUTURA-PROJETO.md - arquitetura
- CONTRATOS-DADOS-EVENTOS.md - integração
- ROADMAP-00-MESTRE.md - convenções e índice

## Deploy

Cada app é um Databricks App independente:
- `segmenthub/`
- `engagementhub/`
- `clientview360/`
- `compasshub/`
