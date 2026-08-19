"""
Serviço de chamados (tickets).

Junta os repositórios (`tickets_repo`, `forms_repo`, `locations_repo`) e
aplica as regras de negócio do portal: como montar a descrição de um
chamado rápido, como montar a descrição de uma solicitação via formulário,
como saber se um chamado pode ser excluído pelo solicitante, etc.

As páginas (`pages_app/`) não devem montar payload de chamado nem decidir
regra nenhuma - só chamam estas funções.
"""
from __future__ import annotations

import re
import html
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from core.logging_config import obter_logger
from domain.models import (
    Categoria,
    Chamado,
    Formulario,
    Mensagem,
    PerguntaFormulario,
    SecaoFormulario,
)
from glpi.client import GLPIClient
from glpi import forms_repo, locations_repo, tickets_repo

logger = obter_logger(__name__)


# ----------------------------------------------------------------------
# Consulta
# ----------------------------------------------------------------------
def listar_meus_chamados(client: GLPIClient, localizacao_id: int, usuario_id: int) -> list[Chamado]:
    chamados = tickets_repo.buscar_chamados_do_usuario(client, localizacao_id, usuario_id)
    return sorted(chamados, key=lambda c: c.id, reverse=True)


@dataclass
class DetalheChamado:
    chamado: Chamado
    tecnicos: list[str]
    mensagens: list[Mensagem]
    solucoes: list[str]


def buscar_detalhe_chamado(client: GLPIClient, ticket_id: int) -> DetalheChamado:
    return DetalheChamado(
        chamado=tickets_repo.buscar_chamado(client, ticket_id),
        tecnicos=tickets_repo.buscar_tecnicos_do_chamado(client, ticket_id),
        mensagens=tickets_repo.buscar_mensagens_do_chamado(client, ticket_id),
        solucoes=tickets_repo.buscar_solucoes_do_chamado(client, ticket_id),
    )


def listar_categorias(client: GLPIClient) -> list[Categoria]:
    return locations_repo.listar_categorias_ativas(client)


# ----------------------------------------------------------------------
# Abertura de chamado
# ----------------------------------------------------------------------
def abrir_chamado_rapido(
    client: GLPIClient,
    *,
    solicitante: str,
    localizacao_id: int,
    localizacao_nome: str,
    usuario_id: int,
    categoria: Categoria,
    acesso_remoto: str,
    descricao: str,
) -> Chamado:
    titulo = f"{categoria.nome} - {localizacao_nome}"
    descricao_final = (
        f"Solicitante: {solicitante}\n"
        f"Filial: {localizacao_nome}\n"
        f"Tipo do problema: {categoria.nome}\n"
        f"Acesso remoto: {acesso_remoto}\n\n"
        f"Descrição:\n{descricao}"
    )

    chamado = tickets_repo.criar_chamado(
        client,
        titulo=titulo,
        descricao=descricao_final,
        localizacao_id=localizacao_id,
        usuario_id=usuario_id,
        categoria_id=categoria.id,
    )
    logger.info(
        "Chamado rápido #%s criado - filial '%s' (id=%s), categoria '%s', usuário id=%s",
        chamado.id, localizacao_nome, localizacao_id, categoria.nome, usuario_id,
    )
    return chamado


def abrir_chamado_via_formulario(
    client: GLPIClient,
    *,
    solicitante: str,
    localizacao_id: int,
    localizacao_nome: str,
    usuario_id: int,
    formulario: Formulario,
    respostas: dict[int, dict],
) -> Chamado:
    """`respostas` é {pergunta_id: {"pergunta": str, "valor": Any, "obrigatorio": bool}}."""
    blocos_resposta = "\n\n".join(
        f"{r['pergunta']}:\n{r['valor']}" for r in respostas.values()
    )

    descricao_final = (
        f"Solicitante: {solicitante}\n"
        f"Filial: {localizacao_nome}\n"
        f"Formulário: {formulario.nome}\n\n"
        f"Respostas do formulário:\n{blocos_resposta}"
    )

    chamado = tickets_repo.criar_chamado(
        client,
        titulo=formulario.nome,
        descricao=descricao_final,
        localizacao_id=localizacao_id,
        usuario_id=usuario_id,
    )
    logger.info(
        "Chamado via formulário #%s criado - filial '%s' (id=%s), formulário '%s', usuário id=%s",
        chamado.id, localizacao_nome, localizacao_id, formulario.nome, usuario_id,
    )
    return chamado


def campos_obrigatorios_faltando(respostas: dict[int, dict]) -> list[str]:
    return [
        r["pergunta"]
        for r in respostas.values()
        if r["obrigatorio"] and not str(r["valor"]).strip()
    ]


def listar_formularios_ativos(client: GLPIClient) -> list[Formulario]:
    return forms_repo.listar_formularios_ativos(client)


def listar_secoes_formulario(client: GLPIClient, formulario_id: int) -> list[SecaoFormulario]:
    return forms_repo.listar_secoes(client, formulario_id)


def listar_perguntas_secao(client: GLPIClient, secao_id: int) -> list[PerguntaFormulario]:
    return forms_repo.listar_perguntas(client, secao_id)


# ----------------------------------------------------------------------
# Interação com um chamado existente
# ----------------------------------------------------------------------
def enviar_mensagem_da_loja(
    client: GLPIClient, ticket_id: int, localizacao_nome: str, texto: str
) -> None:
    mensagem_formatada = f"Mensagem enviada pela loja: {localizacao_nome}\n\n{texto}"
    tickets_repo.enviar_followup(client, ticket_id, mensagem_formatada)
    logger.info("Mensagem enviada no chamado #%s pela filial '%s'", ticket_id, localizacao_nome)


def excluir_chamado(client: GLPIClient, chamado: Chamado) -> None:
    if not chamado.pode_ser_excluido_pelo_solicitante:
        raise ValueError(
            "Este chamado não pode ser excluído pelo portal, pois já está em "
            "atendimento, pendente, solucionado ou fechado."
        )

    tickets_repo.excluir_chamado(client, chamado.id)
    logger.info("Chamado #%s excluído pelo portal", chamado.id)


# ----------------------------------------------------------------------
# Texto: limpeza de HTML e busca "fuzzy" nos chamados
# ----------------------------------------------------------------------
def limpar_html(texto: str | None) -> str:
    """
    Extrai o texto legível de um campo HTML do GLPI (descrição, mensagem, solução).

    Retorna TEXTO PURO - ainda pode conter caracteres < > (de entidades
    decodificadas) e NÃO é seguro para inserir direto em HTML. Para exibir
    na tela dentro de um bloco `unsafe_allow_html=True`, use sempre
    `texto_para_html_seguro()` depois desta função.
    """
    if not texto:
        return ""

    texto = str(texto).replace("<p>", "").replace("</p>", "\n")
    texto = texto.replace("<br>", "\n").replace("<br />", "\n")
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = html.unescape(texto)
    texto = re.sub(r"\n{2,}", "\n", texto)
    return texto.strip()


def texto_para_html_seguro(texto: str) -> str:
    """
    Escapa texto puro (já processado por `limpar_html`) para ser inserido
    com segurança dentro de um `st.markdown(..., unsafe_allow_html=True)`,
    preservando as quebras de linha como `<br>`.

    Sem isso, um chamado ou mensagem com HTML malicioso poderia executar
    JavaScript no navegador de quem visualiza o chamado (XSS armazenado).
    """
    return html.escape(texto).replace("\n", "<br>")


_PADRAO_CAMPO = re.compile(r"^([^\n:]{2,80}):\s*(.*)$")


def estruturar_descricao(texto_limpo: str) -> list[tuple[str, str]]:
    """
    Tenta ler a descrição (já processada por `limpar_html`) como uma
    sequência de campos "Rótulo: valor" - é assim que este portal monta a
    descrição em `abrir_chamado_rapido` e `abrir_chamado_via_formulario`
    (ex.: "Solicitante: Leia", "Pergunta do formulário:" seguido do valor
    na linha de baixo).

    Retorna uma lista de (rótulo, valor) para a tela exibir como campos
    organizados em vez de um bloco de texto corrido. Se o texto não
    seguir esse padrão (ex.: chamado antigo ou descrição digitada livre),
    retorna [] e a tela volta a mostrar o texto puro.
    """
    campos: list[tuple[str, str]] = []
    rotulo_atual: str | None = None
    valor_atual: list[str] = []

    for linha in texto_limpo.split("\n"):
        linha = linha.strip()
        if not linha:
            continue

        casamento = _PADRAO_CAMPO.match(linha)
        if casamento:
            if rotulo_atual is not None:
                campos.append((rotulo_atual, " ".join(valor_atual).strip()))
            rotulo_atual = casamento.group(1).strip()
            resto = casamento.group(2).strip()
            valor_atual = [resto] if resto else []
        elif rotulo_atual is not None:
            valor_atual.append(linha)
        else:
            return []  # não segue o padrão esperado - melhor não arriscar exibir errado

    if rotulo_atual is not None:
        campos.append((rotulo_atual, " ".join(valor_atual).strip()))

    return campos


def _normalizar(texto: str) -> str:
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _palavra_parecida(palavra: str, palavras_texto: list[str]) -> bool:
    for p in palavras_texto:
        if palavra == p:
            return True
        if len(palavra) >= 4 and len(p) >= 4 and SequenceMatcher(None, palavra, p).ratio() >= 0.85:
            return True
    return False


def chamado_corresponde_pesquisa(pesquisa: str, chamado: Chamado) -> bool:
    """Busca tolerante a acentuação, maiúsculas e pequenos erros de digitação."""
    pesquisa_norm = _normalizar(pesquisa)

    if not pesquisa_norm:
        return True

    texto_busca = " ".join(
        [str(chamado.id), chamado.titulo, chamado.descricao_html, chamado.data_abertura]
    )
    texto_norm = _normalizar(texto_busca)

    if pesquisa_norm in texto_norm:
        return True

    palavras_texto = texto_norm.split()
    return all(_palavra_parecida(p, palavras_texto) for p in pesquisa_norm.split())