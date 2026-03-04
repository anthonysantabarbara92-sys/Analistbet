import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import google.generativeai as genai

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="STRATEGY BETTING ENGINE v5.5", layout="wide")

database_competizioni = {
    "🇮🇹 Italia": ["Serie A", "Serie B", "Serie C (Gironi A-B-C)", "Coppa Italia"],
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inghilterra": ["Premier League", "Championship (B)", "League One (C)", "FA Cup"],
    "🇪🇸 Spagna": ["La Liga", "La Liga 2 (B)", "Copa del Rey"],
    "🇩🇪 Germania": ["Bundesliga", "2. Bundesliga (B)", "3. Liga (C)"],
    "🇫🇷 Francia": ["Ligue 1", "Ligue 2 (B)", "National (C)"],
    "🇪🇺 Coppe UEFA": ["Champions League", "Europa League", "Conference League", "Nations League"],
    "🏆 FIFA World": ["Mondiali (World Cup)", "Mondiale per Club"],
    "🌍 Altre Leghe": ["Eredivisie", "Primeira Liga", "Super Lig", "Saudi Pro League", "MLS", "Brasileirao"]
}

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Pro Analyst v5.5")
    api_key = st.text_input("🔑 Gemini API Key", type="password")
    st.divider()
    cat = st.selectbox("Nazione/Categoria", list(database_competizioni.keys()))
    league = st.selectbox("Competizione", database_competizioni[cat])

# --- ENGINE MATEMATICO ---
def get_exact_scores(m_h, m_a):
    m_h = max(m_h, 0.01)
    m_a = max(m_a, 0.01)
    scores = []
    for i in range(5): # Gol Casa da 0 a 4
        for j in range(5): # Gol Ospite da 0 a 4
            prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a) * 100
            scores.append({"Risultato": f"{i} - {j}", "Probabilità": prob})
    
    df = pd.DataFrame(scores)
    return df.sort_values(by="Probabilità", ascending=False).head(8)

def get_probs(m_h, m_a):
    m_h = max(m_h, 0.01)
    m_a = max(m_a, 0.01)
    p_h = sum([poisson.pmf(i, m_h) * sum([poisson.pmf(j, m_a) for j in range(i)]) for i in range(1, 10)])
    p_d = sum([poisson.pmf(i, m_h) * poisson.pmf(i, m_a) for i in range(10)])
    p_a = max(0, 1 - p_h - p_d)
    return p_h * 100, p_d * 100, p_a * 100

# --- INTERFACCIA ---
st.title(f"⚽ Analisi Strategica: {league}")

c1, c2 = st.columns(2)
with c1:
    st.subheader("🏠 Casa")
    t_h = st.text_input("Squadra", "Inter", key="th")
    gf_h = st.number_input("Media Gol Fatti", min_value=0.0, value=1.5, step=0.1)
    xg_h = st.number_input("xG (Media)", min_value=0.0, value=1.0, step=0.1)

with c2:
    st.subheader("🚌 Ospite")
    t_a = st.text_input("Squadra ", "Milan", key="ta")
    gf_a = st.number_input("Media Gol Fatti ", min_value=0.0, value=1.2, step=0.1)
    xg_a = st.number_input("xG (Media) ", min_value=0.0, value=1.0, step=0.1)

st.divider()
st.subheader("⚠️ Parametri Situazionali")
i1, i2, i3 = st.columns(3)
with i1:
    inj = st.select_slider("Assenze", ["Nessuna", "Lievie", "Critiche"])
with i2:
    stress = st.select_slider("Stanchezza", ["Riposati", "Media", "Alta"])
with i3:
    mot = st.select_slider("Motivazione", ["Bassa", "Normale", "Decisiva"])

if st.button("🚀 GENERA ANALISI DEFINITIVA"):
    final_h = (gf_h + xg_h) / 2
    final_a = (gf_a + xg_a) / 2
    
    if inj == "Critiche": final_h *= 0.85
    if mot == "Decisiva": final_h *= 1.15
    if stress == "Alta": final_a *= 0.90

    p1, px, p2 = get_probs(final_h, final_a)

    st.markdown("### 📊 Esiti 1X2")
    r1, r2, r3 = st.columns(3)
    r1.metric(f"1 ({t_h})", f"{p1:.1f}%")
    r2.metric("X (Pareggio)", f"{px:.1f}%")
    r3.metric(f"2 ({t_a})", f"{p2:.1f}%")

    # --- SEZIONE RISULTATI ESATTI ---
    st.divider()
    st.subheader("🎯 Top 8 Risultati Esatti (Dati Statistici)")
    df_scores = get_exact_scores(final_h, final_a)
    
    # Visualizzazione a Tabella
    st.table(df_scores.assign(Probabilità=df_scores['Probabilità'].map('{:.2f}%'.format)))

    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""Match: {t_h} vs {t_a}. Poisson Prob: 1={p1:.1f}%, X={px:.1f}%, 2={p2:.1f}%.
            Top Risultati: {df_scores.to_dict()}. Analizza se i risultati esatti statistici sono coerenti con le assenze ({inj}) e consiglia la giocata migliore."""
            response = model.generate_content(prompt)
            st.success("🤖 Responso IA Elite:")
            st.write(response.text)
        except Exception as e:
            st.error(f"Errore: {e}")
