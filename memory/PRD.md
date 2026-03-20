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

## What's Been Implemented (v1.0 — Feb 2026)
### Backend
- `POST /api/analyze` — Full Claude AI analysis with 4-phase methodology: data collection, Poisson λ calculation, probability markets, analyst report
- `GET /api/analyses` — Returns last 20 analyses from MongoDB
- JSON extraction with robust cleanup (handles markdown, backticks)
- Full error handling with Italian error messages

### Frontend
- **MatchForm** — Structured form with react-hook-form validation, league dropdown, history sidebar
- **LoadingState** — Terminal-style progress animation with 8 AI steps
- **AnalysisResults** — Complete results dashboard:
  - Match header (confidence score + data quality badge)
  - Context section (forma recente, H2H, infortuni, key factor, motivazione, stanchezza, arbitro)
  - Poisson section (λ Casa, λ Trasferta, λ Corner + expandable reasoning)
  - Markets section: 1X2, Over/Under 1.5/2.5/3.5, Multigoal home/away, Corners Over/Under
  - Exact scores grid (top 8, TOP badge on most likely)
  - Analyst report (terminal monospaced style)
  - Data gaps section (when AI lacks certain data)
- **History sidebar** — Last 10 analyses with clickable cards

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
