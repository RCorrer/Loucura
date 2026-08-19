"""Render Engine para peças (S3-BACK-03).

Renderiza conteudo_json em HTML (email) ou texto (WhatsApp)
com substituição de variáveis via Jinja2.
"""

import re
import json
import logging
from typing import Optional
from jinja2 import Environment, BaseLoader

logger = logging.getLogger(__name__)

# Variáveis mock para preview
MOCK_VARIAVEIS = {
    "nome": "Maria Silva",
    "primeiro_nome": "Maria",
    "cpf_cnpj": "***.***.***-00",
    "email": "maria.silva@email.com",
    "telefone": "(11) 99999-0000",
    "limite_aprovado": "R$ 15.000,00",
    "produto": "Cartão Platinum",
    "agencia": "0001",
    "conta": "12345-6",
    "link_ativacao": "https://bradesco.com.br/ativar?t=MOCK",
    "codigo": "123456",
    "data_vencimento": "15/09/2026",
    "valor_fatura": "R$ 1.250,00",
}


def extrair_variaveis(conteudo_json: str) -> list:
    """Extrai variáveis {{var}} do conteúdo da peça."""
    try:
        conteudo = json.loads(conteudo_json) if isinstance(conteudo_json, str) else conteudo_json
    except (json.JSONDecodeError, TypeError):
        return []

    textos = []
    _extrair_textos(conteudo, textos)

    variaveis = set()
    pattern = re.compile(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}')
    for texto in textos:
        variaveis.update(pattern.findall(texto))

    return sorted(variaveis)


def _extrair_textos(obj, textos: list):
    """Recursivamente extrai strings de um objeto JSON."""
    if isinstance(obj, str):
        textos.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _extrair_textos(v, textos)
    elif isinstance(obj, list):
        for item in obj:
            _extrair_textos(item, textos)


def render_preview(
    conteudo_json: str,
    canal: str,
    variaveis_override: Optional[dict] = None,
    assunto: Optional[str] = None,
) -> dict:
    """Renderiza preview da peça com variáveis substituídas.

    Returns:
        {html, texto, assunto_renderizado, variaveis_usadas, variaveis_faltantes}
    """
    vars_ctx = {**MOCK_VARIAVEIS}
    if variaveis_override:
        vars_ctx.update(variaveis_override)

    variaveis_usadas = extrair_variaveis(conteudo_json)
    variaveis_faltantes = [v for v in variaveis_usadas if v not in vars_ctx]

    for v in variaveis_faltantes:
        vars_ctx[v] = f"[{v}]"

    try:
        conteudo = json.loads(conteudo_json) if isinstance(conteudo_json, str) else conteudo_json
    except (json.JSONDecodeError, TypeError):
        return {"html": None, "texto": "Erro: JSON inválido",
                "assunto_renderizado": None, "variaveis_usadas": [], "variaveis_faltantes": []}

    env = Environment(loader=BaseLoader(), undefined=_SafeUndefined)

    assunto_renderizado = None
    if assunto:
        assunto_renderizado = _render_str(assunto, vars_ctx, env)

    if canal == "email":
        html = _render_email(conteudo, vars_ctx, env)
        return {"html": html, "texto": None, "assunto_renderizado": assunto_renderizado,
                "variaveis_usadas": variaveis_usadas, "variaveis_faltantes": variaveis_faltantes}
    elif canal == "whatsapp":
        texto = _render_whatsapp(conteudo, vars_ctx, env)
        return {"html": None, "texto": texto, "assunto_renderizado": None,
                "variaveis_usadas": variaveis_usadas, "variaveis_faltantes": variaveis_faltantes}
    else:
        return {"html": None, "texto": f"Canal '{canal}' não suportado",
                "assunto_renderizado": None, "variaveis_usadas": variaveis_usadas,
                "variaveis_faltantes": variaveis_faltantes}


def _render_email(conteudo: dict, ctx: dict, env: Environment) -> str:
    """Renderiza email a partir de blocks."""
    blocks = conteudo.get("blocks", [])
    parts = ['<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">']

    for block in blocks:
        btype = block.get("type", "text")
        if btype == "text":
            rendered = _render_str(block.get("content", ""), ctx, env)
            parts.append(f'<p style="margin:16px 0;">{rendered}</p>')
        elif btype == "header":
            src = block.get("src", "")
            parts.append(f'<div style="text-align:center;padding:20px;"><img src="{src}" alt="header" style="max-width:100%;"/></div>')
        elif btype == "button":
            label = _render_str(block.get("label", "Clique"), ctx, env)
            url = _render_str(block.get("url", "#"), ctx, env)
            parts.append(f'<div style="text-align:center;margin:24px 0;"><a href="{url}" '
                         f'style="background:#CC092F;color:white;padding:12px 32px;'
                         f'text-decoration:none;border-radius:4px;">{label}</a></div>')
        elif btype == "image":
            parts.append(f'<div style="text-align:center;"><img src="{block.get("src","")}" style="max-width:100%;"/></div>')
        elif btype == "divider":
            parts.append('<hr style="border:none;border-top:1px solid #EDEDED;margin:24px 0;"/>')

    parts.append('</body></html>')
    return '\n'.join(parts)


def _render_whatsapp(conteudo: dict, ctx: dict, env: Environment) -> str:
    """Renderiza WhatsApp: substitui {{1}}, {{2}} posicionais."""
    corpo = conteudo.get("corpo", conteudo.get("body", ""))
    params = conteudo.get("params", conteudo.get("variaveis_posicionais", []))

    texto = corpo
    for i, param_name in enumerate(params, start=1):
        valor = ctx.get(param_name, f"[{param_name}]")
        texto = texto.replace(f"{{{{{i}}}}}", valor)

    texto = _render_str(texto, ctx, env)
    return texto


def _render_str(text: str, ctx: dict, env: Environment) -> str:
    """Render Jinja2 seguro."""
    try:
        return env.from_string(text).render(**ctx)
    except Exception:
        return text


class _SafeUndefined:
    """Retorna placeholder ao invés de erro."""
    def __init__(self, *args, **kwargs):
        self._name = kwargs.get('name', '?')
    def __str__(self): return f"[{self._name}]"
    def __repr__(self): return f"[{self._name}]"
    def __bool__(self): return False
    def __iter__(self): return iter([])
