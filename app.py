“””
╔══════════════════════════════════════════════════════════════════════════════╗
║   QUANTUM FOOTBALL ANALYTICS ENGINE  v4.0                                   ║
║   Bloomberg Terminal — Senior Quant Trading System                          ║
║   MERCATI: 1X2 · Risultati Esatti · OU · BTTS · Multigoal ·               ║
║            Asian/Euro Handicap · HT/FT · Cartellini · Angoli ·             ║
║            Anytime Goalscorer · AI Cross-Check                              ║
║   COMPETIZIONI: 14 paesi · 60+ leghe e coppe                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
“””

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

warnings.filterwarnings(“ignore”)

# ══════════════════════════════════════════════════════════════════════════════

# COMPETITIONS DATABASE  — 14 paesi, 60+ competizioni

# ══════════════════════════════════════════════════════════════════════════════

COMPETITIONS: Dict[str, List[str]] = {
“🇮🇹 Italia”: [
“Serie A”, “Serie B”, “Serie C — Girone A”, “Serie C — Girone B”,
“Serie C — Girone C”, “Coppa Italia”, “Supercoppa Italiana”,
],
“🇩🇪 Germania”: [
“Bundesliga”, “2. Bundesliga”, “3. Liga”,
“DFB-Pokal”, “DFL-Supercup”,
],
“🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inghilterra”: [
“Premier League”, “EFL Championship”, “EFL League One”, “EFL League Two”,
“FA Cup”, “EFL Cup (Carabao Cup)”, “FA Community Shield”,
],
“🇫🇷 Francia”: [
“Ligue 1”, “Ligue 2”, “National (3° livello)”,
“Coupe de France”, “Trophée des Champions”,
],
“🇪🇸 Spagna”: [
“La Liga”, “LaLiga Hypermotion (Segunda División)”,
“Primera Federación (3° livello)”,
“Copa del Rey”, “Supercopa de España”,
],
“🇵🇹 Portogallo”: [
“Liga Portugal (Primeira Liga)”, “Liga Portugal 2 (Segunda Liga)”,
“Taça de Portugal”, “Taça da Liga”,
],
“🇳🇱 Olanda”: [
“Eredivisie”, “Eerste Divisie (Keuken Kampioen Divisie)”,
“Tweede Divisie”, “KNVB Beker”,
],
“🇧🇪 Belgio”: [
“Pro League (First Division A)”, “Challenger Pro League (Division B)”,
“Coupe de Belgique / Beker van België”,
],
“🇸🇪 Svezia”: [
“Allsvenskan (Div. 1)”, “Superettan (Div. 2)”, “Ettan Fotboll (Div. 3)”,
“Division 2 (4° livello)”, “Svenska Cupen”,
],
“🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scozia”: [
“Scottish Premiership”, “Scottish Championship”, “Scottish League One”,
“Scottish League Two”, “Scottish Cup”, “Scottish League Cup”,
],
“🇯🇵 Giappone”: [
“J1 League”, “J2 League”, “J3 League”,
“Coppa dell’Imperatore (Emperor’s Cup)”, “J.League Cup (YBC Levain Cup)”,
“J.League Championship”,
],
“🇳🇴 Norvegia”: [
“Eliteserien (Div. 1)”, “1. divisjon / OBOS-ligaen (Div. 2)”,
“2. divisjon (Div. 3)”, “Norgesmesterskapet (NM Cup)”,
],
“🇫🇮 Finlandia”: [
“Veikkausliiga / Eliteserien (Div. 1)”, “Ykkönen / 1. divisjon (Div. 2)”,
“Kakkonen (Div. 3)”, “Suomen Cup / Norgesmesterskapet”,
],
“🇮🇸 Islanda”: [
“Úrvalsdeild karla / Besta deild (Div. 1)”,
“1. deild karla / Lengjudeildin (Div. 2)”,
“2. deild (Div. 3)”, “Íslandsbikar / Bikar karla (Coppa)”,
],
}

# Flat list for Gemini context

ALL_COMPETITIONS_FLAT = [
comp for comps in COMPETITIONS.values() for comp in comps
]

# ══════════════════════════════════════════════════════════════════════════════

# BLOOMBERG CSS

# ══════════════════════════════════════════════════════════════════════════════

BLOOMBERG_CSS = “””

<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&display=swap');
:root {
  --bg0:#0a0a0f;--bg1:#0f0f1a;--bg2:#12121e;--bg3:#18182a;
  --br1:#1e1e35;--br2:#2a2a50;
  --org:#ff6600;--grn:#00ff88;--red:#ff3355;
  --blu:#00aaff;--yel:#ffcc00;--pur:#9933ff;--cyn:#00e5ff;
  --t1:#e8e8f0;--t2:#8888aa;--t3:#444466;
  --fm:'IBM Plex Mono',monospace;
}
html,body,[class*="css"]{font-family:var(--fm)!important;background:var(--bg0)!important;color:var(--t1)!important;}
.stApp{background:var(--bg0)!important;background-image:
  radial-gradient(ellipse at 15% 15%,rgba(0,170,255,.04) 0%,transparent 50%),
  radial-gradient(ellipse at 85% 85%,rgba(255,102,0,.04) 0%,transparent 50%);}
[data-testid="stSidebar"]{background:var(--bg1)!important;border-right:1px solid var(--br1)!important;}
[data-testid="stSidebar"] input,[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] .stSelectbox>div>div
{background:var(--bg2)!important;border:1px solid var(--br2)!important;
 color:var(--t1)!important;font-family:var(--fm)!important;border-radius:4px!important;}
/* HEADER */
.bh{background:linear-gradient(135deg,var(--bg1),#0d0d20);border:1px solid var(--br1);
  border-left:3px solid var(--org);border-radius:6px;padding:18px 26px;
  margin-bottom:18px;position:relative;overflow:hidden;}
.bh::before{content:'';position:absolute;top:0;right:0;width:260px;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,102,0,.04));}
.bh h1{font-family:var(--fm)!important;font-size:1.5rem!important;font-weight:700!important;
  color:var(--org)!important;letter-spacing:.08em!important;margin:0!important;text-transform:uppercase;}
.bh .sub{font-size:.62rem;color:var(--t2);letter-spacing:.15em;margin-top:4px;text-transform:uppercase;}
.bh .comp-badge{display:inline-block;margin-top:8px;padding:3px 12px;background:rgba(255,102,0,.1);
  border:1px solid rgba(255,102,0,.3);border-radius:3px;font-size:.65rem;
  color:var(--org);letter-spacing:.1em;text-transform:uppercase;}
/* METRIC GRID */
.mg{display:grid;gap:10px;margin:12px 0;}
.mg4{grid-template-columns:repeat(4,1fr);}
.mg3{grid-template-columns:repeat(3,1fr);}
.mg2{grid-template-columns:repeat(2,1fr);}
.mc{background:var(--bg2);border:1px solid var(--br1);border-radius:6px;
  padding:13px 17px;position:relative;transition:border-color .2s;}
.mc:hover{border-color:var(--br2);}
.mc .lbl{font-size:.57rem;color:var(--t2);letter-spacing:.18em;text-transform:uppercase;margin-bottom:4px;}
.mc .val{font-size:1.4rem;font-weight:700;line-height:1;}
.mc .dlt{font-size:.61rem;margin-top:3px;color:var(--t2);}
.mc .ab{position:absolute;top:0;left:0;width:3px;height:100%;border-radius:6px 0 0 6px;}
.mc.org .val{color:var(--org);}.mc.org .ab{background:var(--org);}
.mc.grn .val{color:var(--grn);}.mc.grn .ab{background:var(--grn);}
.mc.red .val{color:var(--red);}.mc.red .ab{background:var(--red);}
.mc.blu .val{color:var(--blu);}.mc.blu .ab{background:var(--blu);}
.mc.yel .val{color:var(--yel);}.mc.yel .ab{background:var(--yel);}
.mc.pur .val{color:var(--pur);}.mc.pur .ab{background:var(--pur);}
.mc.cyn .val{color:var(--cyn);}.mc.cyn .ab{background:var(--cyn);}
/* SECTION HEADER */
.sh{display:flex;align-items:center;gap:10px;margin:18px 0 9px;
  padding-bottom:7px;border-bottom:1px solid var(--br1);}
.sh .icon{color:var(--org);font-size:.9rem;}
.sh h3{font-family:var(--fm)!important;font-size:.7rem!important;font-weight:600!important;
  color:var(--t2)!important;letter-spacing:.2em!important;text-transform:uppercase!important;margin:0!important;}
/* BADGES */
.vbadge{display:inline-block;padding:3px 9px;border-radius:3px;
  font-size:.63rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;}
.vbadge.pos{background:rgba(0,255,136,.13);color:var(--grn);border:1px solid rgba(0,255,136,.3);}
.vbadge.neg{background:rgba(255,51,85,.1);color:var(--red);border:1px solid rgba(255,51,85,.22);}
.vbadge.neu{background:rgba(255,204,0,.1);color:var(--yel);border:1px solid rgba(255,204,0,.22);}
.vbadge.blu{background:rgba(0,170,255,.1);color:var(--blu);border:1px solid rgba(0,170,255,.22);}
/* SCORE CARD — exact results */
.score-card{background:var(--bg2);border:1px solid var(--br1);border-radius:6px;
  padding:12px 16px;margin-bottom:8px;transition:border-color .18s;position:relative;}
.score-card:hover{border-color:var(--br2);}
.score-card.value-hit{border-color:rgba(0,255,136,.35)!important;
  background:linear-gradient(135deg,var(--bg2),rgba(0,255,136,.03));}
.score-card .s-label{font-size:.58rem;color:var(--t2);letter-spacing:.18em;text-transform:uppercase;}
.score-card .s-score{font-size:1.3rem;font-weight:700;color:var(--org);}
.score-card .s-prob{font-size:.9rem;font-weight:600;color:var(--t1);}
.score-card .s-fair{font-size:.72rem;color:var(--t2);}
.score-card .s-edge{font-size:.85rem;font-weight:700;}
.score-card .s-edge.pos{color:var(--grn);}
.score-card .s-edge.neg{color:var(--red);}
/* INPUTS */
.stNumberInput>div>div>input,.stTextInput>div>div>input,.stTextArea>div>div>textarea
{background:var(--bg2)!important;border:1px solid var(--br2)!important;
 color:var(--t1)!important;font-family:var(--fm)!important;border-radius:4px!important;}
.stNumberInput>div>div>input:focus,.stTextInput>div>div>input:focus,
.stTextArea>div>div>textarea:focus
{border-color:var(--org)!important;box-shadow:0 0 0 1px rgba(255,102,0,.3)!important;}
.stButton>button{background:transparent!important;border:1px solid var(--org)!important;
  color:var(--org)!important;font-family:var(--fm)!important;font-size:.7rem!important;
  font-weight:600!important;letter-spacing:.12em!important;text-transform:uppercase!important;
  border-radius:4px!important;transition:all .2s!important;}
.stButton>button:hover{background:rgba(255,102,0,.1)!important;
  box-shadow:0 0 14px rgba(255,102,0,.2)!important;}
/* TABS */
.stTabs [data-baseweb="tab-list"]{background:var(--bg1)!important;
  border-bottom:1px solid var(--br1)!important;gap:0!important;}
.stTabs [data-baseweb="tab"]{font-family:var(--fm)!important;font-size:.64rem!important;
  font-weight:500!important;letter-spacing:.09em!important;color:var(--t2)!important;
  border-bottom:2px solid transparent!important;background:transparent!important;
  text-transform:uppercase!important;padding:10px 14px!important;}
.stTabs [aria-selected="true"]{color:var(--org)!important;
  border-bottom:2px solid var(--org)!important;}
/* EXPANDER */
.streamlit-expanderHeader{background:var(--bg2)!important;border:1px solid var(--br1)!important;
  border-radius:4px!important;font-family:var(--fm)!important;font-size:.68rem!important;
  color:var(--t2)!important;letter-spacing:.1em!important;}
.streamlit-expanderContent{background:var(--bg2)!important;border:1px solid var(--br1)!important;}
.stSelectbox label,.stNumberInput label,.stTextInput label,.stTextArea label,
.stSlider label,.stCheckbox label
{font-family:var(--fm)!important;font-size:.63rem!important;color:var(--t2)!important;
 letter-spacing:.12em!important;text-transform:uppercase!important;}
.stSelectbox>div>div{background:var(--bg2)!important;border:1px solid var(--br2)!important;
  color:var(--t1)!important;font-family:var(--fm)!important;border-radius:4px!important;}
/* VERDICT BOX */
.vbox{background:linear-gradient(135deg,var(--bg2),var(--bg1));border:1px solid var(--br1);
  border-radius:8px;padding:20px;margin:12px 0;position:relative;overflow:hidden;}
.vbox::after{content:'';position:absolute;bottom:0;right:0;width:80px;height:80px;
  border-radius:50%;filter:blur(34px);opacity:.13;}
.vbox.pos::after{background:var(--grn);}.vbox.neg::after{background:var(--red);}
/* MARKET ROW */
.market-row{background:var(--bg2);border:1px solid var(--br1);border-radius:6px;
  padding:13px 17px;margin-bottom:8px;transition:border-color .15s;}
.market-row:hover{border-color:var(--br2);}
hr{border-color:var(--br1)!important;}
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:var(--bg0);}
::-webkit-scrollbar-thumb{background:var(--br2);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:var(--org);}
#MainMenu,footer,header,.stDeployButton{visibility:hidden!important;display:none!important;}
</style>

