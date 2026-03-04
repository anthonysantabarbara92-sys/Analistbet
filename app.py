import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import google.generativeai as genai

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="THE GOD MODE v10.5", layout="wide", initial_sidebar_state="expanded")

# Persistenza dati nella sessione
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'notes' not in st.session_state: st.session_state.notes = ""

# --- DATABASE CAMPIONATI ---
leagues_db = {
    "🇮🇹 Italia": ["Serie A", "Serie B", "Serie C (tutti i gironi)", "Coppa Italia"],
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inghilterra": ["Premier League", "Championship", "League One", "League Two", "FA Cup"],
    "🇪🇸 Spagna": ["La Liga", "La Liga 2", "Copa del Rey"],
    "🇩🇪 Germania": ["Bundesliga", "2. Bundesliga", "3. Liga"],
    "🇫🇷 Francia": ["Ligue 1", "Ligue 2", "National"],
    "🇪🇺 Coppe UEFA": ["Champions League", "Europa League", "Conference League", "Nations League"],
    "🏆 Internazionali": ["Mondiali (World Cup)", "Mondiale per Club", "Qualificazioni"],
    "🌍 Altre Leghe": ["Eredivisie", "Primeira Liga", "Super Lig", "Saudi Pro League", "MLS", "Brasileirao", "J1 League"]
}

# --- ENGINE MATEMATICO ---
def get_poisson_1x2(m_h, m_a):
    m_h, m_a = max(m_h, 0.01), max(m_a, 0.01)
    p1 = sum([poisson.pmf(i, m_h) * sum([poisson.pmf(j, m_a) for j in range(i)]) for i in range(1, 12)]) * 100
    px = sum([poisson.pmf(i, m_h) * poisson.pmf(i, m_a) for i in range(12)]) * 100
    p2 = max(0, 100 - p1 - px)
    return p1, px, p2

def get_over_prob(media, soglia):
    return (1 - sum([poisson.pmf(i, media) for i in range(int(soglia) + 1)])) * 100

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Pannello di Controllo")
    st.session_state.api_key = st.text_input("Gemini API Key", value=st.session_state.api_key, type="password")
    st.divider()
    cat = st.selectbox("Seleziona Nazione", list(leagues_db.keys()))
    sel_league = st.selectbox("Seleziona Competizione", leagues_db[cat])
    st.divider()
    st.info("💡 Consiglio: Copia i dati da FBRef e incollali nel box 'Smart Scraper'.")

# --- INTERFACCIA ---
st.title(f"🚀 Terminale Betting v10.5: {sel_league}")

# 1. SMART DATA ENTRY
st.subheader("🤖 Smart Data Scraper (Semi-Auto)")
raw_input = st.text_area("Copia e incolla qui le statistiche grezze (FBRef/SofaScore)", height=100)

st.divider()

# 2. DATI SQUADRE
col_h, col_a = st.columns(2)
with col_h:
    st.markdown("### 🏠 Casa")
    t_h = st.text_input("Nome Squadra", "Team Home")
    gf_h = st.number_input("Gol Fatti (Media)", 0.0, 5.0, 1.5)
    xg_h = st.number_input("xG (Media)", 0.0, 5.0, 1.6)
    st_h = st.number_input("Tiri in Porta (Media)", 0.0, 15.0, 5.0)
    cr_h = st.number_input("Angoli (Media)", 0.0, 15.0, 5.5)
    cd_h = st.number_input("Cartellini (Media)", 0.0, 10.0, 2.0)

with col_a:
    st.markdown("### 🚌 Ospite")
    t_a = st.text_input("Nome Squadra ", "Team Away")
    gf_a = st.number_input("Gol Fatti (Media) ", 0.0, 5.0, 1.2)
    xg_a = st.number_input("xG (Media) ", 0.0, 5.0, 1.3)
    st_a = st.number_input("Tiri in Porta (Media) ", 0.0, 15.0, 4.0)
    cr_a = st.number_input("Angoli (Media) ", 0.0, 15.0, 4.5)
    cd_a = st.number_input("Cartellini (Media) ", 0.0, 10.0, 2.3)

st.divider()
# 3. DESCRIZIONE E NOTE
st.subheader("📝 Note & Retroscena dell'Analista")
user_notes = st.text_area("Inserisci infortuni, rumors, clima o tue sensazioni sul match", 
                         placeholder="Es: Il portiere titolare è fuori, piove forte, l'allenatore rischia l'esonero...")

# 4. ELABORAZIONE
if st.button("🔥 ESEGUI ANALISI SUPREMA"):
    if not st.session_state.api_key:
        st.error("⚠️ Inserisci la API Key nella barra laterale!")
    else:
        m_h, m_a = (gf_h + xg_h)/2, (gf_a + xg_a)/2
        m_tot = m_h + m_a
        p1, px, p2 = get_poisson_1x2(m_h, m_a)
        
        # Dashboard 1X2
        st.header("📊 Probabilità Calcolate (1X2 & Goal)")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric(f"1 ({t_h})", f"{p1:.1f}%")
        r2.metric("X", f"{px:.1f}%")
        r3.metric(f"2 ({t_a})", f"{p2:.1f}%")
        
        # Goal/No Goal
        p_h0, p_a0 = poisson.pmf(0, m_h), poisson.pmf(0, m_a)
        goal_prob = (1 - (p_h0 + p_a0 - (p_h0 * p_a0))) * 100
        r4.metric("GOAL", f"{goal_prob:.1f}%")

        # Mercati Speciali
        st.divider()
        st.subheader("🎯 Mercati Accessori & Combo")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Over 2.5", f"{get_over_prob(m_tot, 2):.1f}%")
        
        m13 = (poisson.pmf(1, m_tot) + poisson.pmf(2, m_tot) + poisson.pmf(3, m_tot)) * 100
        s2.metric("Multigoal 1-3", f"{m13:.1f}%")
        
        s3.metric("Over 9.5 Angoli", f"{get_over_prob(cr_h + cr_a, 9):.1f}%")
        s4.metric("Over 4.5 Cartellini", f"{get_over_prob(cd_h + cd_a, 4):.1f}%")

        # Risultati Esatti
        st.divider()
        st.subheader("📍 Matrice Risultati Esatti")
        exact = []
        for i in range(4):
            for j in range(4):
                prob = poisson.pmf(i, m_h) * poisson.pmf(j, m_a) * 100
                exact.append({"Punteggio": f"{i}-{j}", "Probabilità": f"{prob:.2f}%"})
        st.table(pd.DataFrame(exact).sort_values(by="Probabilità", ascending=False).head(6))

        # REPORT IA FINALE
        genai.configure(api_key=st.session_state.api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        final_prompt = f"""Analista Betting Professionale. 
        Match: {t_h} vs {t_a} ({sel_league}).
        Dati Poisson: 1={p1:.1f}%, X={px:.1f}%, 2={p2:.1f}%, Goal={goal_prob:.1f}%.
        Stats in campo: Tiri {st_h+st_a}, Angoli {cr_h+cr_a}, Cartellini {cd_h+cd_a}.
        NOTE ANALISTA: {user_notes}
        DATI GREZZI: {raw_input}
        
        Svolgi:
        1. Incrocia i dati Poisson con le Note Analista (Retroscena).
        2. Trova la 'Super Bet' (Combo o mercato speciale ad alto valore).
        3. Identifica il rischio principale del match."""
        
        res = model.generate_content(final_prompt)
        st.success("🕵️ Responso Finale dell'Oracolo (Incrocio Dati & IA)")
        st.write(res.text)
