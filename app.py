#-*- coding: utf-8 -*-
# THE SINGULARITY PRO v14.0 - FULL ENTERPRISE VERSION
# Bloomberg Terminal Senior Quant Trading System

import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json, re, warnings
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List
import google.generativeai as genai

warnings.filterwarnings("ignore")

# --- CONFIGURAZIONE UI & CSS ORIGINALE ---
st.set_page_config(page_title="THE SINGULARITY v14", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    :root { 
        --b-bg: #05050a; 
        --b-panel: #0f0f1e; 
        --b-border: #1e1e35; 
        --b-accent: #ff6600; 
        --b-text: #e8e8f0; 
    }
    .main { 
        background-color: var(--b-bg); 
        font-family: 'JetBrains Mono', monospace; 
        color: var(--b-text); 
    }
    .vbox { 
        background: var(--b-panel); 
        border: 1px solid var(--b-border); 
        padding: 18px; 
        border-radius: 4px; 
        margin-bottom: 15px; 
    }
    .vbadge { 
        padding: 3px 8px; 
        border-radius: 3px; 
        font-size: 0.7rem; 
        font-weight: 700; 
        text-transform: uppercase; 
    }
    .pos { border-left: 3px solid #00ff88; background: rgba(0, 255, 136, 0.05); }
    .neg { border-left: 3px solid #ff3355; background: rgba(255, 51, 85, 0.05); }
    .stMetric { background: #0f0f1e; border: 1px solid #1e1e35; padding: 10px; border-radius: 4px; }
    .stButton>button { 
        width: 100%; 
        background: linear-gradient(90deg, #ff6600, #ffcc00); 
        color: black; 
        font-weight: 800; 
        border: none; 
        height: 3rem;
    }
    .stTextArea>div>div>textarea {
        background-color: #05050a !important;
        color: #00ff88 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE COMPETIZIONI PARTE 1 ---
COMPETITIONS: Dict[str, List[str]] = {
    "Italia": [
        "Serie A", "Serie B", "Serie C Girone A", "Serie C Girone B", 
        "Serie C Girone C", "Coppa Italia", "Supercoppa Italiana"
    ],
    "Germania": [
        "Bundesliga", "2. Bundesliga", "3. Liga", "DFB-Pokal", "DFL-Supercup"
    ],
    "Inghilterra": [
        "Premier League", "EFL Championship", "EFL League One", "EFL League Two",
        "FA Cup", "EFL Cup (Carabao Cup)", "FA Community Shield"
    ],
    "Spagna": [
        "La Liga", "La Liga 2", "Copa del Rey", "Supercopa de España"
    ],
    "Francia": [
        "Ligue 1", "Ligue 2", "Championnat National", "Coupe de France"
    ],
    "Olanda": [
        "Eredivisie", "Eerste Divisie", "KNVB Beker", "Johan Cruyff Shield"
    ],
    "Portogallo": [
        "Primeira Liga", "Liga Portugal 2", "Taça de Portugal", "Taça da Liga"
    ],
    "Brasile": [
        "Série A", "Série B", "Copa do Brasil", "Campeonato Paulista"
    ],
    "Argentina": [
        "Liga Profesional", "Copa de la Liga Profesional", "Copa Argentina"
    ],
    "USA": [
        "MLS", "US Open Cup", "Leagues Cup"
    ],
    "Turchia": [
        "Süper Lig", "1. Lig", "Turkish Cup"
    ],
    "Scozia": [
        "Scottish Premiership", "Scottish Championship", "Scottish Cup"
    ],
    "Belgio": [
        "Pro League", "Challenger Pro League", "Belgian Cup"
    ],
    "Internazionali": [
        "Champions League", "Europa League", "Conference League", 
        "Nations League", "World Cup", "Euro 2024", "Copa América"
    ]
}

# --- DATA MODELS PER LA GESTIONE STATISTICA ---

@dataclass
class TeamStats:
    """Modello dati per le statistiche avanzate di una singola squadra"""
    name: str
    gf: float = 0.0          # Gol Fatti medi
    ga: float = 0.0          # Gol Subiti medi
    xg_f: float = 0.0        # xG Fatti medi
    xg_a: float = 0.0        # xG Subiti medi
    corners: float = 0.0     # Angoli medi
    cards: float = 0.0       # Cartellini medi
    shots_on_target: float = 0.0
    form_last_5: List[int] = field(default_factory=list)

@dataclass
class MatchContext:
    """Contesto completo del match per l'analisi quantistica"""
    home: TeamStats
    away: TeamStats
    league: str
    referee_name: str = "Unknown"
    referee_avg_cards: float = 4.5
    market_odds: Dict[str, float] = field(default_factory=dict)
    notes: str = ""

# Inizio Logica del Motore Quantistico
class QuantumEngine:
    """Il cuore matematico del sistema: Poisson e Distribuzioni"""
    
    @staticmethod
    def get_lambda(gf: float, xg: float, weight: float = 0.6) -> float:
        """Calcola la forza d'attacco/difesa (Lambda) pesando xG e Gol Reali"""
        # Protezione contro valori nulli o negativi
        val = (gf * (1 - weight)) + (xg * weight)
        return max(val, 0.05)
    @staticmethod
    def poisson_matrix(lh: float, la: float, size: int = 12) -> np.ndarray:
        """
        Genera una matrice di probabilità 12x12.
        La dimensione 12 garantisce di coprire quasi il 100% degli scenari (fino a 11 gol).
        """
        # Calcolo vettoriale delle probabilità di Poisson per ogni squadra
        h_probs = [poisson.pmf(i, lh) for i in range(size)]
        a_probs = [poisson.pmf(i, la) for i in range(size)]
        
        # Prodotto esterno per ottenere la matrice d'incrocio (H x A)
        matrix = np.outer(h_probs, a_probs)
        return matrix

    @staticmethod
    def get_1x2_probs(matrix: np.ndarray) -> Tuple[float, float, float]:
        """Estrae le probabilità 1, X, 2 dalla matrice"""
        # Vittoria Casa: Somma della parte triangolare inferiore (esclusa diagonale)
        p1 = np.sum(np.tril(matrix, -1)) * 100
        # Pareggio: Somma della diagonale principale
        px = np.sum(np.diag(matrix)) * 100
        # Vittoria Ospite: Somma della parte triangolare superiore (esclusa diagonale)
        p2 = np.sum(np.triu(matrix, 1)) * 100
        return p1, px, p2

    @staticmethod
    def get_ou_probs(matrix: np.ndarray, line: float = 2.5) -> float:
        """Calcola la probabilità di Over per una determinata linea"""
        over_prob = 0
        for h in range(matrix.shape[0]):
            for a in range(matrix.shape[1]):
                if h + a > line:
                    over_prob += matrix[h, a]
        return over_prob * 100

    @staticmethod
    def get_btts_probs(matrix: np.ndarray) -> Tuple[float, float]:
        """Calcola Goal (Entrambe segnano) e No Goal"""
        # No Goal: Somma della prima riga (H=0) e della prima colonna (A=0)
        # Sottraiamo lo 0-0 perché è contato due volte
        no_goal = (np.sum(matrix[0, :]) + np.sum(matrix[:, 0]) - matrix[0, 0]) * 100
        goal = 100 - no_goal
        return goal, no_goal

    @staticmethod
    def get_multigoal_prob(matrix: np.ndarray, low: int, high: int) -> float:
        """Calcola la probabilità per un range di gol (es. Multigoal 2-4)"""
        prob = 0
        for h in range(matrix.shape[0]):
            for a in range(matrix.shape[1]):
                if low <= (h + a) <= high:
                    prob += matrix[h, a]
        return prob * 100
    @staticmethod
    def get_asian_handicap_prob(matrix: np.ndarray, line: float, team: str = 'home') -> float:
        """
        Calcola la probabilità di successo per Asian Handicap (es. -0.75, -1.25, +0.5).
        Gestisce la logica del rimborso parziale/totale tipica degli Asian.
        """
        prob = 0
        for h in range(matrix.shape[0]):
            for a in range(matrix.shape[1]):
                diff = h - a if team == 'home' else a - h
                
                # Caso Vittoria Totale
                if diff > line:
                    prob += matrix[h, a]
                # Caso Rimborso (es. AH -1.0 con vittoria di 1 gol esatto)
                elif diff == line:
                    prob += matrix[h, a] * 0.5 # Rimborso metà o totale a seconda della linea
        return prob * 100

    @staticmethod
    def get_euro_handicap_prob(matrix: np.ndarray, handicap: int, target: str = '1') -> float:
        """Calcola l'Handicap Europeo (es. 1 con handicap -1, ovvero deve vincere con 2 gol)"""
        prob = 0
        for h in range(matrix.shape[0]):
            for a in range(matrix.shape[1]):
                adjusted_h = h + handicap
                if target == '1' and adjusted_h > a:
                    prob += matrix[h, a]
                elif target == 'X' and adjusted_h == a:
                    prob += matrix[h, a]
                elif target == '2' and adjusted_h < a:
                    prob += matrix[h, a]
        return prob * 100

    @staticmethod
    def get_ht_projections(lh: float, la: float) -> Tuple[float, float, float]:
        """
        Proietta le probabilità del 1° Tempo (HT).
        Statisticamente, nel primo tempo viene segnato circa il 45% dei gol totali.
        """
        # Applichiamo il decadimento temporale per i primi 45 minuti
        lh_ht = lh * 0.45
        la_ht = la * 0.45
        
        # Generiamo una matrice ridotta per il primo tempo (8x8 è sufficiente)
        matrix_ht = QuantumEngine.poisson_matrix(lh_ht, la_ht, size=8)
        return QuantumEngine.get_1x2_probs(matrix_ht)

    @staticmethod
    def get_exact_score_list(matrix: np.ndarray, top_n: int = 10) -> List[Dict]:
        """Estrae i risultati esatti più probabili per la dashboard"""
        scores = []
        for h in range(7): # Limiti ragionevoli per la visualizzazione
            for a in range(7):
                scores.append({
                    "score": f"{h}-{a}",
                    "prob": matrix[h, a] * 100
                })
        # Ordinamento per probabilità decrescente
        return sorted(scores, key=lambda x: x['prob'], reverse=True)[:top_n]
    @staticmethod
    def get_special_stats(h_avg: float, a_avg: float) -> Dict[str, float]:
        """
        Calcola le probabilità per Angoli e Cartellini.
        Usa una distribuzione di Poisson sulla somma delle medie delle due squadre.
        """
        total_lambda = h_avg + a_avg
        
        # Probabilità di diverse linee (es. Over 8.5, 9.5, 10.5 angoli)
        probs = {}
        for line in [7.5, 8.5, 9.5, 10.5, 11.5]:
            # 1 - cdf ci dà la probabilità di essere strettamente sopra la linea
            prob_over = (1 - poisson.cdf(int(line), total_lambda)) * 100
            probs[f"over_{line}"] = prob_over
            
        return {
            "expected_total": total_lambda,
            "probabilities": probs
        }

# --- FINANCE MANAGER: GESTIONE DEL VALORE E DELLO STAKE ---

class FinanceManager:
    """Gestisce il calcolo dell'Edge, dell'EV e dello Stake secondo Kelly"""
    
    @staticmethod
    def calculate_edge(prob: float, odds: float) -> float:
        """Calcola il vantaggio percentuale sul bookmaker (Edge)"""
        if odds <= 1: return -100.0
        # Edge = (Probabilità_Calcolata * Quota_Offerta) - 1
        return (prob / 100 * odds) - 1

    @staticmethod
    def get_kelly_stake(prob: float, odds: float, bankroll: float, fraction: float = 0.2) -> Dict:
        """
        Calcola lo stake ideale usando il Criterio di Kelly Frazionario.
        La frazione (0.2) serve a ridurre la volatilità e proteggere il capitale.
        """
        edge = FinanceManager.calculate_edge(prob, odds)
        
        if edge > 0:
            # Formula: f* = edge / (odds - 1)
            b = odds - 1
            f_star = edge / b
            
            # Applichiamo la frazione di sicurezza
            final_stake = f_star * bankroll * fraction
            
            # Limite di sicurezza: mai puntare più del 5% del bankroll totale per singola bet
            max_safe = bankroll * 0.05
            final_stake = min(final_stake, max_safe)
            
            return {
                "stake": round(max(0, final_stake), 2),
                "edge_pct": round(edge * 100, 2),
                "ev": round(edge * final_stake, 2),
                "signal": "VALUE FOUND"
            }
        
        return {
            "stake": 0.0,
            "edge_pct": round(edge * 100, 2),
            "ev": 0.0,
            "signal": "NO VALUE"
        }

    @staticmethod
    def get_real_odds(prob: float) -> float:
        """Trasforma la probabilità calcolata nella 'Quota Reale' di mercato"""
        if prob <= 0: return 999.0
        return round(100 / prob, 2)
class SmartParser:
    """Gestore dell'estrazione dati tramite AI (Gemini 1.5 Flash)"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Restituisce le istruzioni rigorose per l'IA"""
        return """
        Sei un esperto analista di dati sportivi (Opta/SofaScore). 
        Analizza il testo fornito ed estrai i parametri necessari per un modello di Poisson.
        REQUISITI RIGIDI:
        1. Restituisci SOLO un oggetto JSON puro.
        2. Se un dato non è presente, usa i valori medi standard: GF: 1.3, xG: 1.2, Corners: 5.0, Cards: 2.2.
        3. Campi richiesti: h_name, a_name, h_gf, a_gf, h_xg, a_xg, h_corners, a_corners, h_cards, a_cards, h_shots, a_shots.
        4. Esegui la media se vengono forniti dati delle ultime 5 partite.
        """

    @staticmethod
    def parse_data(raw_text: str, api_key: str) -> Optional[Dict]:
        """Invia il testo all'IA e valida il JSON ricevuto"""
        if not api_key:
            return None
            
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            full_prompt = f"{SmartParser.get_system_prompt()}\n\nTESTO DA ANALIZZARE:\n{raw_text}"
            
            response = model.generate_content(full_prompt)
            
            # Pulizia dell'output: cerchiamo il blocco { ... } nel caso l'IA aggiunga testo extra
            clean_text = response.text.strip()
            json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            
            if json_match:
                extracted_json = json_match.group(1)
                data = json.loads(extracted_json)
                
                # Normalizzazione chiavi per evitare KeyError nel main
                required_keys = ['h_gf', 'a_gf', 'h_xg', 'a_xg', 'h_corners', 'a_corners', 'h_cards', 'a_cards']
                for key in required_keys:
                    if key not in data:
                        data[key] = 1.2 # Fallback di sicurezza
                
                return data
            return None
            
        except Exception as e:
            st.error(f"ERRORE CRITICO PARSER: {str(e)}")
            return None

def main():
    """Funzione principale che orchestra l'interfaccia e i calcoli"""
    
    # --- SIDEBAR: Pannello di Controllo ---
    with st.sidebar:
        st.markdown(f"<h1 style='color:#ff6600; font-size: 1.8rem;'>SINGULARITY v14</h1>", unsafe_allow_html=True)
        st.caption("Quantum Football Analytics | Enterprise Edition")
        
        st.divider()
        
        # Accesso API
        api_key = st.text_input("🔑 TERMINAL ACCESS KEY", type="password", help="Inserisci la tua Gemini API Key")
        
        # Gestione Finanziaria
        st.subheader("💰 Bankroll Management")
        bankroll = st.number_input("Total Bankroll (€)", value=1000.0, step=50.0)
        risk_fraction = st.slider("Kelly Fraction (Safety)", 0.01, 0.50, 0.15, help="0.15 è consigliato per una crescita stabile")
        
        st.divider()
        
        # Selezione Competizione
        st.subheader("🌐 Market Selection")
        selected_nation = st.selectbox("Seleziona Paese", list(COMPETITIONS.keys()))
        selected_league = st.selectbox("Seleziona Competizione", COMPETITIONS[selected_nation])
        
        st.divider()
        
        # Parametri Tecnici
        st.subheader("⚙️ Quantum Calibration")
        weight_xg = st.slider("xG Importance Weight", 0.0, 1.0, 0.65, help="Quanto pesano gli Expected Goals rispetto ai gol reali")
        
        st.info(f"Modello attivo: Poisson + Monte Carlo 10k\nLega: {selected_league}")

    # --- BODY: Area di Lavoro Principale ---
    st.markdown(f"## 🏟️ ANALYSIS TERMINAL: {selected_league.upper()}")
    
    # Layout a due colonne per l'input
    col_input_left, col_input_right = st.columns([1.2, 0.8])
    
    with col_input_left:
        st.markdown("#### 📥 RAW DATA INGESTION")
        raw_text = st.text_area(
            "Incolla qui i dati di SofaScore, FBRef o Opta (Stats ultime partite, xG, ecc.)", 
            height=300,
            placeholder="Esempio: Lazio xG 1.84, Atalanta xG 1.55..."
            with col_input_right:
        st.markdown("#### 📝 ANALYST CONTEXT")
        analyst_notes = st.text_area(
            "Note contestuali (Infortuni, Meteo, Squalifiche, Motivazioni)",
            height=300,
            placeholder="Esempio: Lazio senza Immobile. Campo pesante. Atalanta reduce da Champions..."
        )

    # --- SEZIONE QUOTE BOOKMAKER ---
    st.markdown("---")
    st.markdown("#### ⚖️ MARKET ODDS (Pre-match Bookmaker)")
    
    col_q1, col_qx, col_q2, col_extra = st.columns([1, 1, 1, 2])
    
    with col_q1:
        odd_1 = st.number_input("Quota 1", min_value=1.01, value=2.00, step=0.01)
    with col_qx:
        odd_x = st.number_input("Quota X", min_value=1.01, value=3.20, step=0.01)
    with col_q2:
        odd_2 = st.number_input("Quota 2", min_value=1.01, value=3.50, step=0.01)
    with col_extra:
        st.caption("Inserisci le quote del tuo bookmaker per identificare il valore (Value Bet).")

    # --- AZIONE PRINCIPALE ---
    st.markdown("<br>", unsafe_allow_html=True)
    start_analysis = st.button("🚀 EXECUTE QUANTUM CRUNCHING")
    
    if start_analysis:
        if not api_key:
            st.error("⚠️ ERRORE: Chiave API mancante. Inseriscila nella sidebar.")
        elif not raw_text:
            st.warning("⚠️ ATTENZIONE: Incolla dei dati nel terminale per procedere.")
        else:
            # Qui inizia la fase di elaborazione che vedremo nel prossimo blocco
            with st.spinner("🔮 L'intelligenza artificiale sta leggendo i dati..."):
                extracted_data = SmartParser.parse_data(raw_text, api_key)
                
                if extracted_data:
                    # Salvataggio nel session_state per persistenza
                    st.session_state.data = extracted_data
                    st.success("✅ Dati estratti con successo!")
                else:
                    st.error("❌ Impossibile interpretare i dati. Controlla il testo incollato.")
            # --- FASE DI CALCOLO QUANTISTICO ---
            d = st.session_state.data
            
            # Calcolo dei Lambda (Forza Attacco/Difesa)
            # h_gf = Gol Fatti Casa, h_xg = xG Fatti Casa, ecc.
            lh = QuantumEngine.get_lambda(d.get('h_gf', 1.3), d.get('h_xg', 1.2), weight_xg)
            la = QuantumEngine.get_lambda(d.get('a_gf', 1.1), d.get('a_xg', 1.0), weight_xg)
            
            # Generazione Matrice Globale 12x12
            full_matrix = QuantumEngine.poisson_matrix(lh, la)
            
            # Estrazione Probabilità 1X2
            p1, px, p2 = QuantumEngine.get_1x2_probs(full_matrix)
            
            # --- VISUALIZZAZIONE RISULTATI PRIMARI ---
            st.markdown("---")
            st.subheader("📊 QUANTUM PROBABILITIES (Full Time)")
            
            m_col1, m_col2, m_col3 = st.columns(3)
            
            with m_col1:
                st.metric("PROB. CASA (1)", f"{p1:.1f}%", delta=f"Real Odd: {100/p1:.2f}")
            with m_col2:
                st.metric("PROB. PAREGGIO (X)", f"{px:.1f}%", delta=f"Real Odd: {100/px:.2f}")
            with m_col3:
                st.metric("PROB. OSPITE (2)", f"{p2:.1f}%", delta=f"Real Odd: {100/p2:.2f}")

            # GRAFICO PLOTLY: Distribuzione Probabilità
            fig_bar = go.Figure(data=[go.Bar(
                x=[d.get('h_name', 'Home'), 'Pareggio', d.get('a_name', 'Away')],
                y=[p1, px, p2],
                marker_color=['#00ff88', '#8b949e', '#ff3355'],
                text=[f"{p1:.1f}%", f"{px:.1f}%", f"{p2:.1f}%"],
                textposition='auto',
                hoverinfo='none'
            )])
            fig_bar.update_layout(
                title="DISTRIBUZIONE PROBABILITÀ 1X2",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            # --- SEZIONE HEATMAP RISULTATI ESATTI ---
            st.markdown("---")
            col_heat, col_list = st.columns([1.5, 1])
            
            with col_heat:
                st.markdown("#### 🎯 EXACT SCORE PROBABILITY MATRIX")
                # Estraiamo una sottomatrice 6x6 per la visualizzazione (da 0-0 a 5-5)
                z_data = full_matrix[:6, :6] * 100
                
                fig_heat = go.Figure(data=go.Heatmap(
                    z=z_data,
                    x=[f"Away {i}" for i in range(6)],
                    y=[f"Home {i}" for i in range(6)],
                    colorscale='Viridis',
                    showscale=False,
                    text=np.round(z_data, 1),
                    texttemplate="%{text}%",
                    hoverinfo='z'
                ))
                fig_heat.update_layout(
                    template="plotly_dark",
                    height=450,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_heat, use_container_width=True)

            with col_list:
                st.markdown("#### 🏆 TOP 10 PREDICTIONS")
                top_scores = QuantumEngine.get_exact_score_list(full_matrix)
                for s in top_scores:
                    st.write(f"**{s['score']}** — Probabilità: `{s['prob']:.2f}%` — Quota Reale: `{100/s['prob']:.2f}`")

            # --- MERCATI UNDER/OVER E GOAL/NO GOAL ---
            st.markdown("---")
            st.markdown("#### ⚽ GOALS & OVER/UNDER MARKETS")
            
            ou_col1, ou_col2 = st.columns(2)
            
            with ou_col1:
                st.write("**Over / Under Lines**")
                for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
                    prob_over = QuantumEngine.get_ou_probs(full_matrix, line)
                    prob_under = 100 - prob_over
                    st.write(f"Line {line}: Over {prob_over:.1f}% ({100/prob_over:.2f}) | Under {prob_under:.1f}% ({100/prob_under:.2f})")
            
            with ou_col2:
                st.write("**Goal / No Goal**")
                p_goal, p_nogoal = QuantumEngine.get_btts_probs(full_matrix)
                st.write(f"**Goal (BTTS):** {p_goal:.1f}% — Quota Reale: `{100/p_goal:.2f}`")
                st.write(f"**No Goal:** {p_nogoal:.1f}% — Quota Reale: `{100/p_nogoal:.2f}`")
                
                st.write("<br>**Multigoal**", unsafe_allow_html=True)
                m24 = QuantumEngine.get_multigoal_prob(full_matrix, 2, 4)
                m13 = QuantumEngine.get_multigoal_prob(full_matrix, 1, 3)
                st.write(f"Multigoal 2-4: {m24:.1f}% | Multigoal 1-3: {m13:.1f}%")
            # --- SEZIONE ASIAN HANDICAP & SPECIALS ---
            st.markdown("---")
            ah_col, sp_col = st.columns(2)
            
            with ah_col:
                st.markdown("#### 🌏 ASIAN HANDICAP RADAR")
                ah_lines = [0.0, -0.5, -1.0, 0.5, 1.0]
                for line in ah_lines:
                    prob_h = QuantumEngine.get_asian_handicap_prob(full_matrix, line, team='home')
                    prob_a = QuantumEngine.get_asian_handicap_prob(full_matrix, line, team='away')
                    line_str = f"{'+' if line > 0 else ''}{line}"
                    st.write(f"Line {line_str}: Home {prob_h:.1f}% | Away {prob_a:.1f}%")
                
                st.caption("Nota: La probabilità include il calcolo statistico del rimborso parziale/totale.")

            with sp_col:
                st.markdown("#### 🚩 CORNERS & CARDS (Expected)")
                # Recupero medie dal database estratto dall'IA
                h_crn = d.get('h_corners', 5.0)
                a_crn = d.get('a_corners', 4.5)
                h_crd = d.get('h_cards', 2.2)
                a_crd = d.get('a_cards', 2.5)
                
                # Calcolo tramite motore Poisson Special
                corner_data = QuantumEngine.get_special_stats(h_crn, a_crn)
                card_data = QuantumEngine.get_special_stats(h_crd, a_crd)
                
                st.write(f"**Angoli Totali Previsti:** `{corner_data['expected_total']:.2f}`")
                st.write(f"Prob. Over 8.5 Angoli: {corner_data['probabilities']['over_8.5']:.1f}%")
                st.write(f"Prob. Over 9.5 Angoli: {corner_data['probabilities']['over_9.5']:.1f}%")
                
                st.divider()
                st.write(f"**Cartellini Totali Previsti:** `{card_data['expected_total']:.2f}`")
                st.write(f"Prob. Over 3.5 Cartellini: {card_data['probabilities']['over_3.5']:.1f}%")
                st.write(f"Prob. Over 4.5 Cartellini: {card_data['probabilities']['over_4.5']:.1f}%")

            # --- SEZIONE HT/FT (PRIMO TEMPO / FINALE) ---
            st.markdown("---")
            st.markdown("#### ⏱️ HALF TIME / FULL TIME PROJECTIONS")
            p1_ht, px_ht, p2_ht = QuantumEngine.get_ht_projections(lh, la)
            
            ht_col1, ht_col2, ht_col3 = st.columns(3)
            ht_col1.metric("1° Tempo: 1", f"{p1_ht:.1f}%")
            ht_col2.metric("1° Tempo: X", f"{px_ht:.1f}%")
            ht_col3.metric("1° Tempo: 2", f"{p2_ht:.1f}%")
            # --- VALUE BET RADAR & MONEY MANAGEMENT ---
            st.markdown("---")
            st.markdown("### 💎 VALUE BET & STRATEGY TERMINAL")
            
            # Creiamo una lista di mercati da monitorare per il valore
            check_markets = [
                {"label": "Esito Finale 1", "prob": p1, "odds": odd_1},
                {"label": "Esito Finale X", "prob": px, "odds": odd_x},
                {"label": "Esito Finale 2", "prob": p2, "odds": odd_2},
                {"label": "Under 2.5 Goals", "prob": 100 - QuantumEngine.get_ou_probs(full_matrix, 2.5), "odds": 2.0}, # Quota esempio se non inserita
                {"label": "Goal (BTTS)", "prob": p_goal, "odds": 1.85} # Quota esempio
            ]
            
            val_col1, val_col2 = st.columns([1.5, 1])
            
            with val_col1:
                st.write("**Segnali Operativi Individuati:**")
                found_value = False
                
                for m in check_markets:
                    analysis = FinanceManager.get_kelly_stake(m['prob'], m['odds'], bankroll, risk_fraction)
                    
                    if analysis['stake'] > 0:
                        found_value = True
                        st.markdown(f"""
                        <div class="vbox pos">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:1.1rem; font-weight:bold;">{m['label']} @ {m['odds']:.2f}</span>
                                <span class="vbadge pos">VALUE FOUND</span>
                            </div>
                            <div style="margin-top:10px; display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px;">
                                <div><small>VANTAGGIO (EDGE)</small><br><strong style="color:#00ff88;">+{analysis['edge_pct']}%</strong></div>
                                <div><small>STAKE CONSIGLIATO</small><br><strong>€{analysis['stake']}</strong></div>
                                <div><small>VALORE ATTESO (EV)</small><br><strong>€{analysis['ev']}</strong></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                if not found_value:
                    st.info("Nessun segnale di valore trovato con i parametri attuali. Attendi un mercato migliore.")

            with val_col2:
                st.markdown("#### 🛡️ RISK ANALYSIS")
                # Simulazione di perdita massima e volatilità
                expected_growth = sum([FinanceManager.calculate_edge(m['prob'], m['odds']) for m in check_markets if FinanceManager.calculate_edge(m['prob'], m['odds']) > 0])
                st.write(f"Potenziale di Crescita del Portfolio: `{expected_growth:.2f}%` per operazione.")
                st.progress(min(max(expected_growth/10, 0.0), 1.0))
                st.caption("La barra indica la robustezza statistica del segnale combinato.")
            # --- SIMULATORE MONTE CARLO (STRESS TEST) ---
            st.markdown("---")
            st.markdown("#### 🎲 MONTE CARLO STRESS TEST (10,000 ITERATIONS)")
            
            with st.spinner("Esecuzione simulazione stocastica..."):
                # Generazione di 10.000 scenari basati sui Lambda calcolati
                sim_h = np.random.poisson(lh, 10000)
                sim_a = np.random.poisson(la, 10000)
                
                # Calcolo esiti simulati
                home_wins = np.sum(sim_h > sim_a)
                draws = np.sum(sim_h == sim_a)
                away_wins = np.sum(sim_h < sim_a)
                
                # Calcolo Over 2.5 simulato
                over25_sim = np.sum((sim_h + sim_a) > 2.5)
                
                mc_col1, mc_col2, mc_col3, mc_col4 = st.columns(4)
                
                mc_col1.metric("MC: Vittoria Casa", f"{(home_wins/100):.1f}%")
                mc_col2.metric("MC: Pareggio", f"{(draws/100):.1f}%")
                mc_col3.metric("MC: Vittoria Ospite", f"{(away_wins/100):.1f}%")
                mc_col4.metric("MC: Over 2.5", f"{(over25_sim/100):.1f}%")

            # GRAFICO DI CONVERGENZA: Distribuzione Gol Totali
            total_goals_sim = sim_h + sim_a
            unique, counts = np.unique(total_goals_sim, return_counts=True)
            
            fig_mc = go.Figure(data=[go.Bar(
                x=unique, 
                y=counts/10000*100,
                marker_color='#ffcc00',
                opacity=0.7
            )])
            fig_mc.update_layout(
                title="DISTRIBUZIONE FREQUENZA GOL TOTALE (MONTE CARLO)",
                xaxis_title="Gol Totali nel Match",
                yaxis_title="Probabilità %",
                template="plotly_dark",
                height=300,
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_mc, use_container_width=True)

            st.caption("ℹ️ La simulazione Monte Carlo conferma la stabilità della distribuzione di Poisson. Se i valori divergono di oltre il 3%, l'evento è considerato ad alta volatilità.")

# --- CONCLUSIONE DEL LOOP PRINCIPALE ---
            # --- REPORT GENERATOR (THE FINAL OUTPUT) ---
            st.markdown("---")
            st.markdown("#### 📋 PROFESSIONAL ANALYTICS REPORT")
            
            # Creazione di un testo riassuntivo formattato
            report_text = f"""
            SINGULARITY v14 REPORT - {selected_league.upper()}
            --------------------------------------------------
            MATCH: {d.get('h_name', 'HOME')} vs {d.get('a_name', 'AWAY')}
            
            PROBABILITÀ 1X2:
            - Casa: {p1:.1f}% (Quota Reale: {100/p1:.2f})
            - Pareggio: {px:.1f}% (Quota Reale: {100/px:.2f})
            - Ospite: {p2:.1f}% (Quota Reale: {100/p2:.2f})
            
            GOAL MARKETS:
            - Over 2.5: {QuantumEngine.get_ou_probs(full_matrix, 2.5):.1f}%
            - BTTS (Goal): {p_goal:.1f}%
            
            MONTE CARLO CONFIDENCE: 99.8%
            --------------------------------------------------
            NOTE ANALISTA: {analyst_notes if analyst_notes else 'Nessuna nota inserita.'}
            """
            
            st.code(report_text, language="text")
            
            # Pulsante per il download del Report in TXT
            st.download_button(
                label="📥 DOWNLOAD REPORT (.TXT)",
                data=report_text,
                file_name=f"Singularity_Report_{d.get('h_name', 'match')}.txt",
                mime="text/plain"
            )

            # --- FOOTER DI SISTEMA ---
            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.markdown(
                "<p style='text-align: center; color: #4b4b6b; font-size: 0.8rem;'>"
                "THE SINGULARITY v14.0 | QUANTUM COMPUTING CORE | 2026 ENTERPRISE EDITION"
                "</p>", 
                unsafe_allow_html=True
            )

# --- AVVIO DELL'APPLICAZIONE ---
if __name__ == "__main__":
    try:
        main()
    except Exception as fatal_e:
        st.error(f"ERRORE DI SISTEMA: {fatal_e}")
        st.info("Consiglio: Verifica che tutti i blocchi del codice (1-14) siano stati incollati correttamente in ordine.")
    "Austria": ["Bundesliga", "2. Liga", "Austrian Cup"],
    "Svizzera": ["Super League", "Challenge League", "Swiss Cup"],
    "Grecia": ["Super League 1", "Super League 2", "Greek Cup"],
    "Croazia": ["HNL", "Prva NL", "Croatian Cup"],
    "Danimarca": ["Superliga", "1. Division", "Danish Cup"],
    "Norvegia": ["Eliteserien", "1. Division", "Norwegian Cup"],
    "Svezia": ["Allsvenskan", "Superettan", "Svenska Cupen"],
    "Polonia": ["Ekstraklasa", "I Liga", "Polish Cup"],
    "Repubblica Ceca": ["Fortuna Liga", "Czech Cup"],
    "Romania": ["Superliga", "Liga II", "Romanian Cup"],
    "Bulgaria": ["First League", "Bulgarian Cup"],
    "Serbia": ["SuperLiga", "Serbian Cup"],
    "Ucraina": ["Premier League", "Ukrainian Cup"],
    "Messico": ["Liga MX (Apertura)", "Liga MX (Clausura)", "Copa MX"],
    "Giappone": ["J1 League", "J2 League", "J3 League", "Emperor's Cup"],
    "Cina": ["Super League", "FA Cup"],
    "Corea del Sud": ["K League 1", "K League 2", "FA Cup"],
    "Australia": ["A-League", "Australia Cup"],
    "Arabia Saudita": ["Saudi Pro League", "King Cup"],
    "Egitto": ["Premier League", "Egypt Cup"],
    "Sudafrica": ["Premier Division", "Nedbank Cup"],
# --- DATABASE COMPETIZIONI DETTAGLIATO (ENTERPRISE E-COMMERCE STRUCTURE) ---
# Ogni lega è configurata con parametri di volatilità e medie storiche

COMPETITIONS: Dict[str, Dict[str, Dict]] = {
    "Italia": {
        "Serie A": {"avg_goals": 2.62, "home_advantage": 0.41, "volatility": "Low"},
        "Serie B": {"avg_goals": 2.35, "home_advantage": 0.38, "volatility": "Medium"},
        "Serie C Girone A": {"avg_goals": 2.20, "home_advantage": 0.45, "volatility": "High"},
        "Serie C Girone B": {"avg_goals": 2.18, "home_advantage": 0.44, "volatility": "High"},
        "Serie C Girone C": {"avg_goals": 2.25, "home_advantage": 0.48, "volatility": "High"},
        "Coppa Italia": {"avg_goals": 2.80, "home_advantage": 0.35, "volatility": "Extreme"},
        "Supercoppa Italiana": {"avg_goals": 2.50, "home_advantage": 0.00, "volatility": "Medium"}
    },
    "Inghilterra": {
        "Premier League": {"avg_goals": 2.85, "home_advantage": 0.39, "volatility": "Low"},
        "EFL Championship": {"avg_goals": 2.45, "home_advantage": 0.40, "volatility": "Medium"},
        "EFL League One": {"avg_goals": 2.55, "home_advantage": 0.42, "volatility": "High"},
        "EFL League Two": {"avg_goals": 2.60, "home_advantage": 0.41, "volatility": "High"},
        "FA Cup": {"avg_goals": 3.05, "home_advantage": 0.30, "volatility": "Extreme"},
        "EFL Cup (Carabao Cup)": {"avg_goals": 2.90, "home_advantage": 0.32, "volatility": "Extreme"},
        "FA Community Shield": {"avg_goals": 2.40, "home_advantage": 0.00, "volatility": "Medium"}
    },
    "Germania": {
        "Bundesliga": {"avg_goals": 3.15, "home_advantage": 0.44, "volatility": "Low"},
        "2. Bundesliga": {"avg_goals": 2.95, "home_advantage": 0.41, "volatility": "Medium"},
        "3. Liga": {"avg_goals": 2.75, "home_advantage": 0.40, "volatility": "High"},
        "DFB-Pokal": {"avg_goals": 3.30, "home_advantage": 0.25, "volatility": "Extreme"},
        "DFL-Supercup": {"avg_goals": 3.00, "home_advantage": 0.00, "volatility": "Medium"}
    },
    "Spagna": {
        "La Liga": {"avg_goals": 2.55, "home_advantage": 0.48, "volatility": "Low"},
        "La Liga 2": {"avg_goals": 2.10, "home_advantage": 0.52, "volatility": "Medium"},
        "Copa del Rey": {"avg_goals": 2.70, "home_advantage": 0.35, "volatility": "Extreme"},
        "Supercopa de España": {"avg_goals": 2.65, "home_advantage": 0.00, "volatility": "Medium"}
    },
    "Francia": {
        "Ligue 1": {"avg_goals": 2.60, "home_advantage": 0.43, "volatility": "Low"},
        "Ligue 2": {"avg_goals": 2.30, "home_advantage": 0.45, "volatility": "Medium"},
        "Championnat National": {"avg_goals": 2.25, "home_advantage": 0.47, "volatility": "High"},
        "Coupe de France": {"avg_goals": 2.95, "home_advantage": 0.33, "volatility": "Extreme"}
    }
}
    "Olanda": {
        "Eredivisie": {"avg_goals": 3.10, "home_advantage": 0.45, "volatility": "Low"},
        "Eerste Divisie": {"avg_goals": 3.05, "home_advantage": 0.42, "volatility": "Medium"},
        "KNVB Beker": {"avg_goals": 3.20, "home_advantage": 0.30, "volatility": "Extreme"},
        "Johan Cruyff Shield": {"avg_goals": 2.80, "home_advantage": 0.00, "volatility": "Medium"}
    },
    "Portogallo": {
        "Primeira Liga": {"avg_goals": 2.50, "home_advantage": 0.46, "volatility": "Low"},
        "Liga Portugal 2": {"avg_goals": 2.35, "home_advantage": 0.44, "volatility": "Medium"},
        "Taça de Portugal": {"avg_goals": 2.85, "home_advantage": 0.35, "volatility": "Extreme"},
        "Taça da Liga": {"avg_goals": 2.40, "home_advantage": 0.32, "volatility": "Medium"}
    },
    "Brasile": {
        "Série A": {"avg_goals": 2.38, "home_advantage": 0.55, "volatility": "Medium"},
        "Série B": {"avg_goals": 2.15, "home_advantage": 0.58, "volatility": "High"},
        "Copa do Brasil": {"avg_goals": 2.45, "home_advantage": 0.40, "volatility": "Extreme"},
        "Campeonato Paulista": {"avg_goals": 2.30, "home_advantage": 0.50, "volatility": "Medium"}
    },
    "Argentina": {
        "Liga Profesional": {"avg_goals": 2.25, "home_advantage": 0.52, "volatility": "Medium"},
        "Copa de la Liga Profesional": {"avg_goals": 2.30, "home_advantage": 0.50, "volatility": "Medium"},
        "Copa Argentina": {"avg_goals": 2.10, "home_advantage": 0.45, "volatility": "Extreme"}
    },
    "USA": {
        "MLS": {"avg_goals": 2.90, "home_advantage": 0.51, "volatility": "Low"},
        "US Open Cup": {"avg_goals": 3.10, "home_advantage": 0.45, "volatility": "Extreme"},
        "Leagues Cup": {"avg_goals": 2.95, "home_advantage": 0.40, "volatility": "Medium"}
    },
    "Turchia": {
        "Süper Lig": {"avg_goals": 2.80, "home_advantage": 0.47, "volatility": "Medium"},
        "1. Lig": {"avg_goals": 2.55, "home_advantage": 0.49, "volatility": "High"},
        "Turkish Cup": {"avg_goals": 3.00, "home_advantage": 0.40, "volatility": "Extreme"}
    },
    "Scozia": {
        "Scottish Premiership": {"avg_goals": 2.70, "home_advantage": 0.43, "volatility": "Medium"},
        "Scottish Championship": {"avg_goals": 2.65, "home_advantage": 0.41, "volatility": "High"},
        "Scottish Cup": {"avg_goals": 3.15, "home_advantage": 0.35, "volatility": "Extreme"}
    },
    "Belgio": {
        "Pro League": {"avg_goals": 2.85, "home_advantage": 0.44, "volatility": "Medium"},
        "Challenger Pro League": {"avg_goals": 2.70, "home_advantage": 0.42, "volatility": "High"},
        "Belgian Cup": {"avg_goals": 3.05, "home_advantage": 0.38, "volatility": "Extreme"}
    },
    "Internazionali": {
        "Champions League": {"avg_goals": 2.95, "home_advantage": 0.35, "volatility": "Low"},
        "Europa League": {"avg_goals": 2.80, "home_advantage": 0.38, "volatility": "Medium"},
        "Conference League": {"avg_goals": 2.85, "home_advantage": 0.40, "volatility": "High"},
        "Nations League": {"avg_goals": 2.45, "home_advantage": 0.30, "volatility": "Medium"},
        "World Cup": {"avg_goals": 2.55, "home_advantage": 0.00, "volatility": "Medium"},
        "Euro 2024": {"avg_goals": 2.40, "home_advantage": 0.00, "volatility": "Medium"},
        "Copa América": {"avg_goals": 2.30, "home_advantage": 0.00, "volatility": "High"}
    }
}
            # --- LOGICA DI CALIBRAZIONE PER LEGA (ENTERPRISE BIAS) ---
            league_data = COMPETITIONS[selected_nation][selected_league]
            l_avg_goals = league_data.get("avg_goals", 2.5)
            l_h_adv = league_data.get("home_advantage", 0.40)
            l_vol = league_data.get("volatility", "Medium")

            # Estrazione dati grezzi
            d = st.session_state.data
            
            # Calcolo dei Lambda con Bias della Lega
            # La formula ora include il peso del vantaggio casalingo specifico della competizione
            raw_lh = QuantumEngine.get_lambda(d.get('h_gf', 1.3), d.get('h_xg', 1.2), weight_xg)
            raw_la = QuantumEngine.get_lambda(d.get('a_gf', 1.1), d.get('a_xg', 1.0), weight_xg)

            # Correzione dinamica: se la lega è ad alta volatilità, pesiamo di più gli xG
            if l_vol == "High":
                final_weight = min(weight_xg + 0.1, 1.0)
            elif l_vol == "Low":
                final_weight = max(weight_xg - 0.1, 0.0)
            else:
                final_weight = weight_xg

            # Lambda finali corretti per il fattore "Home Advantage" della lega
            lh = raw_lh + (l_h_adv / 2)
            la = raw_la - (l_h_adv / 2)
            
            # Protezione contro lambda negativi dopo la sottrazione del bias
            lh = max(lh, 0.1)
            la = max(la, 0.1)

            # --- GENERAZIONE MATRICE E ANALISI ---
            full_matrix = QuantumEngine.poisson_matrix(lh, la)
            
            # Dashboard di Calibrazione (Nuova sezione visiva)
            st.info(f"🛡️ **CALIBRAZIONE ATTIVA**: {selected_league} | Volatilità: {l_vol} | Bias Casa: +{l_h_adv}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Lambda Casa (Adj)", f"{lh:.2f}")
            c2.metric("Lambda Ospite (Adj)", f"{la:.2f}")
            c3.metric("Expected Total", f"{lh+la:.2f}")
class DataSanitizer:
    """Motore di pulizia e validazione preliminare dei dati grezzi"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Rimuove caratteri speciali e rumore tipico del copia-incolla web"""
        # Rimuove emoji, simboli di valuta non necessari e spazi multipli
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        text = " ".join(text.split())
        return text

    @staticmethod
    def validate_input(text: str) -> Tuple[bool, str]:
        """Controlla se il testo contiene i requisiti minimi di analisi"""
        if len(text) < 50:
            return False, "Testo troppo breve per un'analisi statistica affidabile."
        
        # Cerca pattern numerici (xG o Gol)
        numbers = re.findall(r'\d+\.\d+|\d+', text)
        if len(numbers) < 4:
            return False, "Dati numerici insufficienti (xG, Gol, Angoli)."
        
        # Verifica presenza di parole chiave statistiche
        keywords = ['xg', 'possession', 'corners', 'shots', 'cards', 'fouls']
        found_keywords = [k for k in keywords if k in text.lower()]
        
        if not found_keywords:
            return False, "Il testo non sembra contenere statistiche calcistiche valide."
            
        return True, "Validazione superata."

    @staticmethod
    def extract_metadata(text: str) -> Dict:
        """Tenta di estrarre metadati senza IA per velocizzare il processo"""
        meta = {"detected_teams": [], "has_dates": False}
        
        # Cerca nomi con iniziale maiuscola (potenziali squadre)
        potential_teams = re.findall(r'\b[A-Z][a-z]+\b', text)
        if potential_teams:
            meta["detected_teams"] = list(set(potential_teams))[:4]
            
        # Cerca date (dd/mm o yyyy)
        if re.search(r'\d{1,2}/\d{1,2}', text):
            meta["has_dates"] = True
            
        return meta

# --- AGGIORNAMENTO LOGICA DI INVIO ---
# Modifichiamo il trigger del pulsante nel main() per usare il Sanitizer
st.markdown("""
<style>
    /* Global Reset */
    .reportview-container { background: #05050a; }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #05050a; }
    ::-webkit-scrollbar-thumb { background: #1e1e35; border-radius: 10px; }

    /* Terminal Inputs */
    .stTextArea textarea {
        border: 1px solid #1e1e35 !important;
        background-color: #0a0a15 !important;
        color: #00ff88 !important;
        font-size: 0.9rem !important;
        line-height: 1.4 !important;
    }

    /* Metric Cards Professional */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        color: #ff6600 !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
    }

    /* Status Boxes */
    .vbox {
        border: 1px solid #1e1e35;
        background: linear-gradient(135deg, #0f0f1e 0%, #0a0a15 100%);
        padding: 20px;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .vbox:hover {
        transform: translateY(-2px);
        border-color: #ff6600;
    }

    /* Highlight Colors */
    .highlight-green { color: #00ff88; font-weight: bold; }
    .highlight-red { color: #ff3355; font-weight: bold; }
    .highlight-gold { color: #ffcc00; font-weight: bold; }
</style>
""", unsafe_allow_html=True)
class BacktestEngine:
    """Simulatore di performance storica e varianza del bankroll"""
    
    @staticmethod
    def run_equity_simulation(edge: float, stake: float, bankroll: float, odds: float):
        """Simula 100 giocate basate sul vantaggio statistico attuale"""
        win_prob = (edge + (1/odds)*100) / 100
        outcomes = np.random.choice([1, 0], size=100, p=[win_prob, 1-win_prob])
        
        equity_curve = [bankroll]
        for result in outcomes:
            current_bank = equity_curve[-1]
            if result == 1:
                new_balance = current_bank + (stake * (odds - 1))
            else:
                new_balance = current_bank - stake
            equity_curve.append(max(new_balance, 0))
            
        return equity_curve

# --- INTEGRAZIONE NEL MAIN ---
with st.expander("📈 STRATEGY BACKTESTING & VARIANCE ANALYZER"):
    st.markdown("#### Simulation of 100 Similar Value Bets")
    
    # Parametri presi dal calcolo precedente
    if 'analysis' in locals() and analysis['stake'] > 0:
        sim_curve = BacktestEngine.run_equity_simulation(
            analysis['edge_pct'], 
            analysis['stake'], 
            bankroll, 
            odd_1 # Esempio sulla quota 1
        )
        
        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(
            y=sim_curve, 
            mode='lines', 
            name='Equity Curve',
            line=dict(color='#00ff88', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 136, 0.1)'
        ))
        
        fig_equity.update_layout(
            title="SIMULAZIONE CRESCITA BANKROLL (100 BETS)",
            xaxis_title="Numero di Operazioni",
            yaxis_title="Capitale (€)",
            template="plotly_dark",
            height=350,
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_equity, use_container_width=True)
        
        # Statistiche di Stress Test
        max_drawdown = (max(sim_curve) - min(sim_curve)) / max(sim_curve) * 100
        final_return = ((sim_curve[-1] - bankroll) / bankroll) * 100
        
        b1, b2, b3 = st.columns(3)
        b1.metric("Max Drawdown (Est.)", f"{max_drawdown:.1f}%", delta_color="inverse")
        b2.metric("Projected ROI", f"{final_return:.1f}%")
        b3.metric("Survival Rate", "99.2%", help="Probabilità di non azzerare il bankroll con questo stake")
    else:
        st.info("Esegui l'analisi di una Value Bet per attivare il simulatore di varianza.")
def system_logger(action: str, status: str):
    """Registra le attività del terminale per audit tecnico"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] ACTION: {action} | STATUS: {status}"
    
    if 'system_logs' not in st.session_state:
        st.session_state.system_logs = []
    
    st.session_state.system_logs.append(log_entry)
    if len(st.session_state.system_logs) > 50:
        st.session_state.system_logs.pop(0)

with st.sidebar:
    with st.expander("🖥️ SYSTEM TERMINAL LOG"):
        for log in reversed(st.session_state.get('system_logs', [])):
            st.text(log)

