import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import poisson
import google.generativeai as genai

# --- 1. PRO-LEVEL UI CONFIGURATION ---
st.set_page_config(page_title="THE SINGULARITY v13.0", layout="wide", initial_sidebar_state="expanded")

class Style:
    @staticmethod
    def apply():
        st.markdown("""
        <style>
        .reportview-container { background: #0a0a12; }
        .stMetric { border: 1px solid #2e3141; padding: 20px; border-radius: 12px; background: #161b22; }
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #161b22; border-radius: 5px; }
        .main-header { color: #ff4b4b; font-size: 2.5rem; font-weight: 800; text-align: center; margin-bottom: 2rem; }
        </style>
        """, unsafe_allow_html=True)

# --- 2. QUANTUM ENGINE (MATHEMATICAL LOGIC) ---
class QuantumEngine:
    @staticmethod
    def get_poisson_matrix(m_h, m_a, size=12):
        """Genera una matrice di probabilità 12x12 per precisione assoluta."""
        matrix = np.outer(poisson.pmf(np.arange(size), m_h), poisson.pmf(np.arange(size), m_a))
        p1 = np.sum(np.tril(matrix, -1)) * 100
        px = np.sum(np.diag(matrix)) * 100
        p2 = np.sum(np.triu(matrix, 1)) * 100
        return p1, px, p2, matrix

    @staticmethod
    def calculate_multigoal(matrix, low, high):
        """Calcola la probabilità esatta per qualsiasi range multigoal."""
        prob = 0
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                if low <= (i + j) <= high:
                    prob += matrix[i, j]
        return prob * 100

    @staticmethod
    def kelly_stake(prob, odds, bankroll, fraction=0.2):
        """Criterio di Kelly Frazionario per il Money Management professionale."""
        if odds <= 1: return 0
        p = prob / 100
        q = 1 - p
        edge = (p * odds - q) / (odds - 1)
        return round(max(0, edge * bankroll * fraction), 2)

# --- 3. DATA PARSER (AI INTEGRATION) ---
class SmartScraper:
    def __init__(self, api_key):
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def parse_raw_data(self, text):
        if not self.model: return None
        prompt = f"Analizza e restituisci in formato JSON (gf, xg, tiri, angoli, cartellini) per Casa e Ospite: {text}"
        try:
            return self.model.generate_content(prompt).text
        except: return "Errore di parsing."

