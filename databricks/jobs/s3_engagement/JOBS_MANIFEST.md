# JOBS_MANIFEST — S3 EngagementHub

> 7 Jobs | Status: Scaffold criado, implementação pendente

---

## Jobs Planejados

| Job | Arquivo | Gatilho | Status |
|---|---|---|---|
| engagement_orquestrador | `engagement_orquestrador.py` | Periódico | [ ] Pendente |
| motor_jornada | `motor_jornada.py` | ~5min | [ ] Pendente |
| motor_disparo | `motor_disparo.py` | ~5min | [ ] Pendente |
| otimizador_mab | `otimizador_mab.py` | Diário | [ ] Pendente |
| guardiao_campanha | `guardiao_campanha.py` | Periódico | [ ] Pendente |
| saude_operacional | `saude_operacional.py` | Periódico | [ ] Pendente |
| consumidor_conversao | `consumidor_conversao.py` | Batch periódico | [ ] Pendente |

## Ordem de Implementação

```
guardiao + orquestrador → motor_jornada → motor_disparo
→ otimizador_mab → saude_operacional → consumidor_conversao
```

## Changelog

| Data | Versão | Descrição |
|---|---|---|
| 2026-08-19 | 1.0 | Scaffold inicial (manifest + estrutura) |
