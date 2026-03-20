from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import asyncio
import logging
import re
import json
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Dict
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
from ddgs import DDGS

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ── System Prompt ─────────────────────────────────────────────────────────────
FOOTBALL_ANALYST_PROMPT = """Sei un bookmaker professionista senior con 20 anni di esperienza nel pricing di mercati calcistici. Analizza le partite con rigore quantitativo esattamente come farebbe un trading desk europeo.

FONTE DATI: Nella richiesta dell'utente troverai dati aggiornati raccolti da ricerche web in tempo reale. USA QUESTI DATI COME FONTE PRIMARIA. Solo dove mancano dati specifici, integra con la tua base di conoscenza. Se un dato non è disponibile né nelle ricerche né nella tua conoscenza, usa "dato non disponibile" — MAI inventare.

PROCESSO DI ANALISI COMPLETO:

FASE 1 — RACCOLTA DATI
Estrai dai dati web forniti (e integra con tua conoscenza dove necessario):
- Ultimi 6 risultati con gol, distinguendo casa vs trasferta
- Stagione corrente: media gol segnati IN CASA e IN TRASFERTA (separati)
- Stagione corrente: media gol subiti IN CASA e IN TRASFERTA
- Media corner totali per partita, % Over 2.5
- Infortuni/squalifiche AGGIORNATI (titolari inamovibili vs riserve)
- Ultimi 4-5 scontri diretti con risultati, gol, tendenza Over/Under
- Posizione in classifica e obiettivi stagionali
- Partite negli ultimi 14 giorni, impegni europei o coppe
- Arbitro designato e tendenze note

FASE 2 — CALCOLO LAMBDA POISSON (matematicamente rigoroso)
Formula base:
  λ_casa = media_gol_segnati_in_casa_home × (media_gol_subiti_in_trasferta_away / media_gol_league)
  λ_trasferta = media_gol_segnati_in_trasferta_away × (media_gol_subiti_in_casa_home / media_gol_league)
  λ_corner = media_corner_totali × rettifica_stile

Rettifiche numeriche precise:
  - Assenti offensivi chiave: -10% a -20%
  - Forma negativa (3+ sconfitte ultime 5): -8% a -12%
  - Motivazione superiore: +5% a +10%
  - Alta stanchezza (4+ partite in 14 giorni): -5% a -8%
  - Vantaggio H2H marcato: +3% a +7%

Documenta OGNI rettifica con percentuale precisa nel campo "reasoning".

FASE 3 — CALCOLO PROBABILITÀ POISSON BIVARIATA
P(i,j) = e^(-λH) × λH^i / i! × e^(-λA) × λA^j / j! per i,j = 0..8

Verifica matematica obbligatoria:
- P(Casa) + P(Pareggio) + P(Trasferta) = 1.000 esatto
- Over + Under = 1.000 per ogni linea
- Multigoal home: somma = 1.000
- Multigoal away: somma = 1.000
- Corner Over + Under = 1.000 per ogni linea

FASE 4 — REPORT ANALITICO
220-260 parole: quadro generale, driver principali, mercati interessanti, rischi nascosti, giudizio netto.
Tono: tecnico, diretto, da trader a collega. Zero fronzoli.

REGOLE ASSOLUTE:
1. Restituisci ESCLUSIVAMENTE JSON valido — ZERO testo fuori, ZERO markdown, ZERO backtick
2. MAI inventare dati — "dato non disponibile" per dati incerti
3. Calcoli Poisson matematicamente corretti
4. Documenta ogni rettifica nel reasoning
5. JSON completo con TUTTI i campi

SCHEMA JSON ESATTO:
{"match_info":{"home":"string","away":"string","league":"string","matchday":"string"},"context":{"form_home":"string (es: V-V-P-P-V-S)","form_away":"string","h2h":"string con risultati","injuries_home":["Cognome - ruolo - gravità"],"injuries_away":["Cognome - ruolo - gravità"],"motivation_home":"string","motivation_away":"string","fatigue":"string","referee":"string","key_factor":"string (una frase)"},"poisson":{"lambda_home":1.45,"lambda_away":1.12,"total_corners":9.8,"reasoning":"string dettagliato con ogni rettifica numerica"},"markets":{"result":{"home_win":0.45,"draw":0.27,"away_win":0.28},"over_under":{"over_1_5":0.72,"under_1_5":0.28,"over_2_5":0.51,"under_2_5":0.49,"over_3_5":0.29,"under_3_5":0.71},"multigoal_home":{"0":0.24,"1":0.35,"2":0.26,"3plus":0.15},"multigoal_away":{"0":0.33,"1":0.37,"2":0.21,"3plus":0.09},"corners":{"over_7_5":0.72,"under_7_5":0.28,"over_8_5":0.58,"under_8_5":0.42,"over_9_5":0.44,"under_9_5":0.56,"over_10_5":0.31,"under_10_5":0.69}},"exact_scores":[{"score":"1-1","prob":0.111,"note":""},{"score":"1-0","prob":0.100,"note":""},{"score":"2-1","prob":0.090,"note":""},{"score":"0-0","prob":0.082,"note":""},{"score":"2-0","prob":0.072,"note":""},{"score":"0-1","prob":0.060,"note":""},{"score":"2-2","prob":0.048,"note":""},{"score":"3-1","prob":0.039,"note":""}],"analyst_report":"string 220-260 parole","confidence":72,"data_quality":"alta","data_gaps":[]}"""


# ── Web Search ────────────────────────────────────────────────────────────────
def _ddg_search(query: str, max_results: int) -> list:
    """Synchronous DuckDuckGo search (runs in thread pool)."""
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        logger.warning(f"DDG error for '{query}': {e}")
        return []


async def search_query(query: str, max_results: int = 3) -> list:
    """Async wrapper for DDG search with timeout."""
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: _ddg_search(query, max_results)),
            timeout=8.0
        )
    except asyncio.TimeoutError:
        logger.warning(f"Timeout searching: {query}")
        return []


async def gather_football_data(home: str, away: str, league: str, matchday: str) -> tuple:
    """Gather current football data via web search. Returns (data_str, queries_found)."""
    month_year = datetime.now().strftime("%B %Y")

    queries = [
        f"{home} risultati partite {league} {month_year}",
        f"{away} risultati partite {league} {month_year}",
        f"{home} infortuni assenti squalificati {month_year}",
        f"{away} infortuni assenti squalificati {month_year}",
        f"{home} {away} precedenti scontri diretti testa a testa",
        f"classifica {league} stagione 2024 2025",
        f"{home} statistiche gol {league} 2024-25",
        f"{away} statistiche gol {league} 2024-25",
    ]

    lines = []
    found = 0

    for query in queries:
        results = await search_query(query, max_results=3)
        if results:
            found += 1
            lines.append(f"\n[RICERCA: {query}]")
            for r in results[:3]:
                body = (r.get('body') or '')[:400].strip()
                title = (r.get('title') or '').strip()
                if body:
                    lines.append(f"  • {title}: {body}")
        await asyncio.sleep(0.2)

    if lines:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        header = f"=== DATI AGGIORNATI DA RICERCA WEB ({now}) — {found}/8 query completate ===\n"
        return header + "\n".join(lines), found
    return "", 0


# ── Math normalization ────────────────────────────────────────────────────────
def normalize_markets(analysis: dict) -> dict:
    """Ensure all probability distributions sum exactly to 1.0."""
    markets = analysis.get('markets', {})
    if not markets:
        return analysis

    def norm_pair(d, k1, k2):
        s = d.get(k1, 0) + d.get(k2, 0)
        if s > 0 and abs(s - 1.0) > 0.004:
            d[k1] = round(d.get(k1, 0) / s, 4)
            d[k2] = round(d.get(k2, 0) / s, 4)

    def norm_group(d, keys):
        s = sum(d.get(k, 0) for k in keys)
        if s > 0 and abs(s - 1.0) > 0.004:
            for k in keys:
                if k in d:
                    d[k] = round(d[k] / s, 4)

    r = markets.get('result', {})
    norm_group(r, ['home_win', 'draw', 'away_win'])

    ou = markets.get('over_under', {})
    for t in ['1_5', '2_5', '3_5']:
        norm_pair(ou, f'over_{t}', f'under_{t}')

    for side in ['multigoal_home', 'multigoal_away']:
        norm_group(markets.get(side, {}), ['0', '1', '2', '3plus'])

    c = markets.get('corners', {})
    for t in ['7_5', '8_5', '9_5', '10_5']:
        norm_pair(c, f'over_{t}', f'under_{t}')

    return analysis


# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_json(text: str) -> dict:
    text = text.strip()
    for prefix in ["```json", "```"]:
        if text.startswith(prefix):
            text = text[len(prefix):]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise ValueError("Impossibile estrarre JSON dalla risposta AI")


# ── Models ────────────────────────────────────────────────────────────────────
class MatchRequest(BaseModel):
    home: str
    away: str
    league: str
    matchday: str


# ── Routes ────────────────────────────────────────────────────────────────────
@api_router.get("/")
async def root():
    return {"message": "Football Analyzer API v2 — Web Search Enabled"}


@api_router.post("/analyze")
async def analyze_match(request: MatchRequest):
    try:
        llm_key = os.environ.get('EMERGENT_LLM_KEY')
        if not llm_key:
            raise HTTPException(status_code=500, detail="LLM key non configurata")

        # STEP 1 — Web search for current data
        logger.info(f"Web search: {request.home} vs {request.away} [{request.league}]")
        web_data, queries_found = await gather_football_data(
            request.home, request.away, request.league, request.matchday
        )
        logger.info(f"Search complete: {queries_found}/8 queries returned results")

        # STEP 2 — Build prompt with web context
        web_section = ""
        if web_data:
            web_section = (
                f"\n\n{web_data}\n\n"
                f"=== ISTRUZIONI SUI DATI WEB ===\n"
                f"- Usa i dati web sopra come fonte PRIMARIA e PRIORITARIA\n"
                f"- Questi dati sono stati recuperati oggi: sono più aggiornati della tua base di conoscenza\n"
                f"- Se i dati web contraddicono la tua conoscenza, DAI PRECEDENZA ai dati web\n"
                f"- Estrai: forma recente, infortuni, statistiche gol, H2H, classifica\n"
                f"- Per dati mancanti, usa la tua conoscenza e segnala in data_gaps\n"
            )

        user_message = (
            f"Analizza questa partita:\n\n"
            f"Squadra Casa: {request.home}\n"
            f"Squadra Trasferta: {request.away}\n"
            f"Campionato: {request.league}\n"
            f"Giornata/Data: {request.matchday}"
            f"{web_section}\n\n"
            f"Esegui l'analisi completa in 4 fasi. Restituisci SOLO il JSON, nessun testo fuori."
        )

        # STEP 3 — Claude analysis
        chat = LlmChat(
            api_key=llm_key,
            session_id=str(uuid.uuid4()),
            system_message=FOOTBALL_ANALYST_PROMPT
        ).with_model("anthropic", "claude-4-sonnet-20250514")

        response = await chat.send_message(UserMessage(text=user_message))
        logger.info(f"Claude response: {len(response)} chars")

        # STEP 4 — Parse, normalize, save
        analysis = extract_json(response)
        analysis = normalize_markets(analysis)
        analysis['web_search_used'] = queries_found > 0
        analysis['web_queries_found'] = queries_found

        doc = {
            "id": str(uuid.uuid4()),
            "match_info": request.model_dump(),
            "result": analysis,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.football_analyses.insert_one(doc)

        return analysis

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Errore parsing JSON risposta AI: {str(e)}")
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/analyses")
async def get_analyses():
    try:
        items = await db.football_analyses.find({}, {"_id": 0}).sort("timestamp", -1).to_list(20)
        return items
    except Exception as e:
        logger.error(f"History error: {e}")
        return []


# ── App setup ─────────────────────────────────────────────────────────────────
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