“””

# ══════════════════════════════════════════════════════════════════════════════

# DATA CLASSES

# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamStats:
name:          str   = “Team”
gf_avg:        float = 1.40
ga_avg:        float = 1.10
xg_avg:        float = 1.35
xga_avg:       float = 1.15
corners_avg:   float = 5.50
cards_avg:     float = 1.80
shots_on_avg:  float = 4.50
weight_recent: float = 1.00

@dataclass
class PlayerStats:
name:        str   = “Player”
goals_pg:    float = 0.30
minutes_avg: float = 80.0
team:        str   = “home”

# ══════════════════════════════════════════════════════════════════════════════

# CLASS 1 — QUANTUM ENGINE

# ══════════════════════════════════════════════════════════════════════════════

class QuantumEngine:
N = 12   # matrix dimension (0–11 goals)

```
def __init__(self, home: TeamStats, away: TeamStats):
    self.home  = home
    self.away  = away
    self.lam_h = self._lam(home.gf_avg, home.xg_avg,
                            away.ga_avg, away.xga_avg, home.weight_recent)
    self.lam_a = self._lam(away.gf_avg, away.xg_avg,
                            home.ga_avg, home.xga_avg, away.weight_recent)
    self._mat: Optional[np.ndarray] = None

@staticmethod
def _lam(gf, xg, ga_opp, xga_opp, w=1.0) -> float:
    att = gf * 0.40 + xg * 0.60
    dfn = (ga_opp * 0.40 + xga_opp * 0.60) ** 0.5
    return max(att * dfn * w, 0.05)

def matrix(self) -> np.ndarray:
    if self._mat is None:
        n = self.N
        m = np.outer(
            [poisson.pmf(i, self.lam_h) for i in range(n)],
            [poisson.pmf(j, self.lam_a) for j in range(n)]
        )
        self._mat = m / m.sum()
    return self._mat

# ── 1X2
def p_1x2(self):
    m = self.matrix()
    I, J = np.mgrid[0:self.N, 0:self.N]
    ph = float(m[I > J].sum())
    pd = float(m[I == J].sum())
    pa = float(m[I < J].sum())
    t  = ph + pd + pa
    return ph/t, pd/t, pa/t

# ── Over/Under
def p_ou(self, line):
    m = self.matrix()
    I, J = np.mgrid[0:self.N, 0:self.N]
    ov = float(m[(I + J) > line].sum())
    return ov, 1.0 - ov

# ── BTTS
def p_btts(self):
    m   = self.matrix()
    yes = float(m[1:, 1:].sum())
    return yes, 1.0 - yes

# ── Multigoal
def p_multigoal(self):
    m = self.matrix()
    I, J = np.mgrid[0:self.N, 0:self.N]
    T = I + J
    return {
        "0-1":  float(m[T <= 1].sum()),
        "1-2":  float(m[(T >= 1) & (T <= 2)].sum()),
        "2-3":  float(m[(T >= 2) & (T <= 3)].sum()),
        "3-4":  float(m[(T >= 3) & (T <= 4)].sum()),
        "4-5":  float(m[(T >= 4) & (T <= 5)].sum()),
        "5+":   float(m[T >= 5].sum()),
    }

# ── Exact Scores  — NUOVO in v4.0
def top_exact_scores(self, top_n: int = 20) -> List[Dict]:
    """
    Estrae i top_n risultati esatti con prob %, fair odd e categoria.
    Categoria: HOME (home vince), DRAW, AWAY (away vince).
    """
    m = self.matrix()
    scores = []
    for i in range(self.N):
        for j in range(self.N):
            prob = float(m[i, j])
            if prob < 1e-6:
                continue
            cat = "HOME" if i > j else ("DRAW" if i == j else "AWAY")
            scores.append({
                "score":    f"{i}-{j}",
                "h_goals":  i,
                "a_goals":  j,
                "prob":     prob,
                "prob_pct": round(prob * 100, 4),
                "fair_odd": round(1.0 / max(prob, 1e-6), 2),
                "category": cat,
            })
    scores.sort(key=lambda x: -x["prob"])
    return scores[:top_n]

def all_exact_scores_dict(self) -> Dict[str, float]:
    """Returns {score_str: prob} for every cell in matrix."""
    m = self.matrix()
    return {f"{i}-{j}": float(m[i, j])
            for i in range(self.N) for j in range(self.N)}

# ── Asian Handicap
def p_asian_handicap(self, handicap: float):
    m = self.matrix()
    I, J = np.mgrid[0:self.N, 0:self.N]
    diff = (I - J).astype(float)
    def _c(h):
        ph = float(m[diff > h].sum())
        pa = float(m[diff < h].sum())
        pp = float(m[diff == h].sum())
        return ph, pa, pp
    frac = abs(handicap % 1)
    if frac in (0.25, 0.75):
        sign = 1 if handicap >= 0 else -1
        h1   = handicap - sign * 0.25
        h2   = handicap + sign * 0.25
        ph1, pa1, pp1 = _c(h1)
        ph2, pa2, pp2 = _c(h2)
        phN = (ph1 + pp1*0.5 + ph2 + pp2*0.5) / 2
        paN = (pa1 + pp1*0.5 + pa2 + pp2*0.5) / 2
        return {"home_cover": round(phN, 4), "away_cover": round(paN, 4),
                "push": 0.0, "type": "quarter"}
    ph, pa, pp = _c(handicap)
    return {"home_cover": round(ph, 4), "away_cover": round(pa, 4),
            "push": round(pp, 4), "type": "full"}

# ── European Handicap
def p_euro_handicap(self, hcap: int):
    m  = self.matrix()
    I, J = np.mgrid[0:self.N, 0:self.N]
    d  = (I - J) + hcap
    ph = float(m[d > 0].sum())
    pd = float(m[d == 0].sum())
    pa = float(m[d < 0].sum())
    t  = ph + pd + pa
    return ph/t, pd/t, pa/t

# ── HT/FT
def p_ht_ft(self):
    def _small(lh, la, n=8):
        m = np.outer([poisson.pmf(i, lh) for i in range(n)],
                     [poisson.pmf(j, la) for j in range(n)])
        return m / m.sum()
    lhh = self.lam_h * 0.43; lah = self.lam_a * 0.43
    lh2 = self.lam_h - lhh;  la2 = self.lam_a - lah
    ht  = _small(lhh, lah)
    sh  = _small(lh2, la2)
    I, J = np.mgrid[0:8, 0:8]
    hth = float(ht[I>J].sum()); htd = float(ht[I==J].sum()); hta = float(ht[I<J].sum())
    shh = float(sh[I>J].sum()); shd = float(sh[I==J].sum()); sha = float(sh[I<J].sum())
    combos = {
        "H/H":(hth, shh+shd*.6), "H/D":(hth, shd*.25), "H/A":(hth, sha*.30),
        "D/H":(htd, shh),        "D/D":(htd, shd*.70),  "D/A":(htd, sha),
        "A/H":(hta, shh*.30),    "A/D":(hta, shd*.25),  "A/A":(hta, sha+shd*.6),
    }
    raw = {k: v[0]*v[1] for k, v in combos.items()}
    tot = sum(raw.values()) or 1
    return {k: round(v/tot, 5) for k, v in raw.items()}

# ── Cards (Poisson univariata)
@staticmethod
def p_cards_ou(h_avg, a_avg, line):
    lam = h_avg + a_avg
    ov  = float(1 - poisson.cdf(int(line), lam))
    return ov, 1.0 - ov

@staticmethod
def p_cards_range(h_avg, a_avg):
    lam = h_avg + a_avg
    return {
        "0-2": float(poisson.cdf(2, lam)),
        "3-4": float(poisson.pmf(3, lam) + poisson.pmf(4, lam)),
        "5-6": float(poisson.pmf(5, lam) + poisson.pmf(6, lam)),
        "7+":  float(1 - poisson.cdf(6, lam)),
    }

# ── Corners
@staticmethod
def p_corners_ou(h_avg, a_avg, line):
    lam = h_avg + a_avg
    ov  = float(1 - poisson.cdf(int(line), lam))
    return ov, 1.0 - ov

# ── Anytime Goalscorer
@staticmethod
def p_goalscorer(goals_pg, minutes_avg=80.0, match_min=90.0):
    lam = goals_pg * (minutes_avg / match_min)
    any_ = float(1 - poisson.pmf(0, lam))
    return {
        "lambda":    round(lam, 4),
        "anytime":   round(any_, 4),
        "brace":     round(float(1 - poisson.cdf(1, lam)), 4),
        "hat_trick": round(float(1 - poisson.cdf(2, lam)), 4),
        "fair_odd":  round(1 / max(any_, 1e-4), 3),
    }

# ── Shot quality
@staticmethod
def shot_quality(xg, sot):
    p  = xg / max(sot, 0.1)
    qi = min(p * 10, 10)
    lv = "ELITE" if qi>7 else ("HIGH" if qi>5 else ("MED" if qi>3 else "LOW"))
    return {"precision": round(p,3), "qi": round(qi,2), "level": lv}

# ── Monte Carlo
def monte_carlo(self, n=10_000):
    rng = np.random.default_rng(42)
    hg  = rng.poisson(self.lam_h, n)
    ag  = rng.poisson(self.lam_a, n)
    tot = hg + ag
    from collections import Counter
    sc  = Counter(zip(hg.tolist(), ag.tolist()))
    top = sorted(sc.items(), key=lambda x: -x[1])[:12]
    return {
        "hw":float(np.mean(hg>ag)), "dr":float(np.mean(hg==ag)), "aw":float(np.mean(hg<ag)),
        "ov15":float(np.mean(tot>1.5)), "ov25":float(np.mean(tot>2.5)),
        "ov35":float(np.mean(tot>3.5)), "ov45":float(np.mean(tot>4.5)),
        "btts":float(np.mean((hg>0)&(ag>0))),
        "mu":float(np.mean(tot)), "sig":float(np.std(tot)),
        "ci_lo":float(np.percentile(tot,2.5)), "ci_hi":float(np.percentile(tot,97.5)),
        "hg_dist":np.bincount(hg,minlength=10)[:10].tolist(),
        "ag_dist":np.bincount(ag,minlength=10)[:10].tolist(),
        "tot_dist":np.bincount(tot,minlength=12)[:12].tolist(),
        "hg_raw":hg.tolist(), "ag_raw":ag.tolist(),
        "top_scores":[(f"{h}-{a}", round(c/n*100,2)) for (h,a),c in top],
    }
```

# ══════════════════════════════════════════════════════════════════════════════

# CLASS 2 — FINANCE MANAGER

# ══════════════════════════════════════════════════════════════════════════════

class FinanceManager:
KF = 0.20

```
@staticmethod
def fair(p): return round(1.0/max(p,1e-4), 3)
@staticmethod
def edge(p, odd): return round(p*odd - 1.0, 5)

@classmethod
def kelly(cls, p, odd, br):
    e = cls.edge(p, odd)
    if e <= 0: return {"stake":0.,"pct":0.,"edge":e,"ev":0.,"ok":False}
    fk = (e/(odd-1))*cls.KF
    st = round(fk*br, 2)
    return {"stake":st,"pct":round(fk*100,3),"edge":e,"ev":round(e*st,2),"ok":True}

@classmethod
def analyse(cls, label, p, bk, br):
    fair = cls.fair(p)
    e    = cls.edge(p, bk)
    kl   = cls.kelly(p, bk, br)
    val  = bk > fair
    sig  = ("🟢 STRONG" if (val and e>0.05) else
            ("🟡 WATCH"  if (val and e>0.02) else "🔴 SKIP"))
    return {"market":label,"prob%":round(p*100,2),"fair":fair,"bk":bk,
            "edge%":round(e*100,2),"stake":kl["stake"],"stake%":kl["pct"],
            "ev":kl["ev"],"value":val,"signal":sig}
```

# ══════════════════════════════════════════════════════════════════════════════

# CLASS 3 — SMART PARSER (Gemini 2.0)

# ══════════════════════════════════════════════════════════════════════════════

class SmartParser:
“””
Gemini 2.0 Flash — extrae statistiche e quote da testo grezzo.
Supporta: SofaScore, FBRef, WhoScored, Transfermarkt, Oddsportal,
BetExplorer, Flashscore, SoccerStats, Sofascore, 365scores.
Competizioni supportate: tutte le 60+ leghe nel database.
“””

```
_COMP_LIST = "\n".join(f"  • {c}" for c in ALL_COMPETITIONS_FLAT)

STATS_PROMPT = f"""
```

Sei un esperto analista di football statistics e betting quantitativo.
Analizza il testo e restituisci SOLO JSON valido (zero testo extra, zero markdown, zero backtick).

Competizioni supportate dal sistema (per contesto):
{_COMP_LIST}

Schema target STATISTICHE:
{{
“home_team”: “”,
“away_team”: “”,
“competition”: “”,
“home_gf_avg”: null, “home_ga_avg”: null,
“home_xg_avg”: null, “home_xga_avg”: null,
“home_corners_avg”: null, “home_cards_avg”: null, “home_shots_on_avg”: null,
“home_weight_recent”: null,
“away_gf_avg”: null, “away_ga_avg”: null,
“away_xg_avg”: null, “away_xga_avg”: null,
“away_corners_avg”: null, “away_cards_avg”: null, “away_shots_on_avg”: null,
“away_weight_recent”: null,
“notes”: “”,
“players”: [
{{“name”:””,“team”:“home|away”,“goals_pg”:null,“minutes_avg”:null}}
]
}}

