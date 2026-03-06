# ⚡ Quantum Football Analytics v9.0

Tool di analisi predittiva per partite di calcio con modello **Poisson + Dixon-Coles + Monte Carlo 50K**.

---

## 🔧 Fix v9.0 rispetto a v8

| Problema v8 | Soluzione v9 |
|---|---|
| Cache senza chiave squadra → stesse stats | `@st.cache_data` con parametri `(team, league, season)` espliciti |
| Fallback silenzioso su medie statiche | Debug panel mostra quale API ha risposto |
| Session state non resettato correttamente | `reset_all()` garantito prima di ogni nuova ricerca |
| Rate limit non gestito | Warning visibile + fallback trasparente |
| xG sempre uguale per stessa lega | Understat sovrascrive xG stimato dove disponibile |

---

## 🚀 Installazione

```bash
git clone https://github.com/TUO_USERNAME/quantum-football-v9
cd quantum-football-v9
pip install -r requirements.txt
streamlit run app.py
```

---

## 🔑 API Keys necessarie

| API | Tier | Link |
|---|---|---|
| **football-data.org** | Free (10 req/min) | https://www.football-data.org/ |
| **The Odds API** | Free (500 req/mese) | https://the-odds-api.com/ |
| **API-Football** | Free (100 req/giorno) | https://api-sports.io/ |

Understat, ClubElo e Transfermarkt non richiedono chiavi.

---

## 📁 Struttura progetto

```
quantum-football-v9/
├── app.py             # Interfaccia Streamlit (UI, fetch, cache)
├── engine.py          # Core matematico (Poisson, Dixon-Coles, Monte Carlo)
├── requirements.txt   # Dipendenze Python
└── README.md
```

---

## 🏗️ Architettura

```
app.py
  └─ render_sidebar()      → API keys, parametri
  └─ render_input()        → Selezione partita, trigger fetch
      └─ fetch_all_data()  → Fetch PARALLELO (5 threads)
          ├─ cached_fd_stats(fd_key, league, team, is_home, season)   ← CACHE PER SQUADRA
          ├─ cached_af_stats(af_key, league, team, season)            ← CACHE PER SQUADRA
          ├─ cached_understat(league, team, season)                   ← CACHE PER SQUADRA
          ├─ cached_clubelo(team)                                     ← CACHE PER SQUADRA
          ├─ cached_injuries(team)                                    ← CACHE PER SQUADRA
          └─ cached_odds(odds_key, league, home, away)                ← CACHE PER MATCH
  └─ AdvancedEngine.compute()
      ├─ Lambda base (xG 70% + GF 30%)
      ├─ Aggiustamento difesa avversaria
      ├─ Regressione verso media lega
      ├─ H2H storico (pesi 1.0/0.7/0.4)
      ├─ Infortuni (Transfermarkt)
      ├─ Elo (ClubElo)
      ├─ Motivazione / Stanchezza / Pressione
      └─ Monte Carlo 50K (CI 90%, bootstrap 20 blocchi)
  └─ render_results()      → 10 tab: mercati, H2H, modello, safety, ROI
```

---

## 📊 Mercati coperti (30+)

1X2, Doppia Chance, DNB, Over/Under (0.5→4.5), Primo/Secondo Tempo, BTTS, BTTS per tempo, Multigoal, Gol Casa/Trasferta, Gol Esatti, HT/FT (9 combo), Handicap Europeo, Winning Margin, Angoli O/U 9.5, Cartellini O/U 3.5, Combo automatiche (20), Top 10 risultati esatti

---

## ⚙️ Deploy su Streamlit Cloud

1. Crea repo GitHub con questi 3 file
2. Vai su https://share.streamlit.io
3. `Main file path: app.py`
4. Inserisci le API keys nei **Secrets** di Streamlit:
   ```toml
   # .streamlit/secrets.toml (NON committare questo file)
   fd_key = "tua_chiave_football_data"
   af_key = "tua_chiave_api_football"
   odds_key = "tua_chiave_odds_api"
   ```

---

## 🔍 Debug Mode

Attiva "Modalità Debug" nella sidebar per vedere:
- Quale API ha risposto per ogni dato
- Quante partite sono state caricate
- Badge colorati: ✓ Verde = dato reale, ~ Giallo = stima, ⚠ Rosso = errore/fallback
