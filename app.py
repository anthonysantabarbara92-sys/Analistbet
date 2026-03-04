import streamlit as st
import numpy as np
from scipy.stats import poisson
import google.generativeai as genai

# --- CONFIGURAZIONE IA ---
# Inserisci qui la tua chiave API (o usa st.secrets per sicurezza su Cloud)
API_KEY = "LA_TUA_API_KEY_QUI" 
if API_KEY != "LA_TUA_API_KEY_QUI":
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Match Analyst AI Pro", layout="wide")

# 1. DATABASE MEDIE (Aggiornabili)
MEDIE_GOL = {"Serie A": 1.35, "Premier": 1.45, "Bundesliga": 1.65, "Liga": 1.25, "Ligue 1": 1.30}

with st.sidebar:
    st.header("⚙️ Impostazioni")
    campionato = st.selectbox("Seleziona Campionato", list(MEDIE_GOL.keys()))
    media_camp = MEDIE_GOL[campionato]
    bankroll = st.number_input("Budget Totale (€)", value=1000)
    st.info("💡 Consiglio: Per i dati live usa siti come Flashscore o FBRef.")

# 2. INPUT DATI
st.header("📊 Analisi Statistica & xG")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏠 Squadra Casa")
    h_att = st.number_input("Media Gol Fatti (Casa)", value=1.6)
    h_def = st.number_input("Media Gol Subiti (Casa)", value=1.0)
    h_xg = st.number_input("xG Fatti (Casa)", value=1.7)
    h_corners = st.number_input("Media Angoli Casa", value=5.5)

with col2:
    st.subheader("🚌 Squadra Ospite")
    a_att = st.number_input("Media Gol Fatti (Ospite)", value=1.1)
    a_def = st.number_input("Media Gol Subiti (Ospite)", value=1.4)
    a_xg = st.number_input("xG Fatti (Ospite)", value=1.0)
    a_falli = st.number_input("Media Falli Ospite", value=13.0)

# 3. ANALISI QUALITATIVA (NEWS)
testo_news = st.text_area("📝 Note, News e Formazioni:", 
                          placeholder="Esempio: Assente il bomber titolare, campo pesante per pioggia...")

# --- ENGINE DI CALCOLO ---
def calcola_match():
    # Poisson base corretta
    h_exp = (h_att/media_camp) * (a_def/media_camp) * media_camp
    a_exp = (a_att/media_camp) * (h_def/media_camp) * media_camp
    
    # Bilanciamento xG (30% peso)
    h_exp_final = (h_exp * 0.7) + (h_xg * 0.3)
    a_exp_final = (a_exp * 0.7) + (a_xg * 0.3)
    
    return h_exp_final, a_exp_final

h_goal, a_goal = calcola_match()

# --- RISULTATI STATISTICI ---
st.markdown("---")
res1, res2, res3 = st.columns(3)

with res1:
    st.metric("⚽ Stima Gol Casa", f"{h_goal:.2f}")
    prob_1 = (1 - poisson.cdf(0, h_goal)) * 100
    st.write(f"Prob. Segna almeno 1 gol: **{prob_1:.1f}%**")

with res2:
    st.metric("⚽ Stima Gol Ospite", f"{a_goal:.2f}")
    prob_a = (1 - poisson.cdf(0, a_goal)) * 100
    st.write(f"Prob. Segna almeno 1 gol: **{prob_a:.1f}%**")

with res3:
    st.metric("🚩 Angoli Stimati", f"{(h_corners + 4.5):.1f}") # Algoritmo semplificato

# --- 🤖 INTEGRAZIONE IA ---
st.markdown("---")
st.header("🧠 Consulto con l'Assistente IA")

if st.button("Analizza Partita con IA"):
    if model:
        with st.spinner("Sto ragionando sui dati..."):
            prompt = f"""
            Agisci come un esperto analista di scommesse sportive. 
            Dati statistici del match:
            - Squadra Casa (Att: {h_att}, xG: {h_xg}) -> Proiezione Gol: {h_goal:.2f}
            - Squadra Ospite (Att: {a_att}, xG: {a_xg}) -> Proiezione Gol: {a_goal:.2f}
            - News dell'ultima ora: {testo_news}
            
            Fornisci un'analisi breve e cinica:
            1. Vedi discrepanze tra numeri e news?
            2. Qual è il rischio principale?
            3. Consiglio tattico (es. "Attenzione all'Under" o "Partita da Over").
            """
            response = model.generate_content(prompt)
            st.markdown(response.text)
    else:
        st.error("⚠️ Configura la tua API KEY nel codice per attivare l'IA!")

# CHECKLIST
st.sidebar.markdown("---")
st.sidebar.write("✅ **Checklist Finale**")
st.sidebar.checkbox("Formazioni Ufficiali")
st.sidebar.checkbox("Meteo controllato")
