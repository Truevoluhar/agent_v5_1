from pathlib import Path
import pathlib
import ssl
import logging
import httpx

from agent.tools.tools_models import Tool, ToolResult

logger = logging.getLogger("uvicorn")


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

        ctx.load_verify_locations(cadata=cadata)

        logger.info("Nalaganje certifikatov OK")
        return ctx

    except Exception:
        logger.exception("NAPAKA pri nalaganju certifikatov")
        raise


def najdiAsset_executor(
    workspace: Path,
    najdiAsset: str,
    assetTip: str = "",
) -> ToolResult:

    url = (
        "https://RVLBPCDS1.zpiz.si:9444/"
        "automationservices/rest/BAWOROD/BAW/findAssets"
    )

    username = "Z66176"
    password = "JonTestnoOkolje123"
    timeout = 30

    payload = {
        "najdiAsset": najdiAsset,
        "assetTip": assetTip,
    }

    try:
        ctx = make_ctx_from_pems()

        with httpx.Client(
            verify=ctx,
            auth=httpx.BasicAuth(username, password),
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
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
                else f"HTTP {response.status_code}: "
                     f"{response.reason_phrase}"
            ),
            metadata={
                "url": url,
                "method": "POST",
                "status_code": response.status_code,
                "reason": response.reason_phrase,
            },
        )

    except httpx.TimeoutException as e:
        return ToolResult(
            ok=False,
            error=f"Request timed out: {e}",
            metadata={
                "url": url,
                "method": "POST",
            },
        )

    except httpx.ConnectError as e:
        return ToolResult(
            ok=False,
            error=f"Connection error: {e}",
            metadata={
                "url": url,
                "method": "POST",
            },
        )

    except httpx.HTTPError as e:
        return ToolResult(
            ok=False,
            error=f"HTTP request failed: {e}",
            metadata={
                "url": url,
                "method": "POST",
            },
        )

    except Exception as e:
        logger.exception("Napaka pri izvajanju najdiAsset")

        return ToolResult(
            ok=False,
            error=str(e),
            metadata={
                "url": url,
                "method": "POST",
            },
        )
        
NAJDI_ASSET_TOOL = Tool(
    name="najdiAsset",
    description="""
    Iskanje po katalogu artefaktov IBM BAW toolkita UDG Toolkit 2 (UDGTLK2).
Katalog obsega 2982 elementov: service flowe, client-side human service,
coach viewe, business objecte, EPV-je, external service, web in server file.
Uporabi to orodje vedno, kadar uporabnik sprašuje, ali nek artefakt obstaja,
kako se točno imenuje, kakšnega tipa je, s katerimi tagi je označen, kdo ga
je nazadnje spreminjal in kdaj.
Parametra:
- najdiAsset (obvezen): del imena artefakta
- assetTip (neobvezen): omejitev na en tip artefakta
Prvi klic naredi vedno samo z najdiAsset, brez assetTip.
Odgovor vsebuje polje "status". Ravnaj se po njem:
- status "TOO_MANY": zadetkov je preveč in polje "results" je prazno.
  Polje "byType" vsebuje razrez po tipih, polje "limit" pa največje
  dovoljeno število zadetkov. Poglej, ali je v "byType" kateri tip s
  številom, manjšim od "limit":
    * če tak tip obstaja in ustreza temu, kar uporabnik išče, naredi še
      en klic z istim najdiAsset in tem tipom v assetTip
    * če je takih tipov več in iz vprašanja ni jasno, kateri je pravi,
      orodja ne kliči znova, ampak uporabniku pokaži razrez iz "byType"
      in ga vprašaj, kateri tip ga zanima
    * če noben tip nima manj zadetkov od "limit", orodja ne kliči znova.
      Sporoči število zadetkov (totalMatches), pokaži razrez po tipih in
      prosi uporabnika, naj doda še eno besedo iz imena.
  Nikoli si ne izmišljuj zadetkov, ko je "results" prazen.
- prazen seznam zadetkov: enkrat lahko poskusiš s krajšim ali splošnejšim
  delom imena. Če tudi drugi klic nič ne vrne, odgovori, da artefakta v
  katalogu ni.
- sicer: odgovori na podlagi vrnjenih zadetkov.
Za eno uporabnikovo vprašanje naredi največ dva klica tega orodja.
Nikoli ne ugibaj imen artefaktov iz lastnega znanja in nikoli ne trdi, da
nekaj ne obstaja, brez klica orodja.
    """,
    parameters={
        "type": "object",
        "properties": {
            "najdiAsset": { "type": "string", "description": "Del imena artefakta"},
            "assetTip": { "type": "string", "default": "", "description": "Omejitev na en tip artefakta"},
        },
        "required": ["najdiAsset", "assetTip"],
        "additionalProperties": False
    },
    executor=najdiAsset_executor
)