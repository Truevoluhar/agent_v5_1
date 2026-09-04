# agent_v5_1
Generična agentska zanka

## Arhitektura

Projekt je razdeljen na štiri dele:

- **agent/** - izvajalni mehanizem. `agent/runner.py` (`AgentRunner`) vsebuje ponovno uporabljivo agentsko zanko, ki jo poganjajo vtični povratni klici `emit`/`wait_for_input`. `agent/cli.py` je zdaj tanek enkratni adapter nad njim. Pakira se oziroma se izvaja v vsebniku samostojno (`agent/Dockerfile`).
- **service/** - trajni API za izvajanje agenta (`agent-api`). Agentski mehanizem uvozi neposredno v proces in ga izvaja kot upravljan, opazljiv in preklicljiv zagon namesto kot ločen CLI podproces - za utemeljitev zasnove glej "Agent GUI Integration.pdf". Izpostavlja `POST /api/runs`, `POST /api/runs:wait`, SSE `GET /api/runs/{id}/events`, `POST /api/runs/{id}/input`, `POST /api/runs/{id}/cancel` ter minimalni klepetalni uporabniški vmesnik na `/`. Zagone in dogodke trajno shranjuje v `data/runs/runs.sqlite3`, zato se lahko prekinjena seja brskalnika ponovno poveže z uporabo `after_sequence`.
- **client/** - neodvisno orodje (CLI + spletna nadzorna plošča) za pregledovanje in upravljanje skupnih podatkov: sej, pomnilnika, delovnega prostora in virov (polni CRUD - ustvarjanje/brisanje sej, dodajanje/urejanje/brisanje sporočil, nalaganje/urejanje/premikanje/brisanje datotek). Pakira se oziroma se izvaja v vsebniku samostojno (`client/Dockerfile`). Ni odvisen od paketa `agent`.
- **data/** - skupna priklopljena mapa (`session/`, `memory/`, `resources/`, `agent_workspace/`, `runs/`). Vse tri komponente se usklajujejo samo glede strukture te mape.

```text
AGENT (CLI, enkratni zagon) ---\
                               >--  data/ (bind mount)  <-->  CLIENT (pregled/urejanje)
AGENT-API (trajni) ------------/
```

Lokalno (brez vsebnikov) vse komponente privzeto uporabljajo `<repo>/data`. V Dockerju vsi vsebniki priklopijo `./data` na gostiteljskem sistemu v `/data`, kar nadzira okoljska spremenljivka `AGENT_DATA_ROOT`.

### Znane omejitve (še niso implementirane)

V skladu s faznim načrtom iz PDF-ja naslednji koraki za utrditev sistema namenoma **še niso** izvedeni in jih je treba implementirati pred javno izpostavitvijo sistema: prava avtentikacija (trenutno je `username` samo vrednost obrazca oziroma poizvedbenega parametra), izolacija delovnega prostora za posamezen zagon, zaklepi izvajanja za posamezno sejo, avtorizacija/odobritev orodij, omejitve ukazov lupine, roki ter omejitve izhoda in sočasnosti ter produkcijsko primerna shramba zagonov (Postgres/Redis) za okolja z več replikami. Register zagonov v `agent-api` je shranjen v pomnilniku posameznega procesa, zato `cancel`/`input` delujeta samo za proces, ki je zagon ustvaril (trajno shranjeni dogodki in status preživijo ponovni zagon, neposreden nadzor nad aktivnim zagonom pa ne).

## Kako zagnati

### Z Dockerjem

```bash
docker compose build
docker compose up -d bifrost agent-api client   # klepetalni UI: http://localhost:8100/?username=jon
                                         # nadzorna plošča podatkov: http://localhost:8000/?username=jon
docker compose run --rm agent --username jon --workspace agent_workspace --interactive false --test false --initial_prompt "..."
```

### Lokalno (brez vsebnikov)

Najprej je treba pripraviti Pythonovo okolje. Nastavitve agenta so določene v **pyproject.toml** (paket `agentv5`, samo mapa `agent/`). Odjemalec in storitev imata vsak svoje odvisnosti (`client/requirements.txt`, `service/requirements.txt`).

```bash
pip install -e .
pip install -r client/requirements.txt
pip install -r service/requirements.txt

agentv5 --username jon --workspace agent_workspace --interactive false --test false --initial_prompt "..."
python -m client.cli sessions-list --username jon
python -m client.api      # nadzorna plošča podatkov na http://localhost:8000/?username=jon
python -m service.api     # klepetalni UI + API za zagone na http://localhost:8100/?username=jon
```

### Bifrost gateway

All agent LLM requests use Bifrost's OpenAI-compatible API at
`http://localhost:8080/v1`. Set `BIFROST_API_KEY` in `.env` for the gateway
credential before starting the agent or `agent-api`. Configure each upstream
provider credential, such as `OPENAI_API_KEY`, on the Bifrost gateway itself.
Docker Compose starts Bifrost at `bifrost:8080` and applies that address to the
agent containers automatically.

Copy `.env.example` to `.env` and replace its placeholder values before using
Docker Compose.

For a Bifrost instance on another host, change every agent `base_url` in
`agent/config.yml` to that instance's `/v1` endpoint.

## Izvorna koda agenta

Izvorna koda agenta je v mapi **agent**.

## Izvorna koda odjemalca

Izvorna koda odjemalca je v mapi **client**.