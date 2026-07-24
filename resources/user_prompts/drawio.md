Ustvari celovit arhitekturni diagram za razvoj lokalno gostovanega osebnega AI-agenta, zasnovanega po podobnih načelih kot OpenClaw.

Končni rezultat mora biti dejanska, veljavna in urejevalna datoteka draw.io oziroma diagrams.net v formatu XML:

`ai-agent-architecture.drawio`

Ne ustvari samo opisa, slike, SVG-ja ali Mermaid kode. Dejansko generiraj celotno `.drawio` XML-datoteko, ki jo je mogoče neposredno odpreti in urejati v aplikaciji diagrams.net.

## Glavni cilj

Diagram naj predstavi celotno produkcijsko arhitekturo osebnega AI-agenta, ki:

* deluje lokalno oziroma self-hosted,
* sprejema zahteve iz različnih komunikacijskih kanalov,
* uporablja enega ali več LLM ponudnikov,
* podpira uporabo orodij,
* izvaja večkorakovne naloge,
* upravlja seje in dolgoročni spomin,
* podpira več agentov in podagente,
* uporablja vtičnike oziroma skills,
* izvaja periodične in dogodkovno sprožene naloge,
* uporablja varnostne omejitve in sandbox,
* omogoča nadzor, beleženje in spremljanje stroškov,
* ima spletni oziroma namizni uporabniški vmesnik.

Arhitektura naj bo podobna sistemom, kot je OpenClaw, vendar naj bo predstavljena kot samostojna, generična arhitektura in ne kot neposredna kopija projekta.

## Struktura draw.io dokumenta

Draw.io datoteka naj vsebuje najmanj naslednjih sedem strani:

1. `01 - System Overview`
2. `02 - Agent Runtime`
3. `03 - Request Flow`
4. `04 - Memory and Data`
5. `05 - Tools and Integrations`
6. `06 - Security Architecture`
7. `07 - Deployment and Development`

Vsaka stran mora biti pregledna, samostojna in dovolj podrobna, da jo lahko uporabi razvojna ekipa.

---

# 1. Stran: System Overview

Prikaži arhitekturo sistema od uporabnika do zunanjih storitev.

Diagram razdeli v naslednje horizontalne ali vertikalne plasti:

### A. Uporabniki in naprave

Vključi:

* končni uporabnik,
* spletni brskalnik,
* namizna aplikacija,
* mobilna aplikacija,
* CLI,
* glasovni vmesnik,
* administratorski uporabnik.

### B. Komunikacijski kanali

Vključi:

* Web Chat,
* REST API,
* WebSocket,
* Telegram,
* Discord,
* Slack,
* e-pošta,
* webhooki,
* glasovni vhod,
* periodični cron dogodki.

Kanale poveži z adapterji oziroma konektorji.

### C. Gateway oziroma Control Plane

Gateway naj bo osrednja komponenta sistema.

V njem prikaži:

* API Gateway,
* Authentication,
* Channel Adapters,
* Message Normalizer,
* Event Bus,
* Request Router,
* Agent Router,
* Session Manager,
* Rate Limiter,
* Policy Engine,
* Scheduler,
* Webhook Manager,
* Health Check,
* Configuration Manager.

Prikaži, da Gateway sprejema dogodke iz vseh kanalov ter jih usmerja do ustreznega agenta in seje.

### D. Agentna plast

Vključi:

* Primary Agent,
* Planner Agent,
* Research Agent,
* Coding Agent,
* Browser Agent,
* Communication Agent,
* Reviewer oziroma Critic Agent,
* poljubne dinamične podagente.

Prikaži možnost:

* delegiranja nalog,
* komunikacije med agenti,
* vzporednega izvajanja,
* združevanja rezultatov,
* izoliranih delovnih prostorov,
* ločenih sej in dovoljenj.

### E. Modelna plast

Vključi:

* Model Router,
* OpenAI-compatible API,
* Anthropic-compatible API,
* lokalni model prek Ollama oziroma podobnega strežnika,
* embedding model,
* speech-to-text model,
* text-to-speech model,
* fallback model,
* model selection policy.

Prikaži izbiro modela glede na:

* zahtevnost naloge,
* ceno,
* hitrost,
* zasebnost,
* zahtevana orodja,
* velikost konteksta.

### F. Orodja in integracije

Vključi:

* File System,
* Shell oziroma Process Executor,
* Browser Automation,
* HTTP Client,
* Code Execution,
* Database Tools,
* Email,
* Calendar,
* Contacts,
* Git in GitHub,
* Search API,
* MCP strežniki,
* poljubni zunanji API-ji,
* uporabniško definirani skills.