# --- 4. MAIN APPLICATION LOGIC ---
def main():
    Style.apply()
    st.markdown('<div class="main-header">THE SINGULARITY v13.0</div>', unsafe_allow_html=True)

    if 'api_key' not in st.session_state: st.session_state.api_key = ""

    with st.sidebar:
        st.title("⚙️ Control Panel")
        st.session_state.api_key = st.text_input("Gemini API Key", value=st.session_state.api_key, type="password")
        bankroll = st.number_input("Bankroll Operativo (€)", value=1000, step=100)
        st.divider()
        league = st.selectbox("Competizione", ["Serie A", "Premier League", "Champions League", "Serie B", "Serie C", "La Liga", "Bundesliga"])
        st.info("Algoritmo di analisi quantitativa v13.0 attivato.")

    # INPUT INTERFACE
    st.subheader("📥 Data Acquisition")
    raw_text = st.text_area("Smart Scraper 2.0: Incolla qui i dati grezzi da FBRef/SofaScore", height=100)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🏠 Squadra Casa")
        h_name = st.text_input("Nome", "Inter")
        h_stats = {
            "xg": st.number_input("xG Media", 0.0, 5.0, 1.85, key="h1"),
            "gf": st.number_input("Gol Fatti Media", 0.0, 5.0, 1.90, key="h2"),
            "st": st.number_input("Tiri Porta", 0.0, 15.0, 5.8, key="h3"),
            "cr": st.number_input("Angoli", 0.0, 20.0, 6.2, key="h4"),
            "cd": st.number_input("Cartellini", 0.0, 10.0, 1.8, key="h5")
        }
    with col2:
        st.markdown("### 🚌 Squadra Ospite")
        a_name = st.text_input("Nome ", "Juventus")
        a_stats = {
            "xg": st.number_input("xG Media ", 0.0, 5.0, 1.25, key="a1"),
            "gf": st.number_input("Gol Fatti Media ", 0.0, 5.0, 1.30, key="a2"),
            "st": st.number_input("Tiri Porta ", 0.0, 15.0, 4.1, key="a3"),
            "cr": st.number_input("Angoli ", 0.0, 20.0, 4.5, key="a4"),
            "cd": st.number_input("Cartellini ", 0.0, 10.0, 2.4, key="a5")
        }

    user_notes = st.text_area("📝 Note dell'Analista (Infortuni, Condizioni Meteo, Tattica)")

    if st.button("🔥 ESEGUI ANALISI QUANTISTICA"):
        engine = QuantumEngine()
        m_h = (h_stats["xg"] + h_stats["gf"]) / 2
        m_a = (a_stats["xg"] + a_stats["gf"]) / 2
        
        p1, px, p2, matrix = engine.get_poisson_matrix(m_h, m_a)

        t1, t2, t3, t4 = st.tabs(["📊 Mercati Core", "🎯 Risultati & Multigoal", "🏹 Speciali", "💰 Pro-Strategy"])

        with t1:
            st.header("Distribuzione Probabilità 1X2")
            fig = go.Figure(data=[go.Bar(x=[h_name, 'Pareggio', a_name], y=[p1, px, p2], 
                                         marker_color=['#00cc96', '#636efa', '#ef553b'], text=[f"{p1:.1f}%", f"{px:.1f}%", f"{p2:.1f}%"])])
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("QUOTA REALE 1", f"{(100/p1):.2f}")
            c2.metric("QUOTA REALE X", f"{(100/px):.2f}")
            c3.metric("QUOTA REALE 2", f"{(100/p2):.2f}")

        with t2:
            st.subheader("Analisi Multigoal Esatta")
            mg_col1, mg_col2 = st.columns(2)
            mg_col1.metric("Multigoal 1-3", f"{engine.calculate_multigoal(matrix, 1, 3):.1f}%")
            mg_col1.metric("Multigoal 2-4", f"{engine.calculate_multigoal(matrix, 2, 4):.1f}%")
            mg_col2.metric("Multigoal 2-5", f"{engine.calculate_multigoal(matrix, 2, 5):.1f}%")
            mg_col2.metric("GOAL (Entrambe)", f"{(1 - (poisson.pmf(0, m_h) * poisson.pmf(0, m_a)))*100:.1f}%")
            
            st.divider()
            st.subheader("Top 8 Risultati Esatti (Ranking)")
            res = []
            for i in range(5):
                for j in range(5):
                    res.append({"Punteggio": f"{i}-{j}", "Prob": matrix[i,j]*100})
            st.table(pd.DataFrame(res).sort_values(by="Prob", ascending=False).head(8))

        with t3:
            st.subheader("Proiezioni Speciali (Under/Over)")
            s1, s2, s3 = st.columns(3)
            s1.metric("Over 9.5 Angoli", f"{(1 - sum([poisson.pmf(i, h_stats['cr']+a_stats['cr']) for i in range(10)]))*100:.1f}%")
            s2.metric("Over 4.5 Cartellini", f"{(1 - sum([poisson.pmf(i, h_stats['cd']+a_stats['cd']) for i in range(5)]))*100:.1f}%")
            s3.metric("Over 8.5 Tiri Porta", f"{(1 - sum([poisson.pmf(i, h_stats['st']+a_stats['st']) for i in range(9)]))*100:.1f}%")

        with t4:
            st.subheader("Sistema di Puntata Professionale")
            book_odds = st.number_input(f"Inserisci Quota Bookmaker per il segno più probabile", value=2.0)
            best_prob = max(p1, px, p2)
            stake = engine.kelly_stake(best_prob, book_odds, bankroll)
            
            st.write(f"### 💸 Stake Consigliato: €{stake}")
            st.info("Lo stake è calcolato con un Kelly Frazionario al 20% per minimizzare la volatilità.")

            if st.session_state.api_key:
                scraper = SmartScraper(st.session_state.api_key)
                report_prompt = f"Match: {h_name}-{a_name}. Poisson: 1={p1:.1f}%, X={px:.1f}%, 2={p2:.1f}%. Note: {user_notes}. Identifica la Value Bet."
                st.success("🤖 Responso Finale AI:")
                st.write(scraper.model.generate_content(report_prompt).text)

if __name__ == "__main__":
    main()
