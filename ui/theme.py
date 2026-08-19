"""
Tema visual do portal.

No projeto antigo existiam 4 blocos de CSS diferentes (auth.py,
utils/layout.py, views/home.py, views/abrir_chamado.py), cada um
redefinindo cores e espaçamentos parecidos. Mudar a cor da marca
significava caçar cada bloco. Aqui existe UM só CSS, aplicado uma vez
por página, e a paleta fica em variáveis no topo do arquivo.
"""
from __future__ import annotations

import streamlit as st

# Paleta da marca — mude aqui para re-skinar o portal inteiro.
COR_PRIMARIA = "#003b73"
COR_PRIMARIA_CLARA = "#0056a6"
COR_DESTAQUE = "#ffd000"
COR_FUNDO = "#f4f6fa"

CSS_BASE = f"""
<style>
    #MainMenu, footer, header[data-testid="stHeader"],
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"] {{
        visibility: hidden !important;
    }}

    .stApp {{ background: {COR_FUNDO} !important; }}

    .block-container {{
        max-width: 1120px !important;
        padding-top: 2rem !important;
    }}

    h1, h2, h3 {{ color: {COR_PRIMARIA} !important; font-weight: 800 !important; }}

    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3 {{
        border-left: 5px solid {COR_DESTAQUE};
        padding-left: 12px;
    }}

    .stButton > button {{
        background: linear-gradient(90deg, {COR_PRIMARIA}, {COR_PRIMARIA_CLARA}) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        box-shadow: 0 6px 16px rgba(0, 59, 115, 0.22) !important;
    }}

    div[data-testid="stForm"] {{
        background: #fff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 20px !important;
        padding: 28px 34px !important;
        box-shadow: 0 12px 28px rgba(15, 42, 70, 0.08) !important;
    }}

    /* --- Sidebar --- */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #003b73 0%, {COR_PRIMARIA_CLARA} 100%) !important;
    }}

    section[data-testid="stSidebar"] * {{ color: #fff !important; }}

    section[data-testid="stSidebar"] .stRadio label {{
        background: rgba(255,255,255,0.10) !important;
        border: 1px solid rgba(255,255,255,0.16) !important;
        border-radius: 14px !important;
        padding: 11px 13px !important;
        margin-bottom: 3px !important;
    }}

    section[data-testid="stSidebar"] label:has(input[type="radio"]:checked) {{
        background: linear-gradient(90deg, rgba(255,208,0,0.28), rgba(255,255,255,0.16)) !important;
        border-color: rgba(255,208,0,0.70) !important;
    }}

    section[data-testid="stSidebar"] .stButton > button {{
        background: {COR_DESTAQUE} !important;
        color: {COR_PRIMARIA} !important;
    }}

    /* --- Componentes reutilizáveis (ver ui/components.py) --- */
    .brand-bar {{
        height: 6px;
        background: linear-gradient(90deg, {COR_PRIMARIA}, {COR_PRIMARIA_CLARA}, {COR_DESTAQUE});
        border-radius: 20px;
        margin-bottom: 20px;
    }}

    .metric-card {{
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 8px 20px rgba(15, 42, 70, 0.07);
        min-height: 120px;
    }}

    .metric-card .icone {{ font-size: 22px; margin-bottom: 6px; }}
    .metric-card .titulo {{ color: #475569; font-size: 13px; font-weight: 800; }}
    .metric-card .valor {{ color: {COR_PRIMARIA}; font-size: 30px; font-weight: 900; }}
    .metric-card .desc {{ color: #64748b; font-size: 12px; margin-top: 6px; }}

    .badge {{
        display: inline-block;
        color: white;
        padding: 5px 11px;
        border-radius: 999px;
        font-weight: 800;
        font-size: 12px;
    }}

    .ticket-card {{
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 12px;
        box-shadow: 0 8px 18px rgba(15, 42, 70, 0.06);
    }}

    .ticket-card .titulo {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        font-weight: 900;
        color: {COR_PRIMARIA};
        font-size: 16px;
        margin-bottom: 6px;
    }}

    .ticket-card .meta {{ color: #64748b; font-size: 13px; }}

    .equip-card {{
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 16px 18px;
        margin-bottom: 12px;
        box-shadow: 0 8px 18px rgba(15, 42, 70, 0.06);
        display: flex;
        align-items: center;
        gap: 14px;
    }}

    .equip-card .equip-icone {{
        font-size: 22px;
        background: {COR_FUNDO};
        border-radius: 12px;
        width: 46px;
        height: 46px;
        min-width: 46px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .equip-card .equip-nome {{
        font-weight: 900;
        color: {COR_PRIMARIA};
        font-size: 15px;
    }}

    .equip-card .equip-serie {{ color: #64748b; font-size: 13px; margin-top: 2px; }}

    .campos-descricao {{
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 6px 22px;
    }}

    .campo-linha {{
        padding: 12px 0;
        border-bottom: 1px solid #e5e7eb;
    }}
    .campo-linha:last-child {{ border-bottom: none; }}

    .campo-linha .campo-rotulo {{
        color: #64748b;
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-bottom: 3px;
    }}
    .campo-linha .campo-valor {{
        color: #1e293b;
        font-size: 15px;
        font-weight: 600;
        white-space: pre-wrap;
    }}
    .campo-linha.campo-secao .campo-rotulo {{
        color: {COR_PRIMARIA};
        font-size: 13px;
        margin-top: 4px;
    }}

    .mensagem-bolha {{
        padding: 14px;
        border-radius: 14px;
        margin: 10px 0;
        max-width: 75%;
    }}

    .mensagem-loja {{ background: #dcfce7; color: #14532d; margin-left: auto; border-radius: 14px 14px 2px 14px; }}
    .mensagem-ti {{ background: #eff6ff; color: #0f2d5c; margin-right: auto; border-radius: 14px 14px 14px 2px; }}
    .mensagem-meta {{ font-size: 11px; opacity: 0.7; margin-top: 6px; }}

    .callout {{
        border-radius: 16px;
        padding: 16px 20px;
        font-weight: 700;
        margin: 16px 0;
    }}
    .callout-info {{ background: #e8f3ff; border-left: 6px solid #2563eb; color: #0f3b73; }}
    .callout-warning {{ background: #fff7ed; border-left: 6px solid #f97316; color: #7c2d12; }}
</style>
"""

