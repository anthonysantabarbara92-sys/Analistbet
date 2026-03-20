# Analizzatore Calcistico Pro — PRD

## Problem Statement
Football Analyzer App that acts as a professional bookmaker AI (20 anni di esperienza). Analyzes football matches with quantitative rigor using Poisson distribution, real statistical analysis, and professional analyst reports.

## Architecture
- **Frontend**: React 19 + Tailwind CSS (dark theme, JetBrains Mono / IBM Plex Sans fonts)
- **Backend**: FastAPI + Motor (async MongoDB)
- **AI**: Claude claude-4-sonnet-20250514 via emergentintegrations (EMERGENT_LLM_KEY)
- **Database**: MongoDB (collection: football_analyses)

## User Personas
- Professional football trader / bookmaker
- Italian-speaking sports analyst
- Betting market researcher

## Core Requirements (Static)
- Italian language interface
- Dark professional "trading desk" aesthetic
- Structured form input (no free text)
- Full Poisson distribution analysis (4 phases)
- No login required
- JSON output matching exact schema from problem statement

## What's Been Implemented (v2.0 — Feb 2026)
### Backend
- `POST /api/analyze` — **8 ricerche web DuckDuckGo (ddgs)** + Claude AI analisi 4 fasi Poisson
- `GET /api/analyses` — Returns last 20 analyses from MongoDB
- `gather_football_data()` — Ricerca web in tempo reale (ddgs v9.11.4): risultati recenti, infortuni, H2H, classifica
- `normalize_markets()` — Normalizzazione matematica automatica di tutti i mercati
- JSON extraction with robust cleanup (handles markdown, backticks)
- `web_search_used` e `web_queries_found` fields in response

### Frontend
- **MatchForm** — Form strutturato con react-hook-form, dropdown campionato, storico sidebar
- **LoadingState** — Terminal con 8 step reali (search web + calc Poisson + report)
- **AnalysisResults** — Dashboard completa:
  - Header con **badge Web Search (X/8)**, confidence, qualità dati
  - **Pulsante Ricalcola** per ri-eseguire con dati freschi
  - 1X2 con **quote decimali europee** (1/probabilità)
  - Over/Under con 5 colonne: Linea, Over%, Quota, Under%, Quota
  - Corners con 5 colonne + quote
  - Exact scores con quote decimali per ogni risultato
  - Context section, Poisson reasoning, Multigoal, Analyst Report, Data Gaps
- **History sidebar** — Last 10 analisi con card cliccabili

## AI Methodology (Claude System Prompt)
- FASE 1: Data collection (knowledge base — campionati europei)
- FASE 2: Poisson λ calculation with documented adjustments
- FASE 3: Bivariate Poisson probabilities (1X2, O/U, Multigoal, Corners, Exact Scores)
- FASE 4: 220-260 word professional analyst report

## Prioritized Backlog

### P0 (Must Have - DONE)
- [x] Match input form
- [x] Claude AI integration
- [x] Full Poisson analysis
- [x] All betting markets (1X2, O/U, Multigoal, Corners)
- [x] Exact scores grid
- [x] Analyst report
- [x] Analysis history

### P1 (Should Have)
- [ ] Real-time web search augmentation (Tavily/Serper API) for live injury data
- [ ] Comparison view (two analyses side by side)
- [ ] Export analysis as PDF
- [ ] Favorite/pin analyses

### P2 (Nice to Have)
- [ ] Multiple language support (EN/IT toggle)
- [ ] Odds comparison vs bookmakers (integrate odds API)
- [ ] Email/share analysis link
- [ ] Historical accuracy tracking

## Next Tasks
1. Add real-time web search for live injury/lineup data
2. PDF export functionality
3. Comparison between two match analyses
