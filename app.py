import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import google.generativeai as genai

# --- CONFIGURAZIONE PROFESSIONALE ---
st.set_page_config(page_title="ELITE BETTING ENGINE v3.5", layout="wide")

# --- CSS CUSTOM PER INTERFACCIA DARK PREMIUM ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #ffffff; }
    .metric-card { background: linear-gradient(145deg, #1e2530, #161b22); border-radius: 12px; padding: 20px; border: 1px solid #30363d; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .stButton>button { background: linear-gradient(90deg, #00c8ff, #0088ff); color: white; border: none; font-weight: bold; height: 3em; border-radius: 10px; transition: 0.3s; }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 0 15px #00c8ff; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR E FONTI DATI ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/football-monitor.png", width=80)
    st.title("PRO ANALYST HUB")
    gemini_key = st.text_input("🔑 Gemini API Key", type="password")
    
    st.divider()
    st.markdown("### 🔍 Fonti Dati Consigliate")
    st.write("👉 [Dati xG su FBRef](https://fbref.com)")
    st.write("👉 [Live & Formazioni Flashscore](https://www.flashscore.it)")
    
    st.divider()
    leagues = {
        "Top Europe": ["Serie A", "Premier League", "La Liga", "Bundesliga", "Ligue 1"],
        "Second Tier": ["Serie B", "Championship", "Eredivisie", "Liga Portugal"],
        "Americas/Asia": ["MLS", "Brasileirao", "Saudi Pro League", "J1 League"],
        "Cups": ["Champions League", "Europa League", "Conference League"]
    }
    cat = st.selectbox("Area Geografica", list(leagues.keys()))
    league = st.selectbox("Campionato", leagues[cat])

# --- DASHBOARD PRINCIPALE ---
st.title("⚽ Betting Engine Elite v3.5")
st.caption("Advanced Poisson Model + AI Context Analysis")

# INPUT DATI
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.header("🏠 Casa")
    h_name = st.text_input("Team", "Inter", key="h1")
    h_gf = st.number_input("Media Gol Fatti", 1.8, step=0.1)
    h_xg = st.number_input("Media xG (da FBRef)", 1.9, step=0.1)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.header("🚌 Ospite")
    a_name = st.text_input("Team", "Milan", key="a1")
    a_gf = st.number_input("Media Gol Fatti ", 1.4, step=0.1)
    a_xg = st.number_input("Media xG (da FBRef) ", 1.3, step=0.1)
    st.markdown('</div>', unsafe_allow_html=True)

# MODULO IMPREVISTI (VALORE AGGIUNTO)
st.divider()
st.subheader("⚠️ Fattori Esterni (Imprevisti)")
c_i1, c_i2, c_i3 = st.columns(3)
with c_i1:
    injury = st.select_slider("Assenze Chiave", ["Nessuna", "1-2 Player", "Critiche"])
with c_i2:
    stress = st.select_slider("Stanchezza (Coppe)", ["Riposati", "Media", "Overload"])
with c_i3:
    weather = st.selectbox("Meteo/Campo", ["Ottimo", "Pioggia/Fango", "Vento Forte"])

# CALCOLO E OUTPUT
if st.button("🔥 GENERA PRONOSTICO DEFINITIVO"):
    if not gemini_key:
        st.error("Inserisci la chiave API!")
    else:
        # Algoritmo di Poisson con correzione xG
        exp_h = (h_gf + h_xg) / 2
        exp_a = (a_gf + a_xg) / 2
        
        # Correzione Imprevisti
        if injury == "Critiche": exp_h *= 0.85
        if stress == "Overload": exp_a *= 0.90
        
        p_h = sum([poisson.pmf(i, exp_h) * sum([poisson.pmf(j, exp_a) for j in range(i)]) for i in range(1, 10)]) * 100
        p_d = sum([poisson.pmf(i, exp_h) * poisson.pmf(i, exp_a) for i in range(10)]) * 100
        p_a = 100 - p_h - p_d

        # Display Risultati
        st.markdown("### 📈 Probabilità Statistiche")
        r1, r2, r3 = st.columns(3)
        r1.metric("1 (Casa)", f"{p_h:.1f}%")
        r2.metric("X (Pareggio)", f"{p_d:.1f}%")
        r3.metric("2 (Ospite)", f"{p_a:.1f}%")

        # INTEGRAZIONE IA
        with st.spinner("Analisi IA in corso..."):
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"""
                Agisci come un analista di scommesse professionista. 
                Match: {h_name} vs {a_name} ({league}). 
                Dati statistici: {h_name} xG {h_xg}, {a_name} xG {a_xg}. 
                Imprevisti: Assenze {injury}, Stanchezza {stress}, Meteo {weather}.
                Probabilità Poisson: 1={p_h:.1f}%, X={p_d:.1f}%, 2={p_a:.1f}%.
                
                Fornisci:
                1. Analisi del valore (Value Bet) confrontando queste % con una quota ipotetica.
                2. Pronostico Safe e Pronostico High Risk.
                3. Consiglio sulla gestione dello Stake (1/10).
                Sii estremamente cinico e basati solo sui dati.
                """
                response = model.generate_content(prompt)
                st.subheader("🤖 Intelligence AI Report")
                st.info(response.text)
            except Exception as e:
                st.error(f"Errore IA: {e}")
