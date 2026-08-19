# Portal Loja + GLPI

Portal interno para lojas abrirem e acompanharem chamados de TI no GLPI,
além de consultarem os equipamentos cadastrados na filial.

Mesma funcionalidade da versão anterior do projeto, reescrita em camadas
para ficar fácil de manter: para adicionar uma tela nova, mexer numa regra
de negócio, ou trocar a cor da marca, existe sempre **um único lugar**
certo para editar.

## Arquitetura

```
config.py                  → única fonte de variáveis de ambiente (.env)
core/
  exceptions.py             → exceções nomeadas usadas em toda a app
glpi/
  client.py                  → cliente HTTP puro da API do GLPI (sem Streamlit)
  locations_repo.py           → acesso a Location / ITILCategory
  users_repo.py                → acesso a User
  inventory_repo.py             → acesso a Computer/Monitor/Printer/PDU
  tickets_repo.py                → acesso a Ticket e sub-itens (followup, tarefas, soluções)
  forms_repo.py                   → acesso ao plugin Formcreator
domain/
  models.py                        → dataclasses tipadas (Chamado, Localizacao, Equipamento...)
services/
  auth_service.py                   → login + montagem da sessão do usuário
  dashboard_service.py               → resumo da filial (home)
  ticket_service.py                   → regras de abertura/busca/exclusão de chamado
  equipment_service.py                 → inventário da filial
ui/
  theme.py                              → CSS único e centralizado (cores da marca ficam aqui)
  components.py                          → cabeçalho, cards, badges reutilizáveis
  navigation.py                           → menu lateral
  state.py                                 → acesso ao st.session_state sem strings soltas
  cache.py                                  → cache das consultas de leitura (ver seção Performance)
pages_app/
  login.py, home.py, abrir_chamado.py,
  meus_chamados.py, meus_equipamentos.py    → páginas finas: só chamam services/cache + ui
app.py                                       → roteamento entre páginas, nada mais
tests/
  test_ticket_service.py                     → testes das regras de negócio (sem precisar de GLPI real)
```

**Regra de ouro:** dado de fora (GLPI) entra pelo `glpi/`, vira modelo em
`domain/`, regra de negócio mora em `services/`, e `pages_app/` só
desenha a tela. Uma página nunca deveria montar payload de API, e um
repositório do `glpi/` nunca deveria importar `streamlit`.

### Por que isso ajuda na manutenção
- **Achar as coisas fica previsível**: "chamado não abre" → `services/ticket_service.py`
  ou `glpi/tickets_repo.py`. "Cor errada" → `ui/theme.py`. Não precisa
  vasculhar 5 arquivos de 500 linhas.
- **Testável sem GLPI no ar**: `services/` recebe o `GLPIClient` como
  parâmetro, então dá pra simular (mock) as respostas — veja `tests/`.
- **Sem duplicação de CSS**: existe um `ui/theme.py`, os outros arquivos
  não sabem o que é cor de marca.
- **Sem acoplamento ao Streamlit na camada de API**: `glpi/*.py` não
  importa `streamlit`, então poderia virar uma API própria ou um script
  no futuro sem reescrever nada.

## Performance com vários acessos simultâneos

Quatro problemas de carga foram corrigidos, cada um isolado numa camada:

| Problema | Onde foi corrigido | O que mudou |
|---|---|---|
| Cada consulta baixava a tabela inteira do GLPI e filtrava em Python | `glpi/client.py` (`list_all`), `glpi/tickets_repo.py`, `glpi/inventory_repo.py` | `list_all(itemtype, filtros={...})` pede pro GLPI já filtrar por `locations_id` no servidor (`searchText`). Como o `searchText` do GLPI faz "contém" (não "é igual"), o resultado ainda passa por `filtrar_por_localizacao` em Python como garantia de exatidão — mas o volume trafegado já vem bem menor |
| N+1 em "meus chamados" (1 requisição por chamado da filial) | `glpi/tickets_repo.py::buscar_chamados_do_usuario` | Agora são sempre **2** requisições no total (chamados da filial + vínculos do usuário), não importa quantos chamados a filial tenha no histórico |
| Conexão HTTP nova a cada requisição | `glpi/client.py` | `GLPIClient` usa uma `requests.Session()` reaproveitada por instância, reduzindo o overhead de abrir TCP/TLS a cada chamada |
| Toda troca de aba/clique refazia as mesmas consultas | `ui/cache.py` | Consultas de leitura passam por `st.cache_data`: 30s de TTL para dado operacional (chamados, equipamentos), 5 minutos para dado cadastral (localizações, categorias, formulários). Qualquer escrita (abrir chamado, enviar mensagem, excluir) chama `cache.invalidar_dados_operacionais()` logo em seguida, então o usuário nunca vê dado desatualizado por causa da própria ação dele |

**Por que o cache não fica em `services/`:** os serviços continuam sem
depender do Streamlit (testáveis com mock, sem precisar rodar a app) —
`st.cache_data` é uma ferramenta do Streamlit, então mora em `ui/cache.py`.
Se um dado começar a parecer desatualizado pro usuário, o TTL se ajusta
num lugar só.

**Limite dessa abordagem:** o filtro por `searchText` melhora bastante,
mas ainda depende do GLPI aceitar filtro de texto nesses campos. Se o
volume de chamados/equipamentos crescer muito (milhares por filial), o
próximo passo seria usar o endpoint `/search/{itemtype}` do GLPI com
`searchtype=equals` (filtro exato no servidor) — isso exige mapear o
ID numérico do campo `locations_id` por tipo de item na sua instalação
específica do GLPI, então não entrou aqui por depender da configuração
de cada ambiente.

## Logs

Todo evento importante fica registrado em `logs/portal.log` (rotativo,
até 5 arquivos de 2MB) e também no console (`docker logs` captura isso
automaticamente):

- Login bem-sucedido e falha de login (nunca a senha)
- Abertura de chamado (rápido ou via formulário), com número do
  chamado, filial e usuário
- Envio de mensagem e exclusão de chamado
- Qualquer erro de comunicação com o GLPI (timeout, status de erro)
- Qualquer erro não esperado que aconteça ao carregar uma página

Ajuste o nível com `LOG_LEVEL` no `.env` (`DEBUG`, `INFO`, `WARNING`,
`ERROR` — padrão `INFO`). Quando uma loja relatar um problema, comece
por `logs/portal.log` filtrando pelo horário e, se souber, pelo número
do chamado ou nome de usuário.

## Sobre a escala deste projeto

Este portal foi dimensionado para o uso real esperado: algo em torno de
0 a 20 chamados por dia (~100/mês), não milhares de acessos simultâneos.
Por isso as otimizações de performance (cache, filtro no servidor,
correção do N+1) já são suficientes com folga para esse volume — não há
necessidade de infraestrutura adicional (fila, banco de cache externo,
múltiplas réplicas) para esse cenário. Se o uso crescer muito além
disso no futuro, o ponto de partida para escalar está documentado na
seção de Performance abaixo.

## Rodando localmente

### 1. Pré-requisitos
- Python 3.11+ instalado
- Acesso à API REST do GLPI (URL + App-Token)

### 2. Configurar variáveis de ambiente
```bash
cp .env.example .env
```
Edite o `.env` e preencha:
```
GLPI_URL=https://seu-glpi.exemplo.com/apirest.php
APP_TOKEN=seu_app_token_aqui
```

### 3. Criar ambiente virtual e instalar dependências
```bash
python -m venv .venv

# Linux/Mac
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 4. Rodar a aplicação
```bash
streamlit run app.py
```
Acesse em `http://localhost:8501`.

### 5. (Opcional) Rodar os testes
```bash
pip install pytest
pytest
```

## Rodando com Docker

```bash
docker compose up --build
```
A aplicação sobe em `http://localhost:5854` (porta configurável no
`docker-compose.yml`).

## Adicionando uma página nova (exemplo prático)

1. Crie `pages_app/minha_pagina.py` com uma função `render()`.
2. Se precisar de dado novo do GLPI, adicione a função em
   `glpi/<recurso>_repo.py` (ou crie um repo novo) e a regra de negócio
   correspondente em `services/`.
3. Registre a página em `ui/navigation.py` (dicionário `PAGINAS`) e em
   `app.py` (dicionário `PAGINAS`).

Nenhum outro arquivo precisa mudar.