Regole di estrazione:

- Se trovi medie “ultimi 5 / last 5 / recent form”: applica weight_recent = 1.20
- xG = expected goals (NON goals per game)
- GF = goals for media per partita
- GA = goals against media per partita
- Mappa correttamente corners, cartellini (yellow+red), tiri in porta (shots on target)
- Se dato non disponibile: null
- Normalizza nomi squadre in italiano o inglese standard
  “””
  
  ODDS_PROMPT = f”””
  Sei un esperto di quote calcistiche. Analizza testo bookmaker e restituisci SOLO JSON valido.
  Competizioni supportate dal sistema:
  {_COMP_LIST}

Schema target QUOTE:
{{
“home”: null, “draw”: null, “away”: null,
“over15”: null, “under15”: null,
“over25”: null, “under25”: null,
“over35”: null, “under35”: null,
“over45”: null, “under45”: null,
“btts_y”: null, “btts_n”: null,
“mg_01”: null, “mg_12”: null, “mg_23”: null, “mg_34”: null,
“mg_45”: null, “mg_5p”: null,
“ah_minus25”: null, “ah_minus15”: null, “ah_minus10”: null, “ah_minus05”: null,
“ah_zero”: null, “ah_plus05”: null, “ah_plus10”: null, “ah_plus15”: null,
“eh_home_m1”: null, “eh_draw_m1”: null, “eh_away_m1”: null,
“eh_home_p1”: null, “eh_draw_p1”: null, “eh_away_p1”: null,
“htft_hh”: null, “htft_hd”: null, “htft_ha”: null,
“htft_dh”: null, “htft_dd”: null, “htft_da”: null,
“htft_ah”: null, “htft_ad”: null, “htft_aa”: null,
“cards_ou_main”: null, “cards_line”: null,
“corners_over”: null, “corners_line”: null,
“exact_scores”: {{}},
“anytime_goalscorer”: {{}}
}}

Per exact_scores usa: {{“0-0”: quota, “1-0”: quota, “0-1”: quota, …}}
Per anytime_goalscorer usa: {{“Nome Cognome”: quota}}
Includi TUTTI i risultati esatti presenti nel testo.
“””

```
QUALITATIVE_PROMPT = f"""
```

Sei un Senior Quant Trader sportivo con 15 anni di esperienza.
Hai a disposizione un sommario matematico e dei retroscena di un match.

Competizioni monitorate dal sistema:
{_COMP_LIST}

Il tuo compito: analizzare se i FATTORI QUALITATIVI confermano, indeboliscono
o ribaltano il segnale quantitativo.

Rispondi SEMPRE in italiano con ESATTAMENTE 5 bullet point nel formato:
• [CATEGORIA] — Impatto: [ALTO/MEDIO/BASSO] [POSITIVO/NEGATIVO/NEUTRO] — descrizione max 20 parole

Categorie disponibili:
INFORTUNI | FORMA RECENTE | METEO/CAMPO | MOTIVAZIONE | ARBITRO | TATTICA | STORICO PRECEDENTI | PRESSIONE CLASSIFICA | FATIGUE/SCHEDULE | MERCATO/RUMORS
“””

```
def __init__(self, api_key: str):
    self._key   = api_key
    self._model = None

def _init(self):
    if not self._model:
        try:
            genai.configure(api_key=self._key)
            self._model = genai.GenerativeModel("gemini-2.0-flash")
        except Exception as e:
            raise RuntimeError(f"Gemini init: {e}")

def _call(self, system: str, user: str) -> Dict:
    self._init()
    try:
        r    = self._model.generate_content(f"{system}\n\nTESTO INPUT:\n{user}")
        text = re.sub(r"```json\s*|\s*```", "", r.text).strip()
        return {"ok": True, "data": json.loads(text), "raw": text}
    except json.JSONDecodeError as e:
        raw = r.text if 'r' in dir() else ""
        return {"ok": False, "error": f"JSON parse: {e}", "raw": raw}
    except Exception as e:
        return {"ok": False, "error": str(e), "raw": ""}

def parse_stats(self, raw: str) -> Dict:
    return self._call(self.STATS_PROMPT, raw)

def parse_odds(self, raw: str) -> Dict:
    return self._call(self.ODDS_PROMPT, raw)

def qualitative(self, context: str, summary: str) -> str:
    self._init()
    try:
        prompt = (f"{self.QUALITATIVE_PROMPT}\n\n"
                  f"SOMMARIO MATEMATICO:\n{summary}\n\n"
                  f"RETROSCENA / CONTESTO:\n{context}")
        r = self._model.generate_content(prompt)
        return r.text
    except Exception as e:
        return f"⚠️ Analisi AI non disponibile: {e}"
```

# ══════════════════════════════════════════════════════════════════════════════

# PLOTLY HELPERS

# ══════════════════════════════════════════════════════════════════════════════

