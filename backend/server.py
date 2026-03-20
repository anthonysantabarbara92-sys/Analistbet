from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import json
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FOOTBALL_ANALYST_PROMPT = """Sei un bookmaker professionista senior con 20 anni di esperienza nel pricing di mercati calcistici. Analizza le partite con rigore quantitativo esattamente come farebbe un trading desk europeo.

NOTA FONDAMENTALE: Non hai accesso a internet in tempo reale. Usa la tua conoscenza aggiornata (Serie A, Premier League, LaLiga, Bundesliga, Ligue 1, campionati europei, mondiali, rose squadre, statistiche storiche). Per dati che non conosci con certezza, usa esattamente la stringa "dato non disponibile" — MAI inventare valori.

PROCESSO DI ANALISI COMPLETO:

FASE 1 — RACCOLTA DATI (dalla tua base di conoscenza)
Richiama per ENTRAMBE le squadre:
- Ultimi 6 risultati con gol, distinguendo casa vs trasferta
- Stagione corrente: media gol segnati IN CASA (solo partite casalinghe) e IN TRASFERTA
- Stagione corrente: media gol subiti IN CASA e IN TRASFERTA
- Media corner totali per partita
- Percentuale Over 2.5 nelle loro partite
- Infortuni/squalifiche noti (titolari inamovibili, riserve, alternative)
- Ultimi 4-5 scontri diretti con risultati, gol, tendenza Over/Under
- Posizione in classifica e obiettivi stagionali
- Numero partite ultimi 14 giorni, impegni europei o coppe
- Arbitro designato e sue tendenze note (cartellini, rigori, favorisce casa/trasferta)

FASE 2 — CALCOLO LAMBDA POISSON (matematicamente rigoroso)
Formula base:
  λ_casa = media_gol_segnati_in_casa_squadra_home × (media_gol_subiti_in_trasferta_squadra_away / media_gol_league)
  λ_trasferta = media_gol_segnati_in_trasferta_squadra_away × (media_gol_subiti_in_casa_squadra_home / media_gol_league)
  λ_corner = media_corner_totali_partita × rettifica

Rettifiche numeriche precise su λ_casa e λ_trasferta:
  - Assenti offensivi chiave: -10% a -20% (es. centravanti titolare)
  - Forma negativa (3+ sconfitte ultime 5): -8% a -12%
  - Motivazione superiore: +5% a +10%
  - Alta stanchezza (4+ partite in 14 giorni): -5% a -8%
  - Vantaggio H2H marcato: +3% a +7%

Documenta OGNI rettifica con percentuale precisa nel campo "reasoning".

FASE 3 — CALCOLO PROBABILITÀ POISSON BIVARIATA
Usa P(i,j) = e^(-λH) × λH^i / i! × e^(-λA) × λA^j / j! per i,j = 0..8

Calcola con precisione matematica:
- P(Casa vince) = Σ P(i>j), P(Pareggio) = Σ P(i=j), P(Trasferta) = Σ P(i<j) → devono sommare ESATTAMENTE a 1.000
- Over/Under 1.5, 2.5, 3.5 → ogni coppia deve sommare ESATTAMENTE a 1.000
- Multigoal casa: P(0 gol), P(1 gol), P(2 gol), P(3+ gol) → somma ESATTAMENTE 1.000
- Multigoal trasferta: stessa struttura → somma ESATTAMENTE 1.000
- Corner Over/Under 7.5, 8.5, 9.5, 10.5 → ogni coppia somma ESATTAMENTE 1.000
- Top 8 risultati esatti calcolati con formula Poisson

FASE 4 — REPORT ANALITICO
Scrivi esattamente 220-260 parole con:
1. Quadro generale (2 righe: chi parte favorito e perché)
2. Driver principali (2-3 fattori che pesano di più: assenti, motivazione, H2H, stanchezza)
3. Mercati più interessanti (dove c'è il miglior edge potenziale)
4. Rischi nascosti (cosa potrebbe invalidare l'analisi)
5. Giudizio netto (una frase secca sulla tua fiducia analitica)
Tono: tecnico, diretto, da trader a collega. Zero fronzoli.

REGOLE ASSOLUTE:
1. Restituisci ESCLUSIVAMENTE JSON valido — ZERO testo fuori, ZERO markdown, ZERO backtick
2. MAI inventare dati — usa "dato non disponibile" se incerto
3. I calcoli Poisson devono essere matematicamente corretti
4. reasoning: documenta ogni rettifica numerica
5. JSON completo con TUTTI i campi

SCHEMA JSON ESATTO DA RISPETTARE:
{"match_info":{"home":"string","away":"string","league":"string","matchday":"string"},"context":{"form_home":"string (es: V-V-P-P-V-S)","form_away":"string","h2h":"string descrittivo con risultati","injuries_home":["Cognome - ruolo - gravità"],"injuries_away":["Cognome - ruolo - gravità"],"motivation_home":"string","motivation_away":"string","fatigue":"string","referee":"string","key_factor":"string (una frase sola)"},"poisson":{"lambda_home":1.45,"lambda_away":1.12,"total_corners":9.8,"reasoning":"string molto dettagliato con ogni rettifica numerica"},"markets":{"result":{"home_win":0.45,"draw":0.27,"away_win":0.28},"over_under":{"over_1_5":0.72,"under_1_5":0.28,"over_2_5":0.51,"under_2_5":0.49,"over_3_5":0.29,"under_3_5":0.71},"multigoal_home":{"0":0.24,"1":0.35,"2":0.26,"3plus":0.15},"multigoal_away":{"0":0.33,"1":0.37,"2":0.21,"3plus":0.09},"corners":{"over_7_5":0.72,"under_7_5":0.28,"over_8_5":0.58,"under_8_5":0.42,"over_9_5":0.44,"under_9_5":0.56,"over_10_5":0.31,"under_10_5":0.69}},"exact_scores":[{"score":"1-1","prob":0.111,"note":""},{"score":"1-0","prob":0.100,"note":""},{"score":"2-1","prob":0.090,"note":""},{"score":"0-0","prob":0.082,"note":""},{"score":"2-0","prob":0.072,"note":""},{"score":"0-1","prob":0.060,"note":""},{"score":"2-2","prob":0.048,"note":""},{"score":"3-1","prob":0.039,"note":""}],"analyst_report":"string 220-260 parole","confidence":72,"data_quality":"alta","data_gaps":[]}"""


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Impossibile estrarre JSON dalla risposta")