CSS_LOGIN = f"""
<style>
    html, body {{ overflow: hidden !important; }}
    [data-testid="stAppViewContainer"] > .main {{ padding: 0 !important; }}
    .block-container {{ padding: 0 !important; max-width: 100% !important; }}

    div[data-testid="stHorizontalBlock"] {{
        gap: 0 !important;
        min-height: 100vh !important;
    }}

    div[data-testid="stHorizontalBlock"] > div:nth-child(2) {{
        min-height: 100vh !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: {COR_FUNDO} !important;
    }}

    div[data-testid="stHorizontalBlock"] > div:nth-child(2) > div {{
        width: 420px !important;
        background: #fff !important;
        border-radius: 18px !important;
        border: 1px solid #e4e8f0 !important;
        padding: 38px 42px !important;
        box-shadow: 0 22px 55px rgba(0,0,0,0.12) !important;
    }}

    .login-titulo {{
        text-align: center;
        color: {COR_PRIMARIA};
        font-size: 21px;
        font-weight: 800;
        margin-bottom: 26px;
    }}

    .login-rodape {{
        text-align: center;
        margin-top: 20px;
        padding-top: 18px;
        border-top: 1px solid #e4e8f0;
        color: #6e7583;
        font-size: 13px;
    }}
</style>
"""


def aplicar_tema() -> None:
    st.markdown(CSS_BASE, unsafe_allow_html=True)


def aplicar_tema_login() -> None:
    st.markdown(CSS_BASE + CSS_LOGIN, unsafe_allow_html=True)