PL = dict(
paper_bgcolor=”#0a0a0f”, plot_bgcolor=”#0f0f1a”,
font=dict(family=“IBM Plex Mono”, color=”#8888aa”, size=10),
margin=dict(l=44, r=16, t=38, b=34),
legend=dict(bgcolor=“rgba(0,0,0,0)”, bordercolor=”#1e1e35”,
borderwidth=1, font=dict(size=9)),
xaxis=dict(gridcolor=”#1e1e35”, zerolinecolor=”#1e1e35”),
yaxis=dict(gridcolor=”#1e1e35”, zerolinecolor=”#1e1e35”),
)

def _ptitle(t): return dict(text=t, font=dict(color=”#ff6600”, size=11))

def heatmap_fig(mat, hn, an, top_scores=None):
n   = min(9, mat.shape[0])
mpc = mat[:n, :n] * 100
# Overlay: evidenzia top 3 scores
fig = go.Figure(go.Heatmap(
z=mpc, x=[str(i) for i in range(n)], y=[str(i) for i in range(n)],
colorscale=[[0,”#0a0a0f”],[.25,”#1a1a3e”],[.6,”#ff6600”],[1,”#ffcc00”]],
text=[[f”{mpc[i,j]:.2f}%” for j in range(n)] for i in range(n)],
texttemplate=”%{text}”, textfont=dict(size=8),
hovertemplate=f”{hn}=%{{y}} | {an}=%{{x}}<br>%{{z:.3f}}%<extra></extra>”,
colorbar=dict(tickfont=dict(size=8,color=”#8888aa”),outlinewidth=0),
))
fig.update_layout(**PL, title=_ptitle(“SCORE PROBABILITY MATRIX (%)”),
xaxis_title=an, yaxis_title=hn, height=420)
return fig

def bar1x2(ph, pd, pa, hn, an):
fig = go.Figure(go.Bar(
x=[hn,“DRAW”,an], y=[ph*100,pd*100,pa*100],
marker_color=[”#ff6600”,”#444466”,”#00aaff”],
text=[f”{v:.1f}%” for v in [ph*100,pd*100,pa*100]],
textposition=“outside”, textfont=dict(size=12,color=”#e8e8f0”), width=0.45,
))
fig.update_layout(**PL, title=_ptitle(“1X2 DISTRIBUTION”),
yaxis=dict(range=[0,max(ph,pd,pa)*140+5],gridcolor=”#1e1e35”,
ticksuffix=”%”,zerolinecolor=”#1e1e35”),
height=280, bargap=0.35)
return fig

def exact_scores_chart(top_scores: List[Dict], bk_odds_map: Dict[str,float]):
“”“Bar chart top exact scores con colore edge.”””
labels = [s[“score”] for s in top_scores[:15]]
probs  = [s[“prob_pct”] for s in top_scores[:15]]
fairs  = [s[“fair_odd”] for s in top_scores[:15]]
bk_odd = [bk_odds_map.get(s[“score”], 0) for s in top_scores[:15]]
edges  = [round((p/100)*bk - 1, 4) if bk>1 else 0
for p, bk in zip(probs, bk_odd)]
colors = [”#00ff88” if e>0 else (”#ff6600” if e==0 else “#ff3355”) for e in edges]
cats   = [s[“category”] for s in top_scores[:15]]

```
fig = make_subplots(rows=1, cols=2,
                    subplot_titles=("PROB % (Top 15 Risultati Esatti)", "EDGE % vs Bookmaker"),
                    horizontal_spacing=0.10)
cat_colors = {"HOME":"#ff6600","DRAW":"#ffcc00","AWAY":"#00aaff"}
fig.add_trace(go.Bar(
    x=labels, y=probs,
    marker_color=[cat_colors.get(c,"#8888aa") for c in cats],
    text=[f"{p:.2f}%" for p in probs], textposition="outside",
    textfont=dict(size=8), name="Prob%"), row=1, col=1)
fig.add_trace(go.Bar(
    x=labels, y=[e*100 for e in edges],
    marker_color=colors,
    text=[f"{e*100:+.1f}%" if bk_odd[i]>1 else "—" for i,e in enumerate(edges)],
    textposition="outside", textfont=dict(size=8), name="Edge%"), row=1, col=2)
fig.add_hline(y=0, line=dict(color="#444466",width=1), row=1, col=2)
fig.update_layout(**PL, title=_ptitle("EXACT SCORES — PROBABILITY & EDGE ANALYSIS"),
                  height=340, showlegend=False)
for c in [1,2]:
    fig.update_yaxes(ticksuffix="%", gridcolor="#1e1e35", row=1, col=c)
return fig
```

def multigoal_fig(mg_probs, mg_odds):
labels = list(mg_probs.keys())
probs  = [mg_probs[k]*100 for k in labels]
bk_odd = [mg_odds.get(k,0) for k in labels]
edges  = [round((mg_probs[k]*bk-1)*100,2) if bk else 0 for k,bk in zip(labels,bk_odd)]
colors = [”#00ff88” if e>0 else “#ff3355” for e in edges]

```
fig = make_subplots(rows=1, cols=2, subplot_titles=("PROB %","EDGE %"),
                    horizontal_spacing=0.12)
fig.add_trace(go.Bar(x=labels,y=probs,name="Prob",marker_color="#ff6600",
                     text=[f"{p:.1f}%" for p in probs],textposition="outside",
                     textfont=dict(size=9)),row=1,col=1)
fig.add_trace(go.Bar(x=labels,y=edges,name="Edge",marker_color=colors,
                     text=[f"{e:+.1f}%" for e in edges],textposition="outside",
                     textfont=dict(size=9)),row=1,col=2)
fig.add_hline(y=0,line=dict(color="#444466",width=1),row=1,col=2)
fig.update_layout(**PL, title=_ptitle("MULTIGOAL"),height=290,showlegend=False)
for c in [1,2]:
    fig.update_yaxes(ticksuffix="%",gridcolor="#1e1e35",row=1,col=c)
return fig
```

def asian_hcap_fig(ah_lines, ph_list, pa_list):
fig = go.Figure()
fig.add_trace(go.Scatter(x=ah_lines,y=[p*100 for p in ph_list],mode=“lines+markers”,
name=“Home Cover”,line=dict(color=”#ff6600”,width=2),marker=dict(size=7)))
fig.add_trace(go.Scatter(x=ah_lines,y=[p*100 for p in pa_list],mode=“lines+markers”,
name=“Away Cover”,line=dict(color=”#00aaff”,width=2),marker=dict(size=7)))
fig.add_hline(y=50,line=dict(color=”#444466”,width=1,dash=“dot”))
fig.update_layout(**PL, title=_ptitle(“ASIAN HANDICAP CURVE”),
xaxis_title=“Handicap (Home)”,
yaxis=dict(ticksuffix=”%”,gridcolor=”#1e1e35”,zerolinecolor=”#1e1e35”),
height=310)
return fig

def htft_fig(htft_probs):
combos = list(htft_probs.keys())
vals   = [htft_probs[k]*100 for k in combos]
cc = {“H/H”:”#ff6600”,“A/A”:”#00aaff”,“D/D”:”#ffcc00”}
colors = [cc.get(c,”#444466”) for c in combos]
fig = go.Figure(go.Bar(
x=combos, y=vals, marker_color=colors,
text=[f”{v:.2f}%” for v in vals], textposition=“outside”,
textfont=dict(size=9,color=”#e8e8f0”), width=0.6))
fig.update_layout(**PL, title=_ptitle(“HT/FT PROBABILITIES”),
yaxis=dict(ticksuffix=”%”,gridcolor=”#1e1e35”,zerolinecolor=”#1e1e35”),
height=300)
return fig

def cards_fig(cards_range, h_avg, a_avg):
lam = h_avg + a_avg
x   = list(range(12))
y   = [poisson.pmf(i,lam)*100 for i in x]
fig = make_subplots(rows=1,cols=2,subplot_titles=(“PMF CARTELLINI”,“RANGE PROBS”),
horizontal_spacing=0.12)
fig.add_trace(go.Bar(x=x,y=y,name=“P(k)”,
marker_color=[”#ff3355” if i>4 else “#ff6600” if i>2 else “#444466” for i in x],
text=[f”{v:.1f}%” for v in y],textposition=“outside”,
textfont=dict(size=8)),row=1,col=1)
fig.add_trace(go.Bar(x=list(cards_range.keys()),
y=[v*100 for v in cards_range.values()],
marker_color=[”#444466”,”#ff6600”,”#ff3355”,”#9933ff”],
text=[f”{v*100:.1f}%” for v in cards_range.values()],
textposition=“outside”,textfont=dict(size=9)),row=1,col=2)
fig.update_layout(**PL,title=_ptitle(f”CARDS  λ={lam:.2f}”),height=290,showlegend=False)
for c in [1,2]:
fig.update_yaxes(ticksuffix=”%”,gridcolor=”#1e1e35”,row=1,col=c)
return fig

def mc_fig(mc):
fig = make_subplots(rows=1,cols=2,
subplot_titles=(“TOTAL GOALS DIST”,“HOME vs AWAY”),
horizontal_spacing=0.10)
td = mc[“tot_dist”]; xt = list(range(len(td)))
fig.add_trace(go.Bar(x=xt,y=[v/10000*100 for v in td],name=“Total”,
marker_color=[”#ff6600” if x>2.5 else “#444466” for x in xt],
text=[f”{v/100:.1f}%” for v in td],textposition=“outside”,
textfont=dict(size=8)),row=1,col=1)
xg = list(range(10))
fig.add_trace(go.Bar(x=xg,y=[v/10000*100 for v in mc[“hg_dist”]],
name=“Home”,marker_color=”#ff6600”,opacity=0.85),row=1,col=2)
fig.add_trace(go.Bar(x=xg,y=[v/10000*100 for v in mc[“ag_dist”]],
name=“Away”,marker_color=”#00aaff”,opacity=0.85),row=1,col=2)
fig.update_layout(**PL,title=_ptitle(f”MONTE CARLO  μ={mc[‘mu’]:.2f} ± σ={mc[‘sig’]:.2f}”),
height=320,barmode=“group”)
for c in [1,2]:
fig.update_yaxes(ticksuffix=”%”,gridcolor=”#1e1e35”,row=1,col=c)
return fig

def radar_fig(markets):
mkts  = markets[:12]  # cap for readability
cats  = [m[“market”] for m in mkts]+[mkts[0][“market”]]
edge  = [max(m[“edge%”],0) for m in mkts]+[max(mkts[0][“edge%”],0)]
prob  = [m[“prob%”]/10 for m in mkts]+[mkts[0][“prob%”]/10]
fig   = go.Figure()
fig.add_trace(go.Scatterpolar(r=edge,theta=cats,fill=“toself”,name=“Edge%”,
line=dict(color=”#ff6600”,width=2),
fillcolor=“rgba(255,102,0,.09)”))
fig.add_trace(go.Scatterpolar(r=prob,theta=cats,fill=“toself”,name=“Prob Scaled”,
line=dict(color=”#00aaff”,width=2),
fillcolor=“rgba(0,170,255,.06)”))
fig.update_layout(**PL,
polar=dict(bgcolor=”#0f0f1a”,
radialaxis=dict(gridcolor=”#1e1e35”,tickfont=dict(size=8)),
angularaxis=dict(gridcolor=”#1e1e35”,tickfont=dict(size=9))),
title=_ptitle(“EDGE RADAR”), height=350)
return fig

def kelly_bar(markets, br):
valid = [m for m in markets if m[“stake”]>0]
if not valid: return go.Figure()
fig = go.Figure(go.Bar(
x=[m[“market”] for m in valid],
y=[m[“stake”] for m in valid],
marker_color=[f”rgba(0,255,136,{min(m[‘edge%’]/15,.9):.2f})” for m in valid],
text=[f”€{m[‘stake’]:.0f}\n{m[‘stake%’]:.1f}%” for m in valid],
textposition=“outside”,textfont=dict(size=8,color=”#e8e8f0”),width=0.5))
fig.add_hline(y=br*0.05,line=dict(color=”#ffcc00”,dash=“dot”,width=1),
annotation_text=“5% LIMIT”,annotation_font=dict(size=8,color=”#ffcc00”))
fig.update_layout(**PL,title=_ptitle(“KELLY STAKES (€)”),
yaxis=dict(tickprefix=“€”,gridcolor=”#1e1e35”,zerolinecolor=”#1e1e35”),
height=280)
return fig

# ══════════════════════════════════════════════════════════════════════════════

# HTML HELPERS

# ══════════════════════════════════════════════════════════════════════════════

def mc_(label, val, delta=””, color=“org”):
return (f’<div class="mc {color}"><div class="ab"></div>’
f’<div class="lbl">{label}</div><div class="val">{val}</div>’
+ (f’<div class="dlt">{delta}</div>’ if delta else “”) + ‘</div>’)

def sh_(icon, title):
return (f’<div class="sh"><span class="icon">{icon}</span>’
f’<h3>{title}</h3></div>’)

def grid(*cards, cols=4):
c = {4:“mg4”,3:“mg3”,2:“mg2”}.get(cols,“mg4”)
return f’<div class="mg {c}">{””.join(cards)}</div>’

def badge(t, cls=“pos”):
return f’<span class="vbadge {cls}">{t}</span>’

# ══════════════════════════════════════════════════════════════════════════════

# CORE ANALYSIS — CACHED

# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def run_analysis(
hn, hgf, hga, hxg, hxga, hcor, hcrd, hsot, hwt,
an, agf, aga, axg, axga, acor, acrd, asot, awt,
odds_json, n_sim, players_json,
):
home = TeamStats(hn, hgf, hga, hxg, hxga, hcor, hcrd, hsot, hwt)
away = TeamStats(an, agf, aga, axg, axga, acor, acrd, asot, awt)
odds = json.loads(odds_json)
players: List[Dict] = json.loads(players_json)
br   = odds.get(“bankroll”, 1000.0)

```
eng = QuantumEngine(home, away)
mat = eng.matrix()

ph, pd, pa       = eng.p_1x2()
ov15, un15       = eng.p_ou(1.5)
ov25, un25       = eng.p_ou(2.5)
ov35, un35       = eng.p_ou(3.5)
ov45, un45       = eng.p_ou(4.5)
bttsy, bttsn     = eng.p_btts()
mg               = eng.p_multigoal()
htft             = eng.p_ht_ft()
sh_h             = eng.shot_quality(home.xg_avg, home.shots_on_avg)
sh_a             = eng.shot_quality(away.xg_avg, away.shots_on_avg)

# Exact scores
top_scores       = eng.top_exact_scores(top_n=30)
all_scores_dict  = eng.all_exact_scores_dict()

# Cards
cr_ou_main, _    = eng.p_cards_ou(home.cards_avg, away.cards_avg, odds.get("cards_line",3.5))
cr_ou25, _       = eng.p_cards_ou(home.cards_avg, away.cards_avg, 2.5)
cr_ou35, _       = eng.p_cards_ou(home.cards_avg, away.cards_avg, 3.5)
cr_range         = eng.p_cards_range(home.cards_avg, away.cards_avg)
lam_cards        = home.cards_avg + away.cards_avg

# Corners
cor_ov, _        = eng.p_corners_ou(home.corners_avg, away.corners_avg, odds.get("corners_line",10.5))

# Asian Handicap curve
ah_lines = [-2.5,-2.0,-1.5,-1.0,-0.5,0.0,0.5,1.0,1.5,2.0,2.5]
ah_data  = {str(h): eng.p_asian_handicap(h) for h in ah_lines}

# European Handicap
eh_m1 = eng.p_euro_handicap(-1)
eh_p1 = eng.p_euro_handicap(+1)

# Goalscorer
gs_results = {}
for pl in players:
    gs = eng.p_goalscorer(pl["goals_pg"], pl.get("minutes_avg",80))
    gs_results[pl["name"]] = {**gs, "team": pl["team"]}

# Monte Carlo
mc = eng.monte_carlo(n_sim)

# ── Finance: build all markets
fm = FinanceManager
markets = [
    fm.analyse("1 "+hn,         ph,    odds.get("home",2.1),   br),
    fm.analyse("X DRAW",         pd,    odds.get("draw",3.4),   br),
    fm.analyse("2 "+an,          pa,    odds.get("away",3.2),   br),
    fm.analyse("OVER 1.5",       ov15,  odds.get("over15",1.4), br),
    fm.analyse("OVER 2.5",       ov25,  odds.get("over25",1.9), br),
    fm.analyse("OVER 3.5",       ov35,  odds.get("over35",2.8), br),
    fm.analyse("OVER 4.5",       ov45,  odds.get("over45",4.2), br),
    fm.analyse("BTTS YES",       bttsy, odds.get("btts_y",1.85),br),
    fm.analyse("MG 0-1",         mg["0-1"], odds.get("mg_01",5.5),  br),
    fm.analyse("MG 1-2",         mg["1-2"], odds.get("mg_12",3.8),  br),
    fm.analyse("MG 2-3",         mg["2-3"], odds.get("mg_23",2.6),  br),
    fm.analyse("MG 3-4",         mg["3-4"], odds.get("mg_34",3.2),  br),
    fm.analyse("MG 4-5",         mg["4-5"], odds.get("mg_45",5.0),  br),
    fm.analyse("AH -1.5",        ah_data["-1.5"]["home_cover"],odds.get("ah_minus15",1.9),br),
    fm.analyse("AH -0.5",        ah_data["-0.5"]["home_cover"],odds.get("ah_minus05",1.88),br),
    fm.analyse("AH +0.5",        ah_data["0.5"]["home_cover"], odds.get("ah_plus05",1.88),br),
    fm.analyse("AH +1.5",        ah_data["1.5"]["home_cover"], odds.get("ah_plus15",1.9),br),
    fm.analyse(f"EH {hn} -1",    eh_m1[0], odds.get("eh_home_m1",1.6),br),
    fm.analyse(f"EH {an} -1",    eh_p1[2], odds.get("eh_away_p1",1.65),br),
    fm.analyse("HT/FT H/H",     htft["H/H"], odds.get("htft_hh",3.8),br),
    fm.analyse("HT/FT D/H",     htft["D/H"], odds.get("htft_dh",5.5),br),
    fm.analyse("HT/FT D/D",     htft["D/D"], odds.get("htft_dd",4.2),br),
    fm.analyse(f"CARDS O{odds.get('cards_line',3.5)}",
               cr_ou_main, odds.get("cards_ou_main",1.9),br),
    fm.analyse(f"CORNERS O{odds.get('corners_line',10.5)}",
               cor_ov, odds.get("corners_over",1.9),br),
]

# Exact scores markets (from BK odds provided)
es_bk = odds.get("exact_scores", {})
for score, bk_q in es_bk.items():
    if bk_q and bk_q > 1:
        p_sc = all_scores_dict.get(score, 0)
        if p_sc > 0:
            markets.append(fm.analyse(f"ES {score}", p_sc, bk_q, br))

# Goalscorer markets
gs_bk = odds.get("anytime_goalscorer", {})
for nm, gs in gs_results.items():
    bk_q = gs_bk.get(nm, 0)
    if bk_q and bk_q > 1:
        markets.append(fm.analyse(f"⚽ {nm}", gs["anytime"], bk_q, br))

return {
    "ph":ph,"pd":pd,"pa":pa,
    "ov15":ov15,"ov25":ov25,"ov35":ov35,"ov45":ov45,
    "bttsy":bttsy,
    "mg":mg,"htft":htft,
    "ah_data":ah_data,"ah_lines":ah_lines,
    "eh_m1":eh_m1,"eh_p1":eh_p1,
    "top_scores":top_scores,
    "all_scores":all_scores_dict,
    "cards":{"lam":lam_cards,"ou25":cr_ou25,"ou35":cr_ou35,
             "main":cr_ou_main,"range":cr_range},
    "cor_ov":cor_ov,
    "gs":gs_results,
    "sh_h":sh_h,"sh_a":sh_a,
    "lam_h":eng.lam_h,"lam_a":eng.lam_a,
    "mat":mat,"mc":mc,
    "markets":markets,"br":br,
}
```

# ══════════════════════════════════════════════════════════════════════════════

# STREAMLIT MAIN

# ══════════════════════════════════════════════════════════════════════════════

def main():
st.set_page_config(page_title=“Quantum Football v4”, page_icon=“⚡”,
layout=“wide”, initial_sidebar_state=“expanded”)
st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)

```
# ── SIDEBAR ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ SYSTEM CONFIG")
    gemini_key = st.text_input("🔑 GEMINI API KEY", type="password", placeholder="AIza...")
    st.markdown("---")

    # COMPETITION SELECTOR
    st.markdown("### 🏆 COMPETIZIONE")
    country = st.selectbox("Paese / Nazione",
                            options=list(COMPETITIONS.keys()), index=0)
    competition = st.selectbox("Lega / Coppa",
                                options=COMPETITIONS[country])
    st.markdown("---")
    st.markdown("### 🏟️ MATCH")
    h_name = st.text_input("Home Team", value="LAZIO")
    a_name = st.text_input("Away Team", value="ATALANTA")
    st.markdown("---")
    st.markdown("### 💰 BANKROLL")
    bankroll = st.number_input("Bankroll (€)", 100.0, 1_000_000.0, 1000.0, 100.0)
    st.markdown("---")
    n_sim = st.select_slider("🎲 Monte Carlo N",
                              [1_000, 5_000, 10_000, 50_000], 10_000)

# ── HEADER ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="bh">
  <h1>⚡ QUANTUM FOOTBALL ANALYTICS  v4.0</h1>
  <div class="sub">
    Poisson · Risultati Esatti · Multigoal · AH/EH · HT/FT ·
    Cartellini · Angoli · Goalscorer · Monte Carlo · AI Cross-Check
  </div>
  <div class="comp-badge">🏆 {country.split()[-1]} — {competition}</div>
</div>""", unsafe_allow_html=True)

# ── TABS ─────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📥 INPUT",
    "📊 QUANTITATIVA",
    "🎯 RISULTATI ESATTI",
    "📐 MERCATI SPECIALI",
    "💰 VALUE & KELLY",
    "🎲 MONTE CARLO",
    "🤖 AI CHECK",
])

# ════════════════════════════════════════════════════════════════════════
#  TAB 0 — INPUT
# ════════════════════════════════════════════════════════════════════════
with tabs[0]:
    # SMART SCRAPERS
    with st.expander("🤖 SMART SCRAPER — STATISTICHE (SofaScore / FBRef / WhoScored)", expanded=False):
        raw_stats = st.text_area("Testo statistiche grezzo", height=160,
            placeholder=f"Incolla stats da SofaScore/FBRef per {competition}...", key="rs")
        if st.button("🔬 PARSE STATISTICHE"):
            if not gemini_key: st.error("Inserisci Gemini API Key!")
            elif raw_stats.strip():
                with st.spinner("Gemini analizza..."):
                    r = SmartParser(gemini_key).parse_stats(raw_stats)
                    if r["ok"]:
                        st.success("✅ Parsing completato!")
                        st.session_state["pstats"] = r["data"]
                        st.json(r["data"])
                    else: st.error(r["error"])

    with st.expander("🤖 SMART SCRAPER — QUOTE (Oddsportal / BetExplorer / Flashscore)", expanded=False):
        raw_odds = st.text_area("Testo quote grezzo", height=160,
            placeholder=f"Incolla quote bookmaker per {competition}...", key="ro")
        if st.button("💹 PARSE QUOTE"):
            if not gemini_key: st.error("Inserisci Gemini API Key!")
            elif raw_odds.strip():
                with st.spinner("Gemini analizza..."):
                    r = SmartParser(gemini_key).parse_odds(raw_odds)
                    if r["ok"]:
                        st.success("✅ Parsing completato!")
                        st.session_state["podds"] = r["data"]
                        st.json(r["data"])
                    else: st.error(r["error"])

    ps = st.session_state.get("pstats", {})
    po = st.session_state.get("podds", {})

    st.markdown("---")
    # STATS INPUT
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### 🏠 {h_name}")
        hgf  = st.number_input("GF avg",   value=float(ps.get("home_gf_avg",  1.60)), step=.05, format="%.2f", key="hgf")
        hga  = st.number_input("GA avg",   value=float(ps.get("home_ga_avg",  1.10)), step=.05, format="%.2f", key="hga")
        hxg  = st.number_input("xG avg",   value=float(ps.get("home_xg_avg",  1.55)), step=.05, format="%.2f", key="hxg")
        hxga = st.number_input("xGA avg",  value=float(ps.get("home_xga_avg", 1.15)), step=.05, format="%.2f", key="hxga")
        hcor = st.number_input("Corners",  value=float(ps.get("home_corners_avg", 6.2)), step=.1, format="%.1f", key="hcor")
        hcrd = st.number_input("Cards",    value=float(ps.get("home_cards_avg",  1.7)), step=.1, format="%.1f", key="hcrd")
        hsot = st.number_input("Shots OT", value=float(ps.get("home_shots_on_avg",4.8)),step=.1, format="%.1f", key="hsot")
        hwt  = st.slider("Recency Weight", 0.80, 1.40, float(ps.get("home_weight_recent",1.0)), 0.05, key="hwt",
                         help="1.2 = ultimi 5 match pesano 20% in più")
    with c2:
        st.markdown(f"#### ✈️ {a_name}")
        agf  = st.number_input("GF avg",   value=float(ps.get("away_gf_avg",  1.90)), step=.05, format="%.2f", key="agf")
        aga  = st.number_input("GA avg",   value=float(ps.get("away_ga_avg",  0.90)), step=.05, format="%.2f", key="aga")
        axg  = st.number_input("xG avg",   value=float(ps.get("away_xg_avg",  1.82)), step=.05, format="%.2f", key="axg")
        axga = st.number_input("xGA avg",  value=float(ps.get("away_xga_avg", 0.95)), step=.05, format="%.2f", key="axga")
        acor = st.number_input("Corners",  value=float(ps.get("away_corners_avg", 5.8)), step=.1, format="%.1f", key="acor")
        acrd = st.number_input("Cards",    value=float(ps.get("away_cards_avg",  1.5)), step=.1, format="%.1f", key="acrd")
        asot = st.number_input("Shots OT", value=float(ps.get("away_shots_on_avg",5.4)),step=.1, format="%.1f", key="asot")
        awt  = st.slider("Recency Weight", 0.80, 1.40, float(ps.get("away_weight_recent",1.0)), 0.05, key="awt")

    st.markdown("---")
    # ODDS INPUT
    st.markdown(sh_("💹", "QUOTE BOOKMAKER"), unsafe_allow_html=True)
    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        st.markdown("**1X2 & O/U**")
        o_home  = st.number_input("1 Home",   value=float(po.get("home",  2.10)),step=.05,format="%.2f",key="oh")
        o_draw  = st.number_input("X Draw",   value=float(po.get("draw",  3.40)),step=.05,format="%.2f",key="od")
        o_away  = st.number_input("2 Away",   value=float(po.get("away",  3.20)),step=.05,format="%.2f",key="oa")
        o_ov15  = st.number_input("Over 1.5", value=float(po.get("over15",1.40)),step=.05,format="%.2f",key="o15")
        o_ov25  = st.number_input("Over 2.5", value=float(po.get("over25",1.90)),step=.05,format="%.2f",key="o25")
        o_ov35  = st.number_input("Over 3.5", value=float(po.get("over35",2.80)),step=.05,format="%.2f",key="o35")
        o_ov45  = st.number_input("Over 4.5", value=float(po.get("over45",4.20)),step=.05,format="%.2f",key="o45")
        o_btts  = st.number_input("BTTS Yes", value=float(po.get("btts_y",1.85)),step=.05,format="%.2f",key="obt")
    with oc2:
        st.markdown("**Multigoal**")
        o_mg01 = st.number_input("MG 0-1",value=float(po.get("mg_01",5.50)),step=.05,format="%.2f",key="m01")
        o_mg12 = st.number_input("MG 1-2",value=float(po.get("mg_12",3.80)),step=.05,format="%.2f",key="m12")
        o_mg23 = st.number_input("MG 2-3",value=float(po.get("mg_23",2.60)),step=.05,format="%.2f",key="m23")
        o_mg34 = st.number_input("MG 3-4",value=float(po.get("mg_34",3.20)),step=.05,format="%.2f",key="m34")
        o_mg45 = st.number_input("MG 4-5",value=float(po.get("mg_45",5.00)),step=.05,format="%.2f",key="m45")
        st.markdown("**Angoli**")
        o_cline = st.number_input("Corners Line",value=float(po.get("corners_line",10.5)),step=.5,format="%.1f",key="ocl")
        o_cov   = st.number_input("Corners Over", value=float(po.get("corners_over",1.90)),step=.05,format="%.2f",key="oco")
        st.markdown("**Cartellini**")
        o_kdline = st.number_input("Cards Line", value=float(po.get("cards_line",3.5)),step=.5,format="%.1f",key="okl")
        o_kdov   = st.number_input("Cards Over", value=float(po.get("cards_ou_main",1.90)),step=.05,format="%.2f",key="oko")
    with oc3:
        st.markdown("**Handicap Asiatico**")
        o_ahm25 = st.number_input("AH -2.5",value=float(po.get("ah_minus25",1.95)),step=.05,format="%.2f",key="am25")
        o_ahm15 = st.number_input("AH -1.5",value=float(po.get("ah_minus15",1.90)),step=.05,format="%.2f",key="am15")
        o_ahm05 = st.number_input("AH -0.5",value=float(po.get("ah_minus05",1.88)),step=.05,format="%.2f",key="am05")
        o_ah00  = st.number_input("AH  0.0",value=float(po.get("ah_zero",   1.90)),step=.05,format="%.2f",key="ah0")
        o_ahp05 = st.number_input("AH +0.5",value=float(po.get("ah_plus05", 1.88)),step=.05,format="%.2f",key="ap05")
        o_ahp15 = st.number_input("AH +1.5",value=float(po.get("ah_plus15", 1.90)),step=.05,format="%.2f",key="ap15")
        st.markdown("**Handicap Europeo**")
        o_ehm1h = st.number_input(f"EH {h_name}-1 H",value=float(po.get("eh_home_m1",1.60)),step=.05,format="%.2f",key="em1h")
        o_ehm1d = st.number_input(f"EH {h_name}-1 D",value=float(po.get("eh_draw_m1",3.80)),step=.05,format="%.2f",key="em1d")
        o_ehm1a = st.number_input(f"EH {h_name}-1 A",value=float(po.get("eh_away_m1",4.50)),step=.05,format="%.2f",key="em1a")

    # HT/FT
    st.markdown("---")
    st.markdown(sh_("⏱️", "HT/FT QUOTE"), unsafe_allow_html=True)
    hc1,hc2,hc3 = st.columns(3)
    with hc1:
        o_hh=st.number_input("H/H",value=float(po.get("htft_hh",3.80)),step=.1,format="%.2f",key="hh")
        o_hd=st.number_input("H/D",value=float(po.get("htft_hd",7.00)),step=.1,format="%.2f",key="hd")
        o_ha=st.number_input("H/A",value=float(po.get("htft_ha",15.0)),step=.5,format="%.2f",key="ha")
    with hc2:
        o_dh=st.number_input("D/H",value=float(po.get("htft_dh",5.50)),step=.1,format="%.2f",key="dh")
        o_dd=st.number_input("D/D",value=float(po.get("htft_dd",4.20)),step=.1,format="%.2f",key="dd")
        o_da=st.number_input("D/A",value=float(po.get("htft_da",6.00)),step=.1,format="%.2f",key="da")
    with hc3:
        o_ah_=st.number_input("A/H",value=float(po.get("htft_ah",18.0)),step=.5,format="%.2f",key="ahx")
        o_ad =st.number_input("A/D",value=float(po.get("htft_ad",8.00)), step=.1,format="%.2f",key="adx")
        o_aa =st.number_input("A/A",value=float(po.get("htft_aa",6.00)), step=.1,format="%.2f",key="aax")

    # EXACT SCORES ODDS INPUT  ← NUOVO v4.0
    st.markdown("---")
    st.markdown(sh_("🎯", "QUOTE RISULTATI ESATTI — INSERIMENTO MANUALE"), unsafe_allow_html=True)
    st.caption("Inserisci le quote del bookmaker per i risultati esatti che vuoi analizzare. "
               "Lascia 0 per saltare. Il parser AI popola automaticamente se incolla quote.")

    common_scores = ["0-0","1-0","0-1","1-1","2-0","0-2","2-1","1-2",
                     "2-2","3-0","0-3","3-1","1-3","3-2","2-3",
                     "4-0","0-4","4-1","1-4","3-3"]

    # Merge parsed + manual
    parsed_es = po.get("exact_scores", {})
    n_score_cols = 4
    score_cols   = st.columns(n_score_cols)
    es_odds_manual: Dict[str, float] = {}
    for idx, score in enumerate(common_scores):
        default_val = float(parsed_es.get(score, 0.0))
        col = score_cols[idx % n_score_cols]
        val = col.number_input(f"⚽ {score}", value=default_val,
                               min_value=0.0, step=0.5, format="%.2f",
                               key=f"es_{score.replace('-','_')}")
        if val > 1.0:
            es_odds_manual[score] = val

    # Extra scores
    with st.expander("➕ Aggiungi risultati esatti personalizzati", expanded=False):
        extra_scores_txt = st.text_area(
            "Formato: score=quota, uno per riga (es: 4-2=18.00)",
            height=80, key="extra_es",
            placeholder="4-2=18.00\n5-1=45.00\n2-4=28.00"
        )
        for line in extra_scores_txt.strip().split("\n"):
            line = line.strip()
            if "=" in line:
                try:
                    sc, qq = line.split("=")
                    sc = sc.strip(); qq = float(qq.strip())
                    if qq > 1.0: es_odds_manual[sc] = qq
                except: pass

    # Merge all ES odds (parsed wins over manual if present)
    final_es_odds = {**es_odds_manual}
    for k, v in parsed_es.items():
        if v and float(v) > 1.0:
            final_es_odds[k] = float(v)

    # GOALSCORER
    st.markdown("---")
    st.markdown(sh_("⚽", "ANYTIME GOALSCORER"), unsafe_allow_html=True)
    players_from_parse = ps.get("players", [])
    n_pl = st.number_input("N° giocatori", 0, 8, max(len(players_from_parse),2), 1)
    players_input = []
    gs_bk_odds = po.get("anytime_goalscorer", {})
    for i in range(int(n_pl)):
        pc1,pc2,pc3,pc4 = st.columns([3,2,2,2])
        dfn  = players_from_parse[i]["name"] if i<len(players_from_parse) else f"Player {i+1}"
        dfgpg= players_from_parse[i].get("goals_pg",0.30) if i<len(players_from_parse) else 0.30
        dftm = players_from_parse[i].get("team","home") if i<len(players_from_parse) else "home"
        with pc1: pn  = st.text_input("Nome",     value=dfn, key=f"pn{i}")
        with pc2: pgpg= st.number_input("Goals/g", value=float(dfgpg), min_value=0.0, max_value=2.0, step=.05, format="%.2f", key=f"pgpg{i}")
        with pc3: pmin= st.number_input("Min/g",  value=80.0, min_value=0.0, max_value=95.0, step=5.0, key=f"pm{i}")
        with pc4: ptm = st.selectbox("Team", ["home","away"], index=0 if dftm=="home" else 1, key=f"pt{i}")
        pn = pn.strip()
        dfbk = float(gs_bk_odds.get(pn, 3.5))
        pbk  = st.number_input(f"BK Anytime {pn}", value=dfbk, min_value=1.01, step=.05, format="%.2f", key=f"pbk{i}")
        if pn:
            players_input.append({"name":pn,"goals_pg":pgpg,"minutes_avg":pmin,"team":ptm,"bk_odd":pbk})

    # NOTES
    st.markdown("---")
    qual_notes = st.text_area("📰 Retroscena / Infortuni / Meteo / Arbitro / Rumors",
                               height=90, key="notes")

    # BUILD ODDS DICT
    odds_dict = {
        "bankroll":bankroll,
        "home":o_home,"draw":o_draw,"away":o_away,
        "over15":o_ov15,"over25":o_ov25,"over35":o_ov35,"over45":o_ov45,
        "btts_y":o_btts,
        "mg_01":o_mg01,"mg_12":o_mg12,"mg_23":o_mg23,"mg_34":o_mg34,"mg_45":o_mg45,
        "ah_minus25":o_ahm25,"ah_minus15":o_ahm15,"ah_minus05":o_ahm05,
        "ah_zero":o_ah00,"ah_plus05":o_ahp05,"ah_plus15":o_ahp15,
        "eh_home_m1":o_ehm1h,"eh_draw_m1":o_ehm1d,"eh_away_m1":o_ehm1a,
        "htft_hh":o_hh,"htft_hd":o_hd,"htft_ha":o_ha,
        "htft_dh":o_dh,"htft_dd":o_dd,"htft_da":o_da,
        "htft_ah":o_ah_,"htft_ad":o_ad,"htft_aa":o_aa,
        "cards_line":o_kdline,"cards_ou_main":o_kdov,
        "corners_line":o_cline,"corners_over":o_cov,
        "exact_scores":final_es_odds,
        "anytime_goalscorer":{p["name"]:p["bk_odd"] for p in players_input if p["name"]},
    }

    st.session_state["rp"] = dict(
        hn=h_name, hgf=hgf,hga=hga,hxg=hxg,hxga=hxga,
        hcor=hcor,hcrd=hcrd,hsot=hsot,hwt=hwt,
        an=a_name, agf=agf,aga=aga,axg=axg,axga=axga,
        acor=acor,acrd=acrd,asot=asot,awt=awt,
        odds_dict=odds_dict, n_sim=n_sim,
        players=players_input, qual_notes=qual_notes,
        competition=competition, country=country,
    )
    st.info(f"✅ Dati salvati — {competition} | {h_name} vs {a_name} — passa agli altri tab.")

# ── HELPER ───────────────────────────────────────────
def get_R():
    rp = st.session_state.get("rp")
    if not rp: return None
    return run_analysis(
        rp["hn"],rp["hgf"],rp["hga"],rp["hxg"],rp["hxga"],
        rp["hcor"],rp["hcrd"],rp["hsot"],rp["hwt"],
        rp["an"],rp["agf"],rp["aga"],rp["axg"],rp["axga"],
        rp["acor"],rp["acrd"],rp["asot"],rp["awt"],
        json.dumps(rp["odds_dict"]), rp["n_sim"],
        json.dumps(rp["players"]),
    )

def no_data():
    st.info("ℹ️ Configura prima i dati nel Tab INPUT.")

# ════════════════════════════════════════════════════════════════════════
#  TAB 1 — ANALISI QUANTITATIVA
# ════════════════════════════════════════════════════════════════════════
with tabs[1]:
    R = get_R()
    if R is None: no_data(); st.stop()
    rp = st.session_state["rp"]
    hn, an = rp["hn"], rp["an"]
    fm = FinanceManager

    st.markdown(sh_("⚡","PARAMETRI POISSON"), unsafe_allow_html=True)
    st.markdown(grid(
        mc_("λ "+hn,    f"{R['lam_h']:.4f}", "Expected Goals Home","org"),
        mc_("λ "+an,    f"{R['lam_a']:.4f}", "Expected Goals Away","blu"),
        mc_("E[Goals]", f"{R['lam_h']+R['lam_a']:.3f}",
            f"CI 95%: {R['mc']['ci_lo']:.1f}–{R['mc']['ci_hi']:.1f}","yel"),
        mc_("σ Goals",  f"{R['mc']['sig']:.3f}", "Std Dev MC","red"),
    ), unsafe_allow_html=True)

    st.markdown(sh_("📊","PROBABILITÀ 1X2 & GOAL"), unsafe_allow_html=True)
    st.markdown(grid(
        mc_("PROB "+hn,  f"{R['ph']*100:.1f}%", f"Fair: {fm.fair(R['ph']):.2f}","org"),
        mc_("PROB DRAW", f"{R['pd']*100:.1f}%", f"Fair: {fm.fair(R['pd']):.2f}","yel"),
        mc_("PROB "+an,  f"{R['pa']*100:.1f}%", f"Fair: {fm.fair(R['pa']):.2f}","blu"),
        mc_("OVER 2.5",  f"{R['ov25']*100:.1f}%",f"O1.5:{R['ov15']*100:.1f}%","grn"),
    ), unsafe_allow_html=True)
    st.markdown(grid(
        mc_("OVER 3.5", f"{R['ov35']*100:.1f}%",f"Fair:{fm.fair(R['ov35']):.2f}","org"),
        mc_("OVER 4.5", f"{R['ov45']*100:.1f}%",f"Fair:{fm.fair(R['ov45']):.2f}","red"),
        mc_("BTTS YES", f"{R['bttsy']*100:.1f}%",f"Fair:{fm.fair(R['bttsy']):.2f}","cyn"),
        mc_("CORNERS O",f"{R['cor_ov']*100:.1f}%",f"Line {rp['odds_dict']['corners_line']}","pur"),
    ), unsafe_allow_html=True)

    c1,c2 = st.columns([3,2])
    with c1:
        st.plotly_chart(heatmap_fig(R["mat"],hn,an), use_container_width=True)
    with c2:
        st.plotly_chart(bar1x2(R["ph"],R["pd"],R["pa"],hn,an), use_container_width=True)
        st.markdown(sh_("🎯","TOP EXACT SCORES — QUICK VIEW"), unsafe_allow_html=True)
        quick = [{"Score":s["score"],"Cat":s["category"],"Prob%":f"{s['prob_pct']:.3f}%",
                  "Fair Odd":f"{s['fair_odd']:.2f}"} for s in R["top_scores"][:10]]
        st.dataframe(pd.DataFrame(quick), use_container_width=True, hide_index=True)

    # Shot Quality
    st.markdown(sh_("🎯","SHOT QUALITY INDEX"), unsafe_allow_html=True)
    tc = {"ELITE":"grn","HIGH":"org","MED":"yel","LOW":"red"}
    c1,c2 = st.columns(2)
    with c1:
        s=R["sh_h"]
        st.markdown(grid(mc_(hn+" PREC",f"{s['precision']:.3f}","xG/SoT","org"),
                         mc_("QUALITY",f"{s['qi']:.1f}/10","Efficiency","yel"),
                         mc_("THREAT",s["level"],"",tc.get(s["level"],"blu")),cols=3),
                    unsafe_allow_html=True)
    with c2:
        s=R["sh_a"]
        st.markdown(grid(mc_(an+" PREC",f"{s['precision']:.3f}","xG/SoT","blu"),
                         mc_("QUALITY",f"{s['qi']:.1f}/10","Efficiency","yel"),
                         mc_("THREAT",s["level"],"",tc.get(s["level"],"blu")),cols=3),
                    unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════
#  TAB 2 — RISULTATI ESATTI  ← NUOVO v4.0
# ════════════════════════════════════════════════════════════════════════
with tabs[2]:
    R = get_R()
    if R is None: no_data(); st.stop()
    rp = st.session_state["rp"]
    hn, an = rp["hn"], rp["an"]
    fm = FinanceManager
    br = R["br"]
    es_bk_map = rp["odds_dict"].get("exact_scores", {})

    st.markdown(sh_("🎯","RISULTATI ESATTI — ANALISI COMPLETA"), unsafe_allow_html=True)

    # Summary metrics
    top_score = R["top_scores"][0]
    val_scores = [s for s in R["top_scores"]
                  if es_bk_map.get(s["score"],0) > s["fair_odd"]]
    best_edge_sc = max(
        (fm.edge(s["prob"], es_bk_map[s["score"]])*100
         for s in R["top_scores"] if es_bk_map.get(s["score"],0)>1),
        default=0.0
    )

    st.markdown(grid(
        mc_("MOST LIKELY",  top_score["score"], f"{top_score['prob_pct']:.3f}%","org"),
        mc_("FAIR ODD #1",  f"{top_score['fair_odd']:.2f}", top_score["category"],"yel"),
        mc_("VALUE SCORES", str(len(val_scores)), "con BK > Fair Odd","grn"),
        mc_("BEST EDGE",    f"{best_edge_sc:.2f}%", "Su risultato esatto","cyn"),
    ), unsafe_allow_html=True)

    # Chart
    st.plotly_chart(exact_scores_chart(R["top_scores"], es_bk_map),
                    use_container_width=True)

    # Full Table — top 30
    st.markdown(sh_("📋","TABELLA COMPLETA — TOP 30 RISULTATI ESATTI"), unsafe_allow_html=True)

    rows = []
    for s in R["top_scores"]:
        bk  = es_bk_map.get(s["score"], 0)
        edge = fm.edge(s["prob"], bk)*100 if bk>1 else None
        kl   = fm.kelly(s["prob"], bk, br) if bk>1 else {"stake":0,"pct":0,"ev":0}
        val  = (bk > s["fair_odd"]) if bk>1 else False
        rows.append({
            "SCORE":     s["score"],
            "CATEGORIA": s["category"],
            "PROB%":     s["prob_pct"],
            "FAIR ODD":  s["fair_odd"],
            "BK ODD":    f"{bk:.2f}" if bk>1 else "—",
            "EDGE%":     f"{edge:+.2f}%" if edge is not None else "—",
            "STAKE€":    f"€{kl['stake']:.2f}" if kl["stake"]>0 else "—",
            "STAKE%":    f"{kl['pct']:.2f}%" if kl["stake"]>0 else "—",
            "EV€":       f"€{kl['ev']:.2f}" if kl["stake"]>0 else "—",
            "VALUE":     "✅" if val else ("⬜" if bk>1 else "—"),
        })

    df_es = pd.DataFrame(rows)

    def style_es(row):
        if row["VALUE"] == "✅":
            return ["background-color:rgba(0,255,136,.06)"]*len(row)
        return [""]*len(row)

    st.dataframe(
        df_es.style.apply(style_es, axis=1)
             .background_gradient(subset=["PROB%"], cmap="YlOrRd"),
        use_container_width=True, hide_index=True
    )

    # Value hits detail
    if val_scores:
        st.markdown(sh_("💎","VALUE SCORES — DETTAGLIO KELLY"), unsafe_allow_html=True)
        val_sorted = sorted(val_scores,
                            key=lambda s: -fm.edge(s["prob"], es_bk_map.get(s["score"],0)))
        for s in val_sorted[:8]:
            bk   = es_bk_map[s["score"]]
            edge = fm.edge(s["prob"], bk)*100
            kl   = fm.kelly(s["prob"], bk, br)
            bar_w= min(int(edge*6), 100)
            ec   = "#00ff88" if edge>5 else "#ffcc00"
            cat_c= {"HOME":"#ff6600","DRAW":"#ffcc00","AWAY":"#00aaff"}.get(s["category"],"#8888aa")
            st.markdown(f"""
            <div class="score-card value-hit">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                  <span class="s-label">RISULTATO ESATTO</span>
                  <div style="display:flex;align-items:center;gap:12px;margin-top:4px;">
                    <span class="s-score">{s['score']}</span>
                    <span class="vbadge {'pos' if s['category']=='HOME' else ('yel' if s['category']=='DRAW' else 'blu')}"
                          style="border-color:{cat_c};color:{cat_c};">{s['category']}</span>
                  </div>
                </div>
                <div style="display:flex;gap:20px;flex-wrap:wrap;">
                  <div style="text-align:center;">
                    <div class="s-label">PROB</div>
                    <div class="s-prob">{s['prob_pct']:.3f}%</div>
                  </div>
                  <div style="text-align:center;">
                    <div class="s-label">FAIR</div>
                    <div class="s-fair" style="font-size:.9rem;color:#e8e8f0;">{s['fair_odd']:.2f}</div>
                  </div>
                  <div style="text-align:center;">
                    <div class="s-label">BK</div>
                    <div style="font-size:.9rem;font-weight:600;color:#e8e8f0;">{bk:.2f}</div>
                  </div>
                  <div style="text-align:center;">
                    <div class="s-label">EDGE</div>
                    <div class="s-edge pos">{edge:+.2f}%</div>
                  </div>
                  <div style="text-align:center;">
                    <div class="s-label">STAKE</div>
                    <div style="font-size:.9rem;font-weight:600;color:#e8e8f0;">€{kl['stake']:.2f}</div>
                  </div>
                  <div style="text-align:center;">
                    <div class="s-label">EV</div>
                    <div style="font-size:.9rem;font-weight:600;color:#00ff88;">€{kl['ev']:.2f}</div>
                  </div>
                </div>
              </div>
              <div style="height:2px;background:#1e1e35;border-radius:2px;margin-top:10px;">
                <div style="height:2px;width:{bar_w}%;background:linear-gradient(90deg,#ff6600,#ffcc00);"></div>
              </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("ℹ️ Nessuna value bet su risultati esatti. Inserisci le quote nel Tab INPUT → Risultati Esatti.")

    # Category breakdown
    st.markdown("---")
    st.markdown(sh_("📊","BREAKDOWN PER CATEGORIA"), unsafe_allow_html=True)
    cat_data = {"HOME":0.0,"DRAW":0.0,"AWAY":0.0}
    for s in R["all_scores"].items() if isinstance(R["all_scores"], dict) else []:
        pass
    # Compute from matrix
    mat = R["mat"]
    N   = mat.shape[0]
    for i in range(N):
        for j in range(N):
            if i > j: cat_data["HOME"] += mat[i,j]
            elif i == j: cat_data["DRAW"] += mat[i,j]
            else: cat_data["AWAY"] += mat[i,j]

    fig_cat = go.Figure(go.Pie(
        labels=list(cat_data.keys()),
        values=[v*100 for v in cat_data.values()],
        hole=0.55,
        marker_colors=["#ff6600","#ffcc00","#00aaff"],
        textinfo="label+percent",
        textfont=dict(size=11,family="IBM Plex Mono"),
    ))
    fig_cat.update_layout(**PL, title=_ptitle("PROB DISTRIBUZIONE HOME/DRAW/AWAY"),
                          height=280, showlegend=False)
    st.plotly_chart(fig_cat, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════
#  TAB 3 — MERCATI SPECIALI
# ════════════════════════════════════════════════════════════════════════
with tabs[3]:
    R = get_R()
    if R is None: no_data(); st.stop()
    rp = st.session_state["rp"]
    hn, an = rp["hn"], rp["an"]
    fm = FinanceManager; br = R["br"]
    od = rp["odds_dict"]

    # MULTIGOAL
    st.markdown(sh_("🎲","MULTIGOAL"), unsafe_allow_html=True)
    mg_map = {"0-1":od["mg_01"],"1-2":od["mg_12"],"2-3":od["mg_23"],
              "3-4":od["mg_34"],"4-5":od["mg_45"]}
    st.plotly_chart(multigoal_fig(R["mg"],mg_map), use_container_width=True)
    mg_rows=[{"RANGE":k,"PROB%":f"{p*100:.2f}%","FAIR":f"{fm.fair(p):.2f}",
              "BK":f"{mg_map.get(k,0):.2f}" if mg_map.get(k,0) else "—",
              "EDGE%":f"{fm.edge(p,mg_map[k])*100:+.2f}%" if mg_map.get(k,0) else "—",
              "VALUE":"✅" if (mg_map.get(k,0) and mg_map[k]>fm.fair(p)) else "❌"}
             for k,p in R["mg"].items()]
    st.dataframe(pd.DataFrame(mg_rows),use_container_width=True,hide_index=True)

    st.markdown("---")
    # ASIAN HANDICAP
    st.markdown(sh_("📐","ASIAN HANDICAP"), unsafe_allow_html=True)
    ah_ph=[R["ah_data"][str(h)]["home_cover"] for h in R["ah_lines"]]
    ah_pa=[R["ah_data"][str(h)]["away_cover"] for h in R["ah_lines"]]
    st.plotly_chart(asian_hcap_fig(R["ah_lines"],ah_ph,ah_pa),use_container_width=True)
    ah_om={-2.5:od["ah_minus25"],-1.5:od["ah_minus15"],-0.5:od["ah_minus05"],
            0.0:od["ah_zero"],0.5:od["ah_plus05"],1.5:od["ah_plus15"]}
    ah_rows=[]
    for h in R["ah_lines"]:
        d=R["ah_data"][str(h)]; bk=ah_om.get(h,0)
        ph=d["home_cover"]; fair=fm.fair(ph); edge=fm.edge(ph,bk) if bk else 0
        kl=fm.kelly(ph,bk,br) if bk else {"stake":0}
        ah_rows.append({"HC":f"{h:+.1f}","HOME%":f"{ph*100:.1f}%",
                        "AWAY%":f"{d['away_cover']*100:.1f}%",
                        "PUSH%":f"{d.get('push',0)*100:.1f}%","FAIR":f"{fair:.2f}",
                        "BK":f"{bk:.2f}" if bk else "—",
                        "EDGE%":f"{edge*100:+.2f}%" if bk else "—",
                        "STAKE":f"€{kl['stake']:.0f}" if kl["stake"]>0 else "—"})
    st.dataframe(pd.DataFrame(ah_rows),use_container_width=True,hide_index=True)

    st.markdown("---")
    # EH
    st.markdown(sh_("🔢","EUROPEAN HANDICAP"), unsafe_allow_html=True)
    eh_m1=R["eh_m1"]; eh_p1=R["eh_p1"]
    eh_rows=[
        {"HC":f"{hn} -1","HOME%":f"{eh_m1[0]*100:.1f}%","DRAW%":f"{eh_m1[1]*100:.1f}%",
         "AWAY%":f"{eh_m1[2]*100:.1f}%","H FAIR":fm.fair(eh_m1[0]),"BK":od["eh_home_m1"],
         "H EDGE%":f"{fm.edge(eh_m1[0],od['eh_home_m1'])*100:+.2f}%"},
        {"HC":f"{an} -1","HOME%":f"{eh_p1[0]*100:.1f}%","DRAW%":f"{eh_p1[1]*100:.1f}%",
         "AWAY%":f"{eh_p1[2]*100:.1f}%","H FAIR":fm.fair(eh_p1[2]),"BK":od["eh_away_m1"],
         "H EDGE%":f"{fm.edge(eh_p1[2],od['eh_away_m1'])*100:+.2f}%"},
    ]
    st.dataframe(pd.DataFrame(eh_rows),use_container_width=True,hide_index=True)

    st.markdown("---")
    # HT/FT
    st.markdown(sh_("⏱️","HT/FT"), unsafe_allow_html=True)
    st.plotly_chart(htft_fig(R["htft"]),use_container_width=True)
    htft_om={"H/H":od["htft_hh"],"H/D":od["htft_hd"],"H/A":od["htft_ha"],
             "D/H":od["htft_dh"],"D/D":od["htft_dd"],"D/A":od["htft_da"],
             "A/H":od["htft_ah"],"A/D":od["htft_ad"],"A/A":od["htft_aa"]}
    htft_rows=[]
    for combo,prob in R["htft"].items():
        bk=htft_om.get(combo,0); fair=fm.fair(prob)
        edge=fm.edge(prob,bk) if bk else 0
        kl=fm.kelly(prob,bk,br) if bk else {"stake":0}
        htft_rows.append({"HT/FT":combo,"PROB%":f"{prob*100:.2f}%","FAIR":f"{fair:.2f}",
                           "BK":f"{bk:.2f}","EDGE%":f"{edge*100:+.2f}%",
                           "STAKE":f"€{kl['stake']:.0f}" if kl["stake"]>0 else "—",
                           "VALUE":"✅" if (bk and bk>fair) else "❌"})
    st.dataframe(pd.DataFrame(htft_rows),use_container_width=True,hide_index=True)

    st.markdown("---")
    # CARTELLINI
    st.markdown(sh_("🟨","CARTELLINI"), unsafe_allow_html=True)
    cr=R["cards"]
    st.markdown(grid(
        mc_("λ CARDS", f"{cr['lam']:.2f}","Totale atteso","yel"),
        mc_("OVER 2.5",f"{cr['ou25']*100:.1f}%",f"Fair:{fm.fair(cr['ou25']):.2f}","org"),
        mc_("OVER 3.5",f"{cr['ou35']*100:.1f}%",f"Fair:{fm.fair(cr['ou35']):.2f}","red"),
        mc_(f"O{od['cards_line']} MAIN",f"{cr['main']*100:.1f}%",
            f"BK:{od['cards_ou_main']:.2f}|Edge:{fm.edge(cr['main'],od['cards_ou_main'])*100:+.1f}%",
            "grn" if fm.edge(cr["main"],od["cards_ou_main"])>0 else "red"),
    ),unsafe_allow_html=True)
    st.plotly_chart(cards_fig(cr["range"],rp["hcrd"],rp["acrd"]),use_container_width=True)

    st.markdown("---")
    # ANYTIME GOALSCORER
    st.markdown(sh_("⚽","ANYTIME GOALSCORER"), unsafe_allow_html=True)
    if R["gs"]:
        gs_rows=[]
        gs_bk_map = od.get("anytime_goalscorer",{})
        for pn,gs in R["gs"].items():
            bk=gs_bk_map.get(pn,0); fair=gs["fair_odd"]
            edge=fm.edge(gs["anytime"],bk) if bk else 0
            kl=fm.kelly(gs["anytime"],bk,br) if bk else {"stake":0,"pct":0}
            gs_rows.append({"PLAYER":pn,"TEAM":gs["team"].upper(),
                            "λ":f"{gs['lambda']:.4f}",
                            "ANYTIME%":f"{gs['anytime']*100:.1f}%",
                            "BRACE%":f"{gs['brace']*100:.1f}%",
                            "HAT%":f"{gs['hat_trick']*100:.2f}%",
                            "FAIR":f"{fair:.2f}","BK":f"{bk:.2f}" if bk else "—",
                            "EDGE%":f"{edge*100:+.2f}%" if bk else "—",
                            "STAKE":f"€{kl['stake']:.0f}" if kl["stake"]>0 else "—",
                            "VALUE":"✅" if (bk and bk>fair) else "❌"})
        st.dataframe(pd.DataFrame(gs_rows),use_container_width=True,hide_index=True)
    else:
        st.info("Aggiungi giocatori nel Tab INPUT.")

# ════════════════════════════════════════════════════════════════════════
#  TAB 4 — VALUE & KELLY
# ════════════════════════════════════════════════════════════════════════
with tabs[4]:
    R = get_R()
    if R is None: no_data(); st.stop()
    markets = R["markets"]; br = R["br"]
    val_mkt = [m for m in markets if m["value"]]
    t_stake = sum(m["stake"] for m in val_mkt)
    t_ev    = sum(m["ev"]    for m in val_mkt)
    b_edge  = max((m["edge%"] for m in val_mkt), default=0)

    st.markdown(sh_("💰","VALUE BET DETECTOR"), unsafe_allow_html=True)
    st.markdown(grid(
        mc_("VALUE BETS", str(len(val_mkt)), f"su {len(markets)} mercati","grn"),
        mc_("STAKE TOT",  f"€{t_stake:.0f}", f"{t_stake/br*100:.1f}% bankroll","org"),
        mc_("EV TOTALE",  f"€{t_ev:.2f}",    "Expected Value aggregato","grn" if t_ev>0 else "red"),
        mc_("BEST EDGE",  f"{b_edge:.1f}%",   "Massimo vantaggio","yel"),
    ), unsafe_allow_html=True)

    st.markdown(sh_("📋","FULL MARKET TABLE"), unsafe_allow_html=True)
    df = pd.DataFrame(markets)
    df["VALUE"] = df["value"].map({True:"✅",False:"❌"})
    sc = ["market","prob%","fair","bk","edge%","stake","stake%","ev","VALUE","signal"]
    df_s = df[sc].rename(columns={"market":"MERCATO","prob%":"PROB%","fair":"FAIR",
                                   "bk":"BK","edge%":"EDGE%","stake":"STAKE€",
                                   "stake%":"STAKE%","ev":"EV€","signal":"SEGNALE"})
    st.dataframe(
        df_s.style
            .background_gradient(subset=["EDGE%"],cmap="RdYlGn",vmin=-5,vmax=15)
            .format({"PROB%":"{:.2f}%","FAIR":"{:.3f}","BK":"{:.2f}",
                     "EDGE%":"{:+.2f}%","STAKE€":"€{:.2f}","STAKE%":"{:.2f}%","EV€":"€{:.2f}"}),
        use_container_width=True, hide_index=True)

    c1,c2 = st.columns(2)
    with c1: st.plotly_chart(radar_fig(markets),use_container_width=True)
    with c2: st.plotly_chart(kelly_bar(markets,br),use_container_width=True)

    if val_mkt:
        st.markdown(sh_("📐","TOP VALUE BETS — KELLY DETAIL"), unsafe_allow_html=True)
        for i,m in enumerate(sorted(val_mkt,key=lambda x:-x["edge%"])[:6],1):
            bw = min(int(m["edge%"]*5),100)
            ec = "#00ff88" if m["edge%"]>5 else "#ffcc00"
            st.markdown(f"""
            <div class="market-row">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                  <span style="color:#8888aa;font-size:.57rem;letter-spacing:.18em;">#{i} VALUE BET</span>
                  <div style="color:#ff6600;font-size:.88rem;font-weight:700;margin-top:3px;">{m['market']}</div>
                  <div style="color:#8888aa;font-size:.63rem;margin-top:2px;">
                    Prob {m['prob%']:.1f}% → Fair {m['fair']:.2f} → BK {m['bk']:.2f}
                  </div>
                </div>
                <div style="display:flex;gap:16px;flex-wrap:wrap;">
                  <div style="text-align:center;"><div style="font-size:.57rem;color:#8888aa;">EDGE</div>
                    <div style="font-size:1.05rem;font-weight:700;color:{ec};">{m['edge%']:+.2f}%</div></div>
                  <div style="text-align:center;"><div style="font-size:.57rem;color:#8888aa;">STAKE</div>
                    <div style="font-size:1.05rem;font-weight:700;color:#e8e8f0;">€{m['stake']:.2f}</div></div>
                  <div style="text-align:center;"><div style="font-size:.57rem;color:#8888aa;">EV</div>
                    <div style="font-size:1.05rem;font-weight:700;color:{'#00ff88' if m['ev']>0 else '#ff3355'};">€{m['ev']:.2f}</div></div>
                </div>
              </div>
              <div style="height:2px;background:#1e1e35;border-radius:2px;margin-top:9px;">
                <div style="height:2px;width:{bw}%;background:linear-gradient(90deg,#ff6600,#ffcc00);"></div>
              </div>
            </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════
#  TAB 5 — MONTE CARLO
# ════════════════════════════════════════════════════════════════════════
with tabs[5]:
    R = get_R()
    if R is None: no_data(); st.stop()
    rp = st.session_state["rp"]
    hn, an = rp["hn"], rp["an"]
    mc = R["mc"]

    st.markdown(sh_("🎲",f"MONTE CARLO — {rp['n_sim']:,} SIM"), unsafe_allow_html=True)
    st.markdown(grid(
        mc_("HOME WIN", f"{mc['hw']*100:.1f}%","MC freq","org"),
        mc_("DRAW",     f"{mc['dr']*100:.1f}%","MC freq","yel"),
        mc_("AWAY WIN", f"{mc['aw']*100:.1f}%","MC freq","blu"),
        mc_("OVER 2.5", f"{mc['ov25']*100:.1f}%",f"BTTS:{mc['btts']*100:.1f}%","grn"),
    ),unsafe_allow_html=True)
    st.markdown(grid(
        mc_("μ GOALS",  f"{mc['mu']:.3f}",f"σ={mc['sig']:.3f}","yel"),
        mc_("CI 2.5%",  f"{mc['ci_lo']:.2f}","Percentile basso","red"),
        mc_("CI 97.5%", f"{mc['ci_hi']:.2f}","Percentile alto","grn"),
        mc_("OVER 3.5", f"{mc['ov35']*100:.1f}%",f"O4.5:{mc['ov45']*100:.1f}%","pur"),
    ),unsafe_allow_html=True)

    st.plotly_chart(mc_fig(mc),use_container_width=True)

    c1,c2 = st.columns(2)
    with c1:
        st.markdown(sh_("🎯","TOP RISULTATI ESATTI (MC)"), unsafe_allow_html=True)
        df_mc = pd.DataFrame(mc["top_scores"],columns=["SCORE","FREQ%"])
        st.dataframe(df_mc.style.background_gradient(subset=["FREQ%"],cmap="YlOrRd")
                       .format({"FREQ%":"{:.2f}%"}),
                     use_container_width=True,hide_index=True)
    with c2:
        st.markdown(sh_("📊","POISSON vs MONTE CARLO"), unsafe_allow_html=True)
        cmp = pd.DataFrame([
            {"METODO":"Poisson","HOME%":f"{R['ph']*100:.1f}%","DRAW%":f"{R['pd']*100:.1f}%",
             "AWAY%":f"{R['pa']*100:.1f}%","O2.5%":f"{R['ov25']*100:.1f}%"},
            {"METODO":"MC","HOME%":f"{mc['hw']*100:.1f}%","DRAW%":f"{mc['dr']*100:.1f}%",
             "AWAY%":f"{mc['aw']*100:.1f}%","O2.5%":f"{mc['ov25']*100:.1f}%"},
        ])
        st.dataframe(cmp,use_container_width=True,hide_index=True)
        d = abs(R["ph"]-mc["hw"])*100
        stab = "🟢 ALTA" if d<1.5 else ("🟡 MEDIA" if d<3.5 else "🔴 BASSA")
        st.markdown(f"""
        <div style="margin-top:12px;padding:14px 16px;background:#12121e;
                    border:1px solid #1e1e35;border-radius:6px;">
          <div style="font-size:.57rem;color:#8888aa;letter-spacing:.15em;">STABILITÀ</div>
          <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin-top:4px;">{stab}</div>
          <div style="font-size:.63rem;color:#8888aa;margin-top:3px;">Δ Home: {d:.2f} pp</div>
        </div>""",unsafe_allow_html=True)

    # Variance Cloud
    st.markdown(sh_("🌡️","NUVOLA DI VARIANZA"), unsafe_allow_html=True)
    hgr = np.array(mc["hg_raw"][:5000])
    agr = np.array(mc["ag_raw"][:5000])
    fig_c = go.Figure(go.Histogram2dContour(
        x=agr+np.random.normal(0,.15,len(agr)),
        y=hgr+np.random.normal(0,.15,len(hgr)),
        colorscale=[[0,"#0a0a0f"],[.3,"#1a1a3e"],[.65,"#ff6600"],[1,"#ffcc00"]],
        contours=dict(showlabels=True,labelfont=dict(size=8,color="white")),
        showscale=False,ncontours=14))
    fig_c.add_shape(type="line",x0=-.5,x1=8,y0=.5,y1=.5,
                    line=dict(color="#ff3355",width=1,dash="dot"))
    fig_c.add_shape(type="line",x0=.5,x1=.5,y0=-.5,y1=8,
                    line=dict(color="#00aaff",width=1,dash="dot"))
    fig_c.update_layout(**PL,title=_ptitle("VARIANCE CLOUD — 5K SIMULATIONS"),
                        xaxis_title=an+" Goals",yaxis_title=hn+" Goals",height=400)
    st.plotly_chart(fig_c,use_container_width=True)

# ════════════════════════════════════════════════════════════════════════
#  TAB 6 — AI CROSS-CHECK
# ════════════════════════════════════════════════════════════════════════
with tabs[6]:
    R = get_R()
    if R is None: no_data(); st.stop()
    rp = st.session_state["rp"]
    hn, an = rp["hn"], rp["an"]
    mc = R["mc"]
    val_mkt = [m for m in R["markets"] if m["value"]]

    vb_txt = "\n".join(
        [f"  - {m['market']}: Edge {m['edge%']:+.2f}%, Stake €{m['stake']:.2f}"
         for m in val_mkt]
    ) or "  Nessuna value bet rilevata"

    # Top value exact scores
    top_es = [s for s in R["top_scores"]
              if rp["odds_dict"].get("exact_scores",{}).get(s["score"],0) > s["fair_odd"]]
    es_txt = "\n".join([f"  - ES {s['score']}: {s['prob_pct']:.3f}%"
                        for s in top_es[:5]]) or "  Nessuna"

    summary = f"""
```

COMPETIZIONE: {rp[‘country’].split()[-1]} — {rp[‘competition’]}
MATCH: {hn} vs {an}
1X2:   Home {R[‘ph’]*100:.1f}%  Draw {R[‘pd’]*100:.1f}%  Away {R[‘pa’]*100:.1f}%
GOALS: O1.5={R[‘ov15’]*100:.1f}%  O2.5={R[‘ov25’]*100:.1f}%  O3.5={R[‘ov35’]*100:.1f}%
BTTS:  {R[‘bttsy’]*100:.1f}%   λH={R[‘lam_h’]:.3f}  λA={R[‘lam_a’]:.3f}
MOST LIKELY SCORE: {R[‘top_scores’][0][‘score’]} ({R[‘top_scores’][0][‘prob_pct’]:.3f}%)
MC:    μ={mc[‘mu’]:.2f} ± σ={mc[‘sig’]:.2f}  CI=[{mc[‘ci_lo’]:.1f}–{mc[‘ci_hi’]:.1f}]
HT/FT TOP: {max(R[‘htft’].items(),key=lambda x:x[1])[0]} → {max(R[‘htft’].values())*100:.1f}%
VALUE BETS:
{vb_txt}
VALUE EXACT SCORES:
{es_txt}”””

```
    st.markdown(f"""
    <div style="background:#12121e;border:1px solid #1e1e35;border-radius:6px;
                padding:15px;font-size:.68rem;color:#8888aa;
                font-family:'IBM Plex Mono',monospace;white-space:pre-wrap;line-height:1.8;">
```

{summary}
</div>”””,unsafe_allow_html=True)

```
    qual = rp.get("qual_notes","")
    if st.button("🧠 AVVIA AI CROSS-CHECK"):
        if not gemini_key:
            st.error("⚠️ Inserisci Gemini API Key nella sidebar!")
        else:
            ctx = qual.strip() or "Nessun contesto qualitativo fornito."
            with st.spinner("Gemini analizza retroscena..."):
                try:
                    ai_txt = SmartParser(gemini_key).qualitative(ctx, summary)
                    pos = ai_txt.lower().count("positivo")
                    neg = ai_txt.lower().count("negativo")
                    vc  = "pos" if pos >= neg else "neg"
                    vt  = "🟢 SEGNALE CONFERMATO" if vc=="pos" else "🔴 SEGNALE INDEBOLITO"
                    vc2 = "positive" if vc=="pos" else "negative"
                    st.markdown(f"""
                    <div class="vbox {vc2}">
                      <div style="font-size:.57rem;color:#8888aa;letter-spacing:.18em;margin-bottom:5px;">
                        AI QUALITATIVE VERDICT — {rp['competition'].upper()}
                      </div>
                      <div style="font-size:1rem;font-weight:700;
                                  color:{'#00ff88' if vc=='pos' else '#ff3355'};
                                  margin-bottom:14px;">{vt}</div>
                      <div style="font-size:.75rem;color:#e8e8f0;line-height:1.9;
                                  white-space:pre-wrap;font-family:'IBM Plex Mono',monospace;">
```

{ai_txt}
</div>
</div>”””,unsafe_allow_html=True)
except Exception as e:
st.error(f”Errore: {e}”)

```
    # DECISION BOARD
    st.markdown("---")
    st.markdown(sh_("📋","DECISION BOARD — TOP BETS"), unsafe_allow_html=True)
    all_val = sorted(val_mkt + [
        {"market":f"ES {s['score']}",
         "edge%": FinanceManager.edge(s["prob"], rp["odds_dict"]["exact_scores"].get(s["score"],0))*100,
         "stake": FinanceManager.kelly(s["prob"], rp["odds_dict"]["exact_scores"].get(s["score"],0), R["br"])["stake"],
         "ev":    FinanceManager.kelly(s["prob"], rp["odds_dict"]["exact_scores"].get(s["score"],0), R["br"])["ev"],
         "bk":    rp["odds_dict"]["exact_scores"].get(s["score"],0),
         "prob%": s["prob_pct"],
         "fair":  s["fair_odd"],
         "signal":"🟢 STRONG" if FinanceManager.edge(s["prob"],rp["odds_dict"]["exact_scores"].get(s["score"],0))>0.05 else "🟡 WATCH",
         "value": True}
        for s in top_es if rp["odds_dict"]["exact_scores"].get(s["score"],0)>1
    ], key=lambda x: -x["edge%"])[:6]

    if all_val:
        for i,m in enumerate(all_val,1):
            bw = min(int(m["edge%"]*5),100)
            ec = "#00ff88" if m["edge%"]>5 else "#ffcc00"
            st.markdown(f"""
            <div class="market-row">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <span style="color:#8888aa;font-size:.57rem;">#{i}</span>&nbsp;
                  <span style="color:#ff6600;font-weight:700;">{m['market']}</span>&nbsp;
                  <span class="vbadge pos">{m['signal']}</span>
                </div>
                <div style="display:flex;gap:14px;">
                  <span style="color:{ec};font-weight:700;">{m['edge%']:+.2f}%</span>
                  <span style="color:#e8e8f0;">€{m['stake']:.2f}</span>
                  <span style="color:{'#00ff88' if m['ev']>0 else '#ff3355'};">EV €{m['ev']:.2f}</span>
                </div>
              </div>
              <div style="height:2px;background:#1e1e35;border-radius:2px;margin-top:8px;">
                <div style="height:2px;width:{bw}%;background:linear-gradient(90deg,#ff6600,#ffcc00);"></div>
              </div>
            </div>""",unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="vbox neg">
          <strong style="color:#ff3355;">⛔ NESSUNA BET CONSIGLIATA</strong><br>
          <span style="color:#8888aa;font-size:.7rem;">
          Il modello non rileva edge positivo. Conserva il bankroll.
          </span>
        </div>""",unsafe_allow_html=True)

    # Disclaimer
    st.markdown("""
    <div style="margin-top:20px;padding:11px 15px;background:#0f0f1a;border:1px solid #1e1e35;
                border-radius:4px;font-size:.59rem;color:#444466;line-height:1.8;">
      ⚠️ DISCLAIMER: Strumento educativo e di ricerca quantitativa.
      Non costituisce consulenza finanziaria o invito al gioco d'azzardo.
      Il trading sportivo comporta rischi di perdita del capitale.
      Gioca responsabilmente. Vietato ai minori di 18 anni.
    </div>""",unsafe_allow_html=True)
```

if **name** == “**main**”:
main()