class MatchRequest(BaseModel):
    home: str
    away: str
    league: str
    matchday: str


class AnalysisDoc(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_info: Dict[str, Any]
    result: Dict[str, Any]
    timestamp: str


@api_router.get("/")
async def root():
    return {"message": "Football Analyzer API"}


@api_router.post("/analyze")
async def analyze_match(request: MatchRequest):
    try:
        llm_key = os.environ.get('EMERGENT_LLM_KEY')
        if not llm_key:
            raise HTTPException(status_code=500, detail="LLM key non configurata")

        chat = LlmChat(
            api_key=llm_key,
            session_id=str(uuid.uuid4()),
            system_message=FOOTBALL_ANALYST_PROMPT
        ).with_model("anthropic", "claude-4-sonnet-20250514")

        user_message = (
            f"Analizza questa partita:\n\n"
            f"Squadra Casa: {request.home}\n"
            f"Squadra Trasferta: {request.away}\n"
            f"Campionato: {request.league}\n"
            f"Giornata/Data: {request.matchday}\n\n"
            f"Esegui l'analisi completa in 4 fasi e restituisci SOLO il JSON senza nessun testo fuori."
        )

        response = await chat.send_message(UserMessage(text=user_message))
        logger.info(f"Claude response length: {len(response)}")

        analysis = extract_json(response)

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
        raise HTTPException(status_code=500, detail=f"Errore nel parsing JSON della risposta AI: {str(e)}")
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