### G. Podatkovna plast

Vključi:

* konfiguracijsko podatkovno bazo,
* uporabnike in dovoljenja,
* session store,
* conversation history,
* dolgoročni spomin,
* vektorsko podatkovno bazo,
* dokumentno shrambo,
* cache,
* task queue,
* audit log,
* telemetry store,
* secret store.

### H. Operativna plast

Vključi:

* Logging,
* Metrics,
* Distributed Tracing,
* Token Usage,
* Cost Tracking,
* Error Reporting,
* Alerting,
* Admin Dashboard,
* Backup,
* Recovery.

Povezave označi z vrsto komunikacije, na primer:

* HTTPS,
* WebSocket,
* RPC,
* dogodki,
* message queue,
* SQL,
* vector search,
* tool call,
* streaming response.

---

# 2. Stran: Agent Runtime

Podrobno prikaži notranji potek delovanja enega agenta.

Vključi naslednje komponente:

* User Request,
* Input Validation,
* Authentication Context,
* Session Loading,
* Identity oziroma System Prompt,
* User Preferences,
* Workspace Context,
* Skill Loader,
* Context Builder,
* Memory Retrieval,
* Document Retrieval oziroma RAG,
* Token Budget Manager,
* Prompt Builder,
* Model Router,
* LLM Request,
* Streaming Response Parser,
* Reasoning oziroma Agent Loop,
* Planner,
* Tool Selector,
* Tool Policy Check,
* Human Approval Check,
* Tool Executor,
* Tool Result Validator,
* Observation Builder,
* Retry Manager,
* Error Handler,
* Context Pruning,
* Context Compaction,
* Response Composer,
* Output Safety Check,
* Session Persistence,
* Memory Extraction,
* Usage and Cost Tracking,
* Final Response.

Agentni cikel prikaži kot zanko:

1. prejem naloge,
2. analiza konteksta,
3. načrtovanje,
4. izbira naslednjega koraka,
5. klic modela ali orodja,
6. preverjanje rezultata,
7. posodobitev stanja,
8. odločitev, ali je naloga končana,
9. ponovitev ali priprava končnega odgovora.

Dodaj jasno označene izhode iz zanke:

* uspešno končano,
* potreben človeški odgovor,
* zavrnjeno zaradi varnostne politike,
* presežen proračun,
* presežen čas,
* neuspešno orodje,
* preklic uporabnika.

Prikaži tudi možnost ustvarjanja podagenta:

`Primary Agent → Spawn Subagent → Isolated Context → Execute Task → Return Structured Result → Merge Result`

---

# 3. Stran: Request Flow

Ustvari podroben sekvenčni oziroma podatkovni diagram za primer:

»Uporabnik prek spletnega klepeta zahteva, naj agent pregleda GitHub repozitorij, popravi napako, zažene teste in pripravi pull request.«

Vključi naslednje akterje:

* User,
* Web UI,
* Gateway,
* Authentication Service,
* Agent Router,
* Session Manager,
* Primary Agent,
* Planner Agent,
* Coding Agent,
* LLM Provider,
* GitHub Tool,
* File System,
* Sandbox,
* Test Runner,
* Policy Engine,
* Human Approval UI,
* Audit Log.

Prikaži tok:

1. uporabnik pošlje zahtevo,
2. Gateway preveri identiteto,
3. sistem naloži ali ustvari sejo,
4. Agent Router izbere agenta,
5. agent pridobi relevantni spomin,
6. Planner pripravi načrt,
7. Primary Agent ustvari Coding Agenta,
8. Coding Agent prebere repozitorij,
9. LLM predlaga spremembo,
10. agent spremeni datoteke znotraj sandboxa,
11. zažene teste,
12. ob neuspehu analizira rezultat in ponovi postopek,
13. pripravi diff,
14. Policy Engine preveri zahtevano GitHub dejanje,
15. uporabnik po potrebi potrdi objavo,
16. agent ustvari branch, commit in pull request,
17. rezultat se zabeleži v audit log,
18. seja in spomin se posodobita,
19. uporabnik prejme povezavo in povzetek.

Uporabi:

* polne puščice za sinhrone klice,
* črtkane puščice za asinhrone dogodke,
* rdeče puščice za napake ali zavrnitve,
* zelene puščice za uspešen zaključek.

---

# 4. Stran: Memory and Data

Prikaži celotno arhitekturo spomina.

Spomin razdeli na:

### Kratkoročni spomin

* trenutni prompt,
* trenutna seja,
* zgodovina pogovora,
* rezultati orodij,
* začasno stanje naloge,
* trenutni načrt,
* povzetek konteksta.

### Dolgoročni spomin

* uporabniške preference,
* profil uporabnika,
* pomembna dejstva,
* pretekle odločitve,
* projekti,
* stiki,
* naučeni postopki,
* uspešne strategije,
* zgodovina izvedenih nalog.

### Semantični oziroma RAG-spomin

* dokumenti,
* razdeljevanje dokumentov na odseke,
* ustvarjanje embeddingov,
* vector store,
* metadata filtering,
* semantic search,
* reranking,
* retrieval,
* context injection.

### Proceduralni spomin

* skills,
* sistemska navodila,
* delovni postopki,
* predloge,
* pravila uporabe orodij,
* primeri uspešnih izvedb.

Prikaži podatkovni cevovod:

`Document Source → Parser → Cleaner → Chunker → Embedding Model → Vector Database → Retriever → Reranker → Context Builder → Agent`

Prikaži tudi zapisovanje spomina:

`Conversation/Task Result → Memory Candidate Extraction → Sensitivity Check → Deduplication → User Approval, if required → Memory Store`

Označi podatke glede na občutljivost:

* javni,
* interni,
* osebni,
* zaupni,
* skrivnosti in poverilnice.

Dodaj politike:

* čas hrambe,
* brisanje podatkov,
* izvoz podatkov,
* šifriranje,
* nadzor dostopa,
* verzioniranje,
* backup,
* obnovitev.

---

# 5. Stran: Tools and Integrations

Prikaži modularni sistem orodij in vtičnikov.

Vključi:

### Tool Registry

* ime orodja,
* opis,
* JSON Schema parametrov,
* zahtevana dovoljenja,
* stopnja tveganja,
* timeout,
* retry policy,
* sandbox policy,
* način potrditve,
* output schema.

### Tool Execution Pipeline

Prikaži tok:

`Agent Tool Call → Schema Validation → Permission Check → Risk Classification → Approval Check → Sandbox Selection → Execution → Output Sanitization → Result Validation → Audit Log → Agent Observation`

### Kategorije orodij

* read-only tools,
* lokalna orodja,
* mrežna orodja,
* orodja za spremembo datotek,
* procesna oziroma shell orodja,
* komunikacijska orodja,
* finančno občutljiva orodja,
* administratorska orodja,
* destruktivna orodja.

### Integracijski sistem

Vključi:

* Plugin Manager,
* Plugin Manifest,
* Plugin SDK,
* Skill Loader,
* MCP Client,
* MCP Server,
* Webhook Adapter,
* OAuth Manager,
* API Credential Manager,
* Plugin Lifecycle,
* Plugin Health Check,
* Plugin Versioning.

Prikaži življenjski cikel vtičnika:

`Discover → Validate Manifest → Verify Permissions → Load → Initialize → Register Tools → Execute → Monitor → Disable/Unload`

---

# 6. Stran: Security Architecture

Ta stran mora biti posebej podrobna.

Uporabi model »defense in depth« in prikaži več varnostnih plasti.

### Varnostni perimetri

* Internet,
* Reverse Proxy,
* API Gateway,
* Authentication Boundary,
* Agent Runtime Boundary,
* Sandbox Boundary,
* Host OS Boundary,
* Data Boundary,
* External Services Boundary.

### Avtentikacija in avtorizacija

Vključi:

* OAuth 2.0 oziroma OIDC,
* API keys,
* session tokens,
* device pairing,
* multi-factor authentication,
* RBAC,
* ABAC,
* per-agent permissions,
* per-tool permissions,
* least privilege,
* allowlist in denylist.

### Zaščita agentnega sistema

Vključi:

* Prompt Injection Detector,
* Untrusted Input Labeling,
* Content Sanitizer,
* Tool Policy Engine,
* Data Loss Prevention,
* Secret Redaction,
* Output Validation,
* URL Allowlist,
* Domain Allowlist,
* File Path Restrictions,
* Command Allowlist,
* Network Egress Policy,
* Resource Limits,
* Timeout,
* Rate Limiting,
* Token Budget,
* Cost Budget,
* Loop Detection,
* Kill Switch.

### Sandbox

Prikaži:

* container sandbox,
* read-only filesystem,
* temporary workspace,
* CPU limit,
* memory limit,
* execution timeout,
* network disabled by default,
* omejen seznam dovoljenih domen,
* non-root user,
* seccomp oziroma sistemske omejitve,
* uničenje okolja po izvedbi.

### Človeška potrditev

Za naslednja dejanja prikaži obvezno potrjevanje:

* pošiljanje sporočil,
* brisanje datotek,
* spreminjanje produkcijskih podatkov,
* objavljanje kode,
* finančne transakcije,
* spreminjanje uporabniških računov,
* dostop do občutljivih podatkov,
* izvajanje privilegiranih ukazov.

Prikaži stopnje tveganja:

* nizko,
* srednje,
* visoko,
* kritično.

### Skrivnosti

Vključi:

* Secret Manager,
* encrypted storage,
* environment injection,
* short-lived credentials,
* credential rotation,
* scoped credentials,
* preprečevanje zapisovanja skrivnosti v loge,
* revocation.

### Revizija in odziv na incidente

Vključi:

* immutable audit log,
* tool-call history,
* model-call history,
* actor identity,
* timestamp,
* input hash,
* output hash,
* approval record,
* anomaly detection,
* security alert,
* incident response,
* session termination,
* credential revocation.

Dodaj legendiran prikaz glavnih groženj:

* prompt injection,
* posredna prompt injection,
* kraja poverilnic,
* nepooblaščen tool call,
* podatkovni eksfiltracijski napad,
* zlonamerna razširitev,
* supply-chain napad,
* neskončna agentna zanka,
* prekomerna poraba API-ja,
* eskalacija privilegijev,
* social engineering.

Vsako grožnjo poveži z ustreznimi varnostnimi kontrolami.

---

# 7. Stran: Deployment and Development

Prikaži lokalno razvojno in produkcijsko postavitev.

### Lokalno razvojno okolje

Vključi:

* Developer Workstation,
* Git Repository,
* IDE,
* Node.js oziroma Python Runtime,
* Local Gateway,
* Local Agent Runtime,
* Local Database,
* Local Vector Store,
* Ollama oziroma Local LLM,
* Docker,
* Test Sandbox,
* Mock External APIs,
* `.env` oziroma lokalni secret manager,
* Web UI Dev Server.

### Produkcijska postavitev

Vključi:

* Reverse Proxy,
* TLS,
* Gateway Service,
* Agent Worker Pool,
* Task Queue,
* Scheduler Worker,
* Tool Execution Workers,
* Sandbox Containers,
* Relational Database,
* Redis oziroma Cache,
* Vector Database,
* Object Storage,
* Secret Manager,
* Monitoring Stack,
* Backup Storage.

### Razvojni življenjski cikel

Prikaži:

`Requirements → Threat Modeling → Architecture → Prototype → Agent Evaluation → Implementation → Unit Tests → Integration Tests → Security Tests → Human Review → Deployment → Monitoring → Iteration`

### CI/CD

Vključi:

* Git Push,
* Lint,
* Type Check,
* Unit Tests,
* Integration Tests,
* Prompt Tests,
* Agent Evaluation Suite,
* Tool Mock Tests,
* Security Scan,
* Dependency Scan,
* Container Build,
* Staging Deployment,
* End-to-End Tests,
* Manual Approval,
* Production Deployment,
* Rollback.

### Testiranje agentov

Vključi:

* deterministic unit tests,
* prompt regression tests,
* golden datasets,
* tool-call evaluation,
* hallucination evaluation,
* task success rate,
* safety evaluation,
* adversarial prompt testing,
* latency benchmarks,
* token consumption,
* cost per task,
* human evaluation.

### Okolja

Prikaži:

* Development,
* Testing,
* Staging,
* Production.

Med okolji označi:

* različne poverilnice,
* različne podatkovne baze,
* ločene agente,
* ločene limite,
* ločene dnevnike,
* prepoved uporabe produkcijskih podatkov v razvoju.

---

# Vizualne zahteve

Uporabi profesionalen, sodoben in tehničen slog.

## Barve

Uporabi dosledno barvno shemo:

* modra: Gateway, API in komunikacija,
* vijolična: agenti in agentni runtime,
* zelena: modeli in uspešni procesi,
* oranžna: orodja in zunanje integracije,
* rumena: spomin in podatkovne shrambe,
* rdeča: varnost, napake in visoko tveganje,
* siva: infrastruktura in podporne komponente.

## Oblike

Uporabi:

* zaobljene pravokotnike za storitve,
* cilindre za podatkovne baze,
* oblake za zunanje ponudnike,
* šestkotnike za agente,
* pravokotnike z dvojno obrobo za varnostne komponente,
* dokumentne oblike za promte, skills in konfiguracije,
* skupine oziroma containers za arhitekturne plasti.

## Povezave

Vse povezave naj imajo:

* smer puščice,
* opis komunikacije,
* čim manj križanj,
* ortogonalne oziroma lomljene povezave,
* jasen prikaz sinhrone ali asinhrone komunikacije.

Uporabi različne vrste črt:

* polna črta: sinhroni klic,
* črtkana črta: asinhroni dogodek,
* debela črta: glavni podatkovni tok,
* rdeča črta: zavrnitev ali napaka,
* zelena črta: uspešen zaključek,
* dvojna črta: zaupna oziroma šifrirana povezava.

## Organizacija

* Elementi se ne smejo prekrivati.
* Besedilo mora biti berljivo pri običajni povečavi.
* Vsaka stran mora imeti naslov.
* Vsaka stran mora imeti legendo.
* Vsaka stran mora imeti kratko polje »Namen diagrama«.
* Komponente naj bodo poravnane na mrežo.
* Sorodne komponente združi v vizualne skupine.
* Diagram naj bo dovolj velik in podroben, ne pa nepregleden.
* Uporabi najmanj 1920 × 1080 delovne površine na stran.
* Imena komponent naj bodo v angleščini.
* Opombe, razlage in legende naj bodo v slovenščini.

---

# Tehnične zahteve za draw.io XML

* Ustvari veljaven XML dokument formata diagrams.net.
* Dokument mora uporabljati korenski element `<mxfile>`.
* Vsaka zahtevana stran mora biti ločen `<diagram>` element.
* Vsak diagram mora vsebovati veljaven `<mxGraphModel>`.
* Vsi elementi morajo imeti unikatne ID-je.
* Geometrija mora biti zapisana z elementi `<mxGeometry>`.
* Povezave morajo uporabljati pravilna atributa `source` in `target`.
* Besedilo mora biti pravilno XML-escaped.
* Datoteka se mora odpreti brez napake v diagrams.net.
* Ne vstavljaj Markdown ograj okoli XML-vsebine v končno datoteko.
* Ne uporabljaj neveljavnih ali izmišljenih draw.io elementov.
* Uporabi standardne `mxCell` stile, ki jih diagrams.net podpira.
* Diagram naj ostane popolnoma urejevalen.
* Ne pretvarjaj celotnega diagrama v eno samo sliko.
* Ne vstavljaj zunanjih slik, ki bi za prikaz zahtevale internetno povezavo.

Kjer je smiselno, uporabi draw.io layers, na primer:

* Background,
* Components,
* Connections,
* Security,
* Labels,
* Notes.

---

# Postopek izvedbe

Izvedi naslednje korake:

1. Preglej uradno arhitekturo OpenClaw in druge relevantne vire o produkcijskih AI-agentih.
2. Oblikuj generično arhitekturo, ki ni vezana samo na enega ponudnika modelov.
3. Pripravi seznam vseh strani, komponent in povezav.
4. Generiraj celotno draw.io XML-datoteko.
5. Shrani jo kot `ai-agent-architecture.drawio`.
6. Programsko preveri, da je XML sintaktično veljaven.
7. Preveri:

   * da obstaja vseh sedem strani,
   * da imajo vsi elementi unikatne ID-je,
   * da vse povezave kažejo na obstoječe elemente,
   * da nobena stran ni prazna.
8. Če je mogoče, datoteko odpri ali pretvori v predogled, da preveriš postavitev.
9. Odpravi prekrivanja, odrezano besedilo in nelogične povezave.
10. Poleg `.drawio` datoteke ustvari še:

    * `ai-agent-architecture-overview.md`,
    * `ai-agent-component-catalog.md`.

Datoteka `ai-agent-architecture-overview.md` naj razloži:

* namen posamezne strani,
* glavne arhitekturne odločitve,
* glavni tok zahtev,
* varnostni model,
* način lokalnega zagona,
* možne tehnologije za implementacijo.

Datoteka `ai-agent-component-catalog.md` naj za vsako komponento vsebuje:

* ime,
* odgovornost,
* vhod,
* izhod,
* odvisnosti,
* podatke, ki jih obdeluje,
* zahtevana dovoljenja,
* ključna tveganja,
* predlagane tehnologije.

---

# Zahtevani končni odgovor

Ne zaključi samo z načrtom ali razlago.

Dejansko ustvari zahtevane datoteke in na koncu navedi:

1. katere datoteke si ustvaril,
2. absolutno ali relativno lokacijo datotek,
3. število strani v draw.io dokumentu,
4. število vozlišč in povezav na posamezni strani,
5. kako odpreti `.drawio` datoteko,
6. katere validacije si izvedel,
7. morebitne omejitve diagrama.

Najpomembnejši končni rezultat je veljavna datoteka:

`ai-agent-architecture.drawio`

Diagram mora biti dovolj podroben, da ga je mogoče uporabiti kot začetno tehnično specifikacijo za dejanski razvoj produkcijskega, lokalno gostovanega AI-agenta.
