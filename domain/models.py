"""
Modelos de domínio.

No projeto antigo, cada view usava chamado.get("name"), chamado.get("status")
etc. direto no dict que a API do GLPI devolve. Isso funciona, mas qualquer
typo no nome do campo só quebra em produção, e não existe um lugar único
que diga "um chamado tem estes campos". Aqui, cada tipo do GLPI que a
aplicação usa vira uma dataclass, construída a partir do dict cru em um
único lugar (`from_glpi`). O resto do código passa a lidar com objetos com
autocompletar, não com dicionários.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

STATUS_NOMES = {
    1: "Novo",
    2: "Em atendimento",
    3: "Planejado",
    4: "Pendente",
    5: "Solucionado",
    6: "Fechado",
}

STATUS_CORES = {
    1: "#f59e0b",
    2: "#2563eb",
    3: "#2563eb",
    4: "#f97316",
    5: "#22c55e",
    6: "#374151",
}


@dataclass(frozen=True)
class Localizacao:
    id: int
    nome: str
    nome_completo: str

    @classmethod
    def from_glpi(cls, dados: dict) -> "Localizacao":
        nome = dados.get("name", "")
        return cls(
            id=dados.get("id"),
            nome=nome,
            nome_completo=dados.get("completename") or nome,
        )


@dataclass(frozen=True)
class Usuario:
    id: int
    login: str
    nome: str
    localizacao_id: int | None = None

    @classmethod
    def from_glpi(cls, dados: dict, login_fallback: str = "") -> "Usuario":
        nome = f"{dados.get('firstname', '')} {dados.get('realname', '')}".strip()
        return cls(
            id=dados.get("id"),
            login=dados.get("name") or login_fallback,
            nome=nome or dados.get("name") or login_fallback,
            localizacao_id=dados.get("locations_id"),
        )


@dataclass(frozen=True)
class Categoria:
    id: int
    nome: str

    @classmethod
    def from_glpi(cls, dados: dict) -> "Categoria":
        return cls(id=dados.get("id"), nome=dados.get("completename") or dados.get("name", ""))


@dataclass
class Chamado:
    id: int
    titulo: str
    descricao_html: str
    status: int
    data_abertura: str
    data_fechamento: str | None
    localizacao_id: int | None
    usuario_recipient_id: int | None

    @property
    def status_nome(self) -> str:
        return STATUS_NOMES.get(self.status, "Desconhecido")

    @property
    def status_cor(self) -> str:
        return STATUS_CORES.get(self.status, "#64748b")

    @property
    def esta_aberto(self) -> bool:
        return self.status in (1, 2, 3, 4)

    @property
    def pode_ser_excluido_pelo_solicitante(self) -> bool:
        return self.status == 1

    @classmethod
    def from_glpi(cls, dados: dict) -> "Chamado":
        return cls(
            id=dados.get("id"),
            titulo=dados.get("name", "Sem título"),
            descricao_html=dados.get("content", ""),
            status=dados.get("status"),
            data_abertura=dados.get("date", ""),
            data_fechamento=dados.get("closedate") or dados.get("solvedate"),
            localizacao_id=dados.get("locations_id"),
            usuario_recipient_id=dados.get("users_id_recipient"),
        )


@dataclass(frozen=True)
class Mensagem:
    conteudo_html: str
    data: str
    da_loja: bool

    @classmethod
    def from_glpi_followup(cls, dados: dict) -> "Mensagem":
        conteudo = dados.get("content", "")
        return cls(
            conteudo_html=conteudo,
            data=dados.get("date", ""),
            da_loja="Mensagem enviada pela loja" in conteudo,
        )


@dataclass(frozen=True)
class Equipamento:
    id: int
    nome: str
    numero_serie: str
    tipo: str  # "Computer" | "Monitor" | "Printer" | "PDU"

    @classmethod
    def from_glpi(cls, dados: dict, tipo: str) -> "Equipamento":
        return cls(
            id=dados.get("id"),
            nome=dados.get("name", ""),
            numero_serie=dados.get("serial") or dados.get("otherserial") or "",
            tipo=tipo,
        )


@dataclass
class InventarioFilial:
    computadores: list[Equipamento] = field(default_factory=list)
    monitores: list[Equipamento] = field(default_factory=list)
    impressoras: list[Equipamento] = field(default_factory=list)
    pdus: list[Equipamento] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.computadores)
            + len(self.monitores)
            + len(self.impressoras)
            + len(self.pdus)
        )


@dataclass(frozen=True)
class Formulario:
    id: int
    nome: str

    @classmethod
    def from_glpi(cls, dados: dict) -> "Formulario":
        return cls(id=dados.get("id"), nome=dados.get("name", "Formulário"))


@dataclass(frozen=True)
class SecaoFormulario:
    id: int
    nome: str
    ordem: int

    @classmethod
    def from_glpi(cls, dados: dict) -> "SecaoFormulario":
        return cls(id=dados.get("id"), nome=dados.get("name", ""), ordem=dados.get("order", 0))


import json


def _extrair_opcoes_formulario(bruto) -> list[str]:
    """
    Interpreta o campo "values" de uma pergunta do plugin Formcreator, que
    guarda as opções configuradas no GLPI para perguntas do tipo
    dropdown/select/radio/checkboxes.

    Formatos aceitos: lista JSON (`["Op1","Op2"]`), objeto JSON
    (`{"0":"Op1","1":"Op2"}`) ou texto simples com uma opção por linha
    (formato legado do Formcreator).

    Campos do tipo "glpiselect" (ligados dinamicamente a um itemtype do
    GLPI, ex.: Location) guardam configuração em vez de opções prontas -
    nesse caso devolvemos lista vazia, pois montar essas opções exigiria
    uma chamada extra à API; a tela deve tratar isso com um aviso em vez
    de exibir opções erradas.
    """
    if not bruto:
        return []

    try:
        dados = json.loads(bruto)
    except (TypeError, ValueError):
        return [linha.strip() for linha in str(bruto).splitlines() if linha.strip()]

    if isinstance(dados, list):
        return [str(v).strip() for v in dados if str(v).strip()]

    if isinstance(dados, dict):
        if "itemtype" in dados:
            return []
        return [str(v).strip() for v in dados.values() if str(v).strip()]

    return []


@dataclass(frozen=True)
class PerguntaFormulario:
    id: int
    nome: str
    tipo_campo: str
    obrigatoria: bool
    opcoes: list = None

    @classmethod
    def from_glpi(cls, dados: dict) -> "PerguntaFormulario":
        return cls(
            id=dados.get("id"),
            nome=dados.get("name", ""),
            tipo_campo=dados.get("fieldtype", "text"),
            obrigatoria=dados.get("required") == 1,
            opcoes=_extrair_opcoes_formulario(dados.get("values")),
        )


@dataclass(frozen=True)
class SessaoUsuario:
    """Estado de autenticação guardado durante a sessão do Streamlit."""

    usuario: Usuario
    localizacao: Localizacao
    autenticado_em: datetime = field(default_factory=datetime.now)