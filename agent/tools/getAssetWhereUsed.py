from pathlib import Path
import pathlib
import ssl
import logging
import httpx

from agent.tools.tools_models import Tool, ToolResult


logger = logging.getLogger("uvicorn")


# Funkcija za nalaganje SSL certifikatov

ZPIZ_PEMS = [
    "/app/certs/ZPIZCA.pem",
    "/app/certs/ZPIZCA2.pem",
    "/app/certs/ZPIZSUB.pem",
    "/app/certs/ZPIZSUB2.pem",
]


def make_ctx_from_pems(paths=ZPIZ_PEMS) -> ssl.SSLContext:
    try:
        logger.info("Nalaganje certifikatov ...")

        cadata = "\n".join(
            pathlib.Path(p).read_text()
            for p in paths
        )

        ctx = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH
        )

        ctx.load_verify_locations(
            cadata=cadata
        )

        logger.info("Nalaganje certifikatov ok")

        return ctx

    except Exception:
        logger.exception(
            "NAPAKA pri nalaganju certifikatov"
        )
        raise


def getAssetWhereUsed_executor(
    workspace: Path,
    poId: str,
) -> ToolResult:

    url = (
        "https://RVLBPCDS1.zpiz.si:9444/"
        "automationservices/rest/BAWOROD/BAW/getAssetWhereUsed"
    )

    username = "Z66176"
    password = "JonTestnoOkolje123"
    timeout = 30

    payload = {
        "poId": poId
    }

    try:
        ctx = make_ctx_from_pems()

        with httpx.Client(
            verify=ctx,
            auth=httpx.BasicAuth(
                username,
                password,
            ),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        ) as client:

            response = client.post(
                url,
                json=payload,
            )

        output = response.text or None
        ok = response.is_success

        return ToolResult(
            ok=ok,
            output=output,
            error=(
                None
                if ok
                else (
                    f"HTTP {response.status_code}: "
                    f"{response.reason_phrase}"
                )
            ),
            metadata={
                "url": url,
                "method": "POST",
                "status_code": response.status_code,
                "reason": response.reason_phrase,
            },
        )

    except httpx.TimeoutException as e:
        logger.exception(
            "Timeout pri klicu getAssetWhereUsed"
        )

        return ToolResult(
            ok=False,
            error=f"Request timed out: {e}",
            metadata={
                "url": url,
                "method": "POST",
            },
        )

    except httpx.ConnectError as e:
        logger.exception(
            "Connection error pri klicu getAssetWhereUsed"
        )

        return ToolResult(
            ok=False,
            error=f"Connection error: {e}",
            metadata={
                "url": url,
                "method": "POST",
            },
        )

    except httpx.HTTPError as e:
        logger.exception(
            "HTTP napaka pri klicu getAssetWhereUsed"
        )

        return ToolResult(
            ok=False,
            error=f"HTTP request failed: {e}",
            metadata={
                "url": url,
                "method": "POST",
            },
        )

    except Exception as e:
        logger.exception(
            "Napaka pri izvajanju getAssetWhereUsed"
        )

        return ToolResult(
            ok=False,
            error=str(e),
            metadata={
                "url": url,
                "method": "POST",
            },
        )


GET_ASSET_WHERE_USED_TOOL = Tool(
    name="getAssetWhereUsed",
    description="""
Identifikator artefakta, katerega uporabo iščemo, v obliki
"64.668b9e9e-b7c7-4d20-9cc1-2c6ced808a0b" – številčna predpona tipa,
pika in UUID.

Vrednost prepiši DOBESEDNO iz polja "poId" edinega zadetka v polju
"results" prejšnjega klica orodja najdiAsset. Ne spreminjaj velikih in
malih črk, ne odstranjuj številčne predpone pred piko, ne dodajaj presledkov
ali narekovajev, ne skrajšuj UUID-ja.

Pošlji samo takrat, ko je imel prejšnji klic najdiAsset status "OK" in
natanko en zadetek. Če zadetkov ni bilo ali jih je bilo več, tega
identifikatorja nimaš in orodja ne smeš klicati.

Ne pošiljaj imena artefakta, taga, tipa ali celotnega uporabnikovega
vprašanja – ta parameter sprejme izključno poId.

Vrne seznam artefaktov, ki uporabljajo (referencirajo) podani artefakt
toolkita UDG Toolkit 2. Odgovarja na vprašanja tipa:
- "kje se to uporablja"
- "kdo to kliče"
- "kaj se podre, če to spremenim"
- "ali se še uporablja"
- "katere storitve uporabljajo ta business object"

Orodje sprejme izključno poId, ne imena. Zato ga NIKOLI ne kliči kot prvo
orodje.

Postopek je vedno dvostopenjski:

1. najprej pokliči najdiAsset, da dobiš artefakt
2. poglej odgovor: šele če ima status "OK" in "totalMatches" enak 1,
   vzemi poId edinega zadetka iz "results" in ga pošlji temu orodju

Tega orodja NE kliči, kadar:
- najdiAsset je vrnil status TOO_MANY ali NO_MATCH
- najdiAsset je vrnil več kot en zadetek
  (totalMatches je večji od 1 ali je polje "ambiguous" true);
  v tem primeru najprej uporabniku naštej najdene artefakte in ga vprašaj,
  za katerega ga zanima uporaba; šele po njegovem odgovoru pokliči to orodje
- uporabnik je poId navedel sam in ga še nisi preveril z najdiAsset

poId nikoli ne sestavljaj, ne ugibaj in ne prepisuj iz spomina ali iz
prejšnjih delov pogovora – vedno ga vzemi iz zadnjega odgovora orodja
najdiAsset.

Pri odgovoru uporabniku vedno povej, za kateri artefakt so rezultati
(ime in tip iz koraka 1), ne samo poId.

Če orodje vrne prazen seznam, to pomeni, da artefakt v tem snapshotu ni
nikjer uporabljen – to povej kot ugotovitev, ne kot napako.
    """,
    parameters={
        "type": "object",
        "properties": {
            "poId": {
                "type": "string",
                "description": (
                    "Identifikator artefakta, katerega uporabo iščemo, "
                    "v obliki "
                    "64.668b9e9e-b7c7-4d20-9cc1-2c6ced808a0b – "
                    "številčna predpona tipa, pika in UUID."
                ),
            },
        },
        "required": ["poId"],
        "additionalProperties": False,
    },
    executor=getAssetWhereUsed_executor,
)