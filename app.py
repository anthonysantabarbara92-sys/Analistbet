# -*- coding: utf-8 -*-
# QUANTUM FOOTBALL ANALYTICS ENGINE v5.0
# Ottimizzato per Anthony -- scommettitore intermedio, pre-match
# Mercati: 1X2, O/U, BTTS, Multigoal, Risultato Esatto, HT/FT, Angoli, Cartellini

import streamlit as st
import numpy as np
from scipy.stats import poisson
import json, re, warnings
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import anthropic

warnings.filterwarnings('ignore')

# ==============================================================================
#  CSS
# ==============================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
:root {
  --bg0:#0d0d0d; --bg1:#141414; --bg2:#1a1a1a; --bg3:#202020;
  --br1:#2a2a2a; --br2:#333;
  --org:#ff6b35; --grn:#00c896; --red:#ff3b5c;
  --yel:#ffd166; --blu:#4cc9f0; --pur:#7b2fff;
  --t1:#f0f0f0; --t2:#888; --t3:#555;
  --fm:'Inter',sans-serif;
}
html,body,[class*="css"]{font-family:var(--fm)!important;background:var(--bg0)!important;color:var(--t1)!important;}
.stApp{background:var(--bg0)!important;}
[data-testid="stSidebar"]{background:var(--bg1)!important;border-right:1px solid var(--br1)!important;}

/* HEADER */
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);
  border:1px solid var(--br1);border-left:4px solid var(--org);
  border-radius:10px;padding:20px 24px;margin-bottom:20px;}
.header h1{font-size:1.4rem;font-weight:700;color:var(--org);margin:0;letter-spacing:-.01em;}
.header .sub{font-size:.75rem;color:var(--t2);margin-top:6px;}
.match-title{font-size:1.1rem;font-weight:600;color:var(--t1);margin-top:8px;}

/* SEZIONI */
.section{background:var(--bg1);border:1px solid var(--br1);
  border-radius:10px;padding:18px 20px;margin-bottom:16px;}
.section-title{font-size:.65rem;font-weight:600;color:var(--t2);
  letter-spacing:.15em;text-transform:uppercase;margin-bottom:14px;
  padding-bottom:8px;border-bottom:1px solid var(--br1);}

/* RACCOMANDAZIONI */
.rec-card{border-radius:10px;padding:16px 20px;margin-bottom:12px;position:relative;overflow:hidden;}
.rec-card.best{background:linear-gradient(135deg,rgba(0,200,150,.12),rgba(0,200,150,.04));
  border:1px solid rgba(0,200,150,.3);}
.rec-card.value{background:linear-gradient(135deg,rgba(255,209,102,.1),rgba(255,209,102,.03));
  border:1px solid rgba(255,209,102,.25);}
.rec-card.long{background:linear-gradient(135deg,rgba(76,201,240,.1),rgba(76,201,240,.03));
  border:1px solid rgba(76,201,240,.2);}
.rec-card.novalue{background:rgba(255,59,92,.05);border:1px solid rgba(255,59,92,.2);}
.rec-badge{display:inline-block;font-size:.58rem;font-weight:700;letter-spacing:.12em;
  text-transform:uppercase;padding:3px 10px;border-radius:20px;margin-bottom:10px;}
.rec-badge.best{background:rgba(0,200,150,.2);color:var(--grn);}
.rec-badge.value{background:rgba(255,209,102,.2);color:var(--yel);}
.rec-badge.long{background:rgba(76,201,240,.2);color:var(--blu);}
.rec-badge.novalue{background:rgba(255,59,92,.15);color:var(--red);}
.rec-market{font-size:1rem;font-weight:600;color:var(--t1);margin-bottom:4px;}
.rec-desc{font-size:.75rem;color:var(--t2);margin-bottom:12px;line-height:1.5;}
.rec-nums{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;}
.rec-num{background:rgba(255,255,255,.04);border-radius:6px;padding:8px 10px;text-align:center;}
.rec-num .rn-label{font-size:.55rem;color:var(--t2);text-transform:uppercase;letter-spacing:.1em;}
.rec-num .rn-val{font-size:.95rem;font-weight:700;margin-top:2px;}
.rec-num .rn-val.grn{color:var(--grn);}
.rec-num .rn-val.yel{color:var(--yel);}
.rec-num .rn-val.red{color:var(--red);}
.rec-num .rn-val.blu{color:var(--blu);}
.rec-num .rn-val.org{color:var(--org);}
.semaforo{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;}
.semaforo.verde{background:var(--grn);box-shadow:0 0 8px var(--grn);}
.semaforo.giallo{background:var(--yel);box-shadow:0 0 8px var(--yel);}
.semaforo.rosso{background:var(--red);box-shadow:0 0 8px var(--red);}

/* MERCATI */
.mkt-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;}
.mkt-row{background:var(--bg2);border:1px solid var(--br1);border-radius:8px;
  padding:12px 14px;display:flex;justify-content:space-between;align-items:center;}
.mkt-row.highlight{border-left:3px solid var(--grn);}
.mkt-row.warn{border-left:3px solid var(--red);}
.mkt-row.neutral{border-left:3px solid var(--br2);}
.mkt-name{font-size:.72rem;color:var(--t2);font-weight:500;}
.mkt-prob{font-size:1rem;font-weight:700;}
.mkt-quota{font-size:.68rem;color:var(--t2);margin-top:2px;}
.mkt-fair{font-size:.62rem;padding:2px 6px;border-radius:4px;margin-left:6px;}
.mkt-fair.ok{background:rgba(0,200,150,.15);color:var(--grn);}
.mkt-fair.no{background:rgba(255,59,92,.15);color:var(--red);}

/* FORMA */
.form-badge{display:inline-block;width:28px;height:28px;border-radius:50%;
  text-align:center;line-height:28px;font-size:.65rem;font-weight:700;margin-right:4px;}
.form-badge.W{background:rgba(0,200,150,.2);color:var(--grn);}
.form-badge.D{background:rgba(255,209,102,.2);color:var(--yel);}
.form-badge.L{background:rgba(255,59,92,.2);color:var(--red);}

/* STATS GRID */
.stats-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px;}
.stat-box{background:var(--bg2);border:1px solid var(--br1);border-radius:8px;
  padding:10px 12px;text-align:center;}
.stat-box .sb-label{font-size:.55rem;color:var(--t2);text-transform:uppercase;letter-spacing:.1em;}
.stat-box .sb-val{font-size:1rem;font-weight:700;color:var(--org);margin-top:3px;}
.stat-box .sb-sub{font-size:.6rem;color:var(--t3);margin-top:2px;}

/* COMBO */
.combo-card{background:linear-gradient(135deg,rgba(123,47,255,.1),rgba(123,47,255,.04));
  border:1px solid rgba(123,47,255,.25);border-radius:10px;padding:14px 18px;margin-top:12px;}
.combo-title{font-size:.62rem;font-weight:700;color:var(--pur);letter-spacing:.12em;
  text-transform:uppercase;margin-bottom:10px;}
.combo-item{display:flex;justify-content:space-between;align-items:center;
  padding:6px 0;border-bottom:1px solid rgba(255,255,255,.05);}
.combo-item:last-child{border-bottom:none;}

/* INPUT */
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stSelectbox>div>div{
  background:var(--bg2)!important;border:1px solid var(--br2)!important;
  color:var(--t1)!important;border-radius:8px!important;}
.stButton>button{background:var(--org)!important;border:none!important;
  color:#fff!important;font-weight:600!important;border-radius:8px!important;
  font-size:.8rem!important;letter-spacing:.02em!important;padding:10px 20px!important;
  width:100%!important;transition:all .2s!important;}
.stButton>button:hover{background:#e55a2b!important;transform:translateY(-1px)!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--bg1)!important;border-bottom:1px solid var(--br1)!important;border-radius:8px 8px 0 0!important;}
.stTabs [data-baseweb="tab"]{font-size:.72rem!important;color:var(--t2)!important;
  background:transparent!important;padding:10px 16px!important;font-weight:500!important;}
.stTabs [aria-selected="true"]{color:var(--org)!important;border-bottom:2px solid var(--org)!important;}
.stExpander{background:var(--bg1)!important;border:1px solid var(--br1)!important;border-radius:10px!important;}
#MainMenu,footer,header,.stDeployButton{visibility:hidden!important;display:none!important;}
</style>
"""

# ==============================================================================
#  COMPETITIONS DATABASE
# ==============================================================================
COMPETITIONS = {
    'Italia': ['Serie A','Serie B','Coppa Italia'],
    'Germania': ['Bundesliga','2. Bundesliga','DFB-Pokal'],
    'Inghilterra': ['Premier League','EFL Championship','FA Cup','EFL Cup'],
    'Francia': ['Ligue 1','Ligue 2','Coupe de France'],
    'Spagna': ['La Liga','LaLiga Hypermotion','Copa del Rey'],
    'Portogallo': ['Liga Portugal','Liga Portugal 2','Taca de Portugal'],
    'Olanda': ['Eredivisie','Eerste Divisie','KNVB Beker'],
    'Belgio': ['Pro League','Challenger Pro League','Coupe de Belgique'],
    'Svezia': ['Allsvenskan','Superettan','Svenska Cupen'],
    'Scozia': ['Scottish Premiership','Scottish Championship','Scottish Cup'],
    'Giappone': ['J1 League','J2 League','Emperors Cup'],
    'Norvegia': ['Eliteserien','1. divisjon','Norgesmesterskapet'],
    'Finlandia': ['Veikkausliiga','Ykkonen','Suomen Cup'],
    'Islanda': ['Urvalsdeild karla','1. deild karla','Islandsbikar'],
}

# ==============================================================================
#  DATA CLASSES
# ==============================================================================
@dataclass
class TeamInput:
    name:         str   = ''
    gf_avg:       float = 1.3
    ga_avg:       float = 1.1
    xg_avg:       float = 1.3
    xga_avg:      float = 1.1
    corners_avg:  float = 5.0
    cards_avg:    float = 2.0
    shots_on_avg: float = 4.5
    form:         str   = ''
    home_gf:      float = 0.0
    home_ga:      float = 0.0
    away_gf:      float = 0.0
    away_ga:      float = 0.0

@dataclass
class MarketResult:
    name:      str
    prob:      float
    fair_odd:  float
    bk_odd:    float   = 0.0
    edge:      float   = 0.0
    semaforo:  str     = 'grigio'
    desc:      str     = ''
    category:  str     = ''

# ==============================================================================
#  ENGINE
# ==============================================================================
class QuantumEngine:
    N = 12

    def __init__(self, home: TeamInput, away: TeamInput):
        self.h = home
        self.a = away
        # Lambda composito
        self.lam_h = max(0.1, (home.gf_avg * 0.6 + home.xg_avg * 0.4) * 0.88 +
                         (away.ga_avg * 0.6 + away.xga_avg * 0.4) * 0.12)
        self.lam_a = max(0.1, (away.gf_avg * 0.6 + away.xg_avg * 0.4) * 0.85 +
                         (home.ga_avg * 0.6 + home.xga_avg * 0.4) * 0.15)

    def matrix(self) -> np.ndarray:
        m = np.zeros((self.N, self.N))
        for i in range(self.N):
            for j in range(self.N):
                m[i, j] = poisson.pmf(i, self.lam_h) * poisson.pmf(j, self.lam_a)
        return m / m.sum()

    def p_1x2(self) -> Tuple[float, float, float]:
        m = self.matrix()
        ph = float(np.tril(m, -1).sum())
        pd = float(np.diag(m).sum())
        pa = float(np.triu(m, 1).sum())
        return ph, pd, pa

    def p_ou(self, line: float) -> Tuple[float, float]:
        m = self.matrix()
        over = 0.0
        for i in range(self.N):
            for j in range(self.N):
                if i + j > line:
                    over += m[i, j]
        return float(over), float(1 - over)

    def p_btts(self) -> Tuple[float, float]:
        m = self.matrix()
        btts = float(sum(m[i,j] for i in range(1,self.N) for j in range(1,self.N)))
        return btts, 1 - btts

    def p_multigoal(self) -> Dict[str, float]:
        m = self.matrix()
        mg = {}
        ranges = [('0-1',0,1),('2-3',2,3),('3-4',3,4),('4-5',4,5),('5+',5,99)]
        for label, lo, hi in ranges:
            mg[label] = float(sum(
                m[i,j] for i in range(self.N) for j in range(self.N)
                if lo <= i+j <= hi
            ))
        return mg

    def p_ht_ft(self) -> Dict[str, float]:
        # HT: use half lambda
        lh2 = self.lam_h / 2
        la2 = self.lam_a / 2
        N2 = 8
        ht = np.zeros((N2, N2))
        for i in range(N2):
            for j in range(N2):
                ht[i,j] = poisson.pmf(i,lh2)*poisson.pmf(j,la2)
        ht /= ht.sum()
        p_ht_h = float(np.tril(ht,-1).sum())
        p_ht_d = float(np.diag(ht).sum())
        p_ht_a = float(np.triu(ht,1).sum())

        ft_h, ft_d, ft_a = self.p_1x2()
        return {
            'HH': p_ht_h * ft_h,
            'HD': p_ht_h * ft_d,
            'HA': p_ht_h * ft_a,
            'DH': p_ht_d * ft_h,
            'DD': p_ht_d * ft_d,
            'DA': p_ht_d * ft_a,
            'AH': p_ht_a * ft_h,
            'AD': p_ht_a * ft_d,
            'AA': p_ht_a * ft_a,
        }

    def top_exact_scores(self, n=6) -> List[Dict]:
        m = self.matrix()
        scores = []
        for i in range(self.N):
            for j in range(self.N):
                prob = float(m[i,j])
                if prob < 1e-5: continue
                scores.append({
                    'score': f'{i}-{j}',
                    'prob': prob,
                    'prob_pct': round(prob*100,2),
                    'fair_odd': round(1/max(prob,1e-6),2),
                    'cat': 'Casa' if i>j else ('Pareggio' if i==j else 'Trasferta'),
                })
        scores.sort(key=lambda x: -x['prob'])
        return scores[:n]

    def p_corners(self, h_avg: float, a_avg: float,
                  line: float = 9.5) -> Tuple[float, float]:
        lam = h_avg + a_avg
        over = 1 - sum(poisson.pmf(k, lam) for k in range(int(line)+1))
        return float(over), float(1-over)

    def p_cards(self, h_avg: float, a_avg: float,
                line: float = 3.5) -> Tuple[float, float]:
        lam = h_avg + a_avg
        over = 1 - sum(poisson.pmf(k, lam) for k in range(int(line)+1))
        return float(over), float(1-over)


# ==============================================================================
#  MARKET BUILDER
# ==============================================================================
def build_markets(eng: QuantumEngine, h: TeamInput, a: TeamInput,
                  odds: Dict) -> List[MarketResult]:
    markets = []
    ph, pd, pa = eng.p_1x2()
    ov15, un15 = eng.p_ou(1.5)
    ov25, un25 = eng.p_ou(2.5)
    ov35, un35 = eng.p_ou(3.5)
    ov45, un45 = eng.p_ou(4.5)
    btts_y, btts_n = eng.p_btts()
    mg = eng.p_multigoal()
    corn_ov, corn_un = eng.p_corners(h.corners_avg, a.corners_avg, 9.5)
    card_ov, card_un = eng.p_cards(h.cards_avg, a.cards_avg, 3.5)

    def make(name, prob, bk_key, category, desc):
        bk = odds.get(bk_key, 0.0)
        fair = round(1/max(prob,0.001), 2)
        edge = round((prob * bk) - 1, 4) if bk > 1 else 0.0
        if bk < 1.5 and bk > 0:
            sem = 'rosso'
        elif edge >= 0.1:
            sem = 'verde'
        elif edge >= 0:
            sem = 'giallo'
        else:
            sem = 'rosso'
        return MarketResult(
            name=name, prob=prob, fair_odd=fair,
            bk_odd=bk, edge=edge, semaforo=sem,
            desc=desc, category=category
        )

    # 1X2
    markets += [
        make(f'1 - {h.name}', ph, 'home', '1X2',
             f'{h.name} vince in casa. Lambda gol attesi: {eng.lam_h:.2f}'),
        make('X - Pareggio', pd, 'draw', '1X2',
             f'Partita equilibrata. Prob pareggio: {pd*100:.1f}%'),
        make(f'2 - {a.name}', pa, 'away', '1X2',
             f'{a.name} vince in trasferta. Lambda gol attesi: {eng.lam_a:.2f}'),
    ]
    # O/U
    markets += [
        make('Over 1.5', ov15, 'over15', 'Over/Under',
             f'Almeno 2 gol nel match. Prob: {ov15*100:.1f}%'),
        make('Under 1.5', un15, 'under15', 'Over/Under',
             f'Massimo 1 gol nel match. Prob: {un15*100:.1f}%'),
        make('Over 2.5', ov25, 'over25', 'Over/Under',
             f'Almeno 3 gol nel match. Prob: {ov25*100:.1f}%'),
        make('Under 2.5', un25, 'under25', 'Over/Under',
             f'Massimo 2 gol nel match. Prob: {un25*100:.1f}%'),
        make('Over 3.5', ov35, 'over35', 'Over/Under',
             f'Almeno 4 gol nel match. Prob: {ov35*100:.1f}%'),
        make('Under 3.5', un35, 'under35', 'Over/Under',
             f'Massimo 3 gol nel match. Prob: {un35*100:.1f}%'),
    ]
    # BTTS
    markets += [
        make('BTTS Si', btts_y, 'btts_y', 'BTTS',
             f'Entrambe le squadre segnano. Prob: {btts_y*100:.1f}%'),
        make('BTTS No', btts_n, 'btts_n', 'BTTS',
             f'Almeno una squadra non segna. Prob: {btts_n*100:.1f}%'),
    ]
    # Multigoal
    for label, key in [('0-1 gol','mg_01'),('2-3 gol','mg_23'),
                       ('3-4 gol','mg_34'),('4+ gol','mg_5p')]:
        mg_key = label.split()[0]
        prob_mg = mg.get(mg_key, 0.0)
        markets.append(make(f'Multigoal {label}', prob_mg, key, 'Multigoal',
                            f'Totale gol nella partita: {label}. Prob: {prob_mg*100:.1f}%'))
    # Angoli
    markets += [
        make('Angoli Over 9.5', corn_ov, 'corners_over', 'Angoli',
             f'Piu di 9 angoli totali. Media casa: {h.corners_avg:.1f}, trasf: {a.corners_avg:.1f}'),
        make('Angoli Under 9.5', corn_un, 'corners_under', 'Angoli',
             f'Meno di 10 angoli totali.'),
    ]
    # Cartellini
    markets += [
        make('Cartellini Over 3.5', card_ov, 'cards_over', 'Cartellini',
             f'Piu di 3 cartellini. Media casa: {h.cards_avg:.1f}, trasf: {a.cards_avg:.1f}'),
        make('Cartellini Under 3.5', card_un, 'cards_under', 'Cartellini',
             f'Meno di 4 cartellini totali.'),
    ]
    return markets


# ==============================================================================
#  RACCOMANDAZIONI
# ==============================================================================
def build_recommendations(markets: List[MarketResult],
                           scores: List[Dict]) -> Dict:
    # Solo mercati con quota inserita
    with_odds = [m for m in markets if m.bk_odd > 1.0]

    # Ordina per edge decrescente
    sorted_m = sorted(with_odds, key=lambda x: -x.edge)

    # BEST BET: miglior equilibrio prob alta + edge positivo + quota >= 1.50
    best_candidates = [m for m in sorted_m
                       if m.edge > 0 and m.bk_odd >= 1.50 and m.prob >= 0.35]
    best = best_candidates[0] if best_candidates else None

    # VALUE BET: buon edge ma prob media (30-55%) + quota >= 1.80
    value_candidates = [m for m in sorted_m
                        if m.edge > 0 and m.bk_odd >= 1.80
                        and 0.25 <= m.prob <= 0.60
                        and m != best]
    value = value_candidates[0] if value_candidates else None

    # LONG SHOT: edge positivo, quota alta >= 2.50, prob piu bassa
    long_candidates = [m for m in sorted_m
                       if m.edge > 0 and m.bk_odd >= 2.50
                       and m != best and m != value]
    long_shot = long_candidates[0] if long_candidates else None

    # COMBO suggerita: best + value se entrambi verdi
    combo = []
    if best and best.semaforo == 'verde':
        combo.append(best)
    if value and value.semaforo in ('verde','giallo'):
        combo.append(value)

    return {
        'best':     best,
        'value':    value,
        'long':     long_shot,
        'combo':    combo,
        'all':      sorted_m,
        'top_score': scores[0] if scores else None,
    }


# ==============================================================================
#  UI HELPERS
# ==============================================================================
def semaforo_html(color: str) -> str:
    return f'<span class="semaforo {color}"></span>'

def render_rec_card(m: MarketResult, tipo: str):
    if m is None:
        st.markdown(
            f'<div class="rec-card novalue">'
            f'<span class="rec-badge novalue">Nessuna scommessa</span>'
            f'<div class="rec-market">Quota non inserita o edge negativo</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        return

    label_map = {
        'best':  ('BEST BET -- Scommessa Principale', 'best'),
        'value': ('VALUE BET -- Buon Valore', 'value'),
        'long':  ('LONG SHOT -- Alto Rischio / Alta Quota', 'long'),
    }
    label, css = label_map[tipo]

    edge_color = 'grn' if m.edge > 0.05 else ('yel' if m.edge > 0 else 'red')
    prob_color = 'grn' if m.prob > 0.5 else ('yel' if m.prob > 0.3 else 'red')

    warn = ''
    if m.bk_odd < 1.5:
        warn = '<div style="font-size:.65rem;color:#ff3b5c;margin-top:8px">⚠️ Quota bassa -- valuta attentamente</div>'

    st.markdown(
        f'<div class="rec-card {css}">'
        f'<span class="rec-badge {css}">{label}</span>'
        f'<div class="rec-market">{semaforo_html(m.semaforo)}{m.name}</div>'
        f'<div class="rec-desc">{m.desc}</div>'
        f'<div class="rec-nums">'
        f'<div class="rec-num"><div class="rn-label">Probabilita</div>'
        f'<div class="rn-val {prob_color}">{m.prob*100:.1f}%</div></div>'
        f'<div class="rec-num"><div class="rn-label">Quota Fair</div>'
        f'<div class="rn-val org">{m.fair_odd:.2f}</div></div>'
        f'<div class="rec-num"><div class="rn-label">Edge %</div>'
        f'<div class="rn-val {edge_color}">{m.edge*100:+.1f}%</div></div>'
        f'</div>{warn}</div>',
        unsafe_allow_html=True
    )

def render_market_row(m: MarketResult):
    if m.bk_odd <= 1.0:
        css = 'neutral'
        quota_str = 'Quota N/D'
        fair_html = ''
    elif m.bk_odd < 1.5:
        css = 'warn'
        quota_str = f'Quota: {m.bk_odd:.2f}'
        fair_html = f'<span class="mkt-fair no">Quota bassa</span>'
    elif m.edge > 0:
        css = 'highlight'
        quota_str = f'Quota: {m.bk_odd:.2f}'
        fair_html = f'<span class="mkt-fair ok">Value +{m.edge*100:.1f}%</span>'
    else:
        css = 'neutral'
        quota_str = f'Quota: {m.bk_odd:.2f}'
        fair_html = f'<span class="mkt-fair no">No value</span>'

    prob_color = 'grn' if m.prob > 0.5 else ('yel' if m.prob > 0.3 else 'red')
    st.markdown(
        f'<div class="mkt-row {css}">'
        f'<div><div class="mkt-name">{semaforo_html(m.semaforo)}{m.name}</div>'
        f'<div class="mkt-quota">{quota_str} | Fair: {m.fair_odd:.2f}{fair_html}</div></div>'
        f'<div style="text-align:right">'
        f'<div class="mkt-prob" style="color:var(--{prob_color})">{m.prob*100:.1f}%</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

def form_html(form_str: str) -> str:
    if not form_str:
        return '<span style="color:#555;font-size:.7rem">Nessun dato</span>'
    html = ''
    for c in form_str[-5:]:
        html += f'<span class="form-badge {c}">{c}</span>'
    return html


# ==============================================================================
#  QUALITATIVE AI
# ==============================================================================
def ai_check(key: str, home: str, away: str, comp: str,
             summary: str, context: str) -> str:
    if not key:
        return ''
    try:
        client = anthropic.Anthropic(api_key=key)
        system = (
            'Sei un analista sportivo esperto. Analizza i fattori qualitativi '
            'della partita e dai 5 considerazioni brevi in italiano. '
            'Formato: - [CATEGORIA] Breve analisi (max 15 parole). '
            'Categorie: INFORTUNI | FORMA | MOTIVAZIONE | TATTICA | METEO/CAMPO'
        )
        msg = client.messages.create(
            model='claude-opus-4-5', max_tokens=600,
            system=system,
            messages=[{'role':'user','content':
                f"Partita: {home} vs {away} -- {comp}\n"
                f"Dati: {summary}\nContesto: {context}"}]
        )
        return msg.content[0].text
    except Exception as e:
        return f'AI non disponibile: {e}'


# ==============================================================================
#  MAIN
# ==============================================================================
def main():
    st.set_page_config(
        page_title='Quantum Football v5',
        page_icon='QF',
        layout='wide',
        initial_sidebar_state='collapsed',
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # Sidebar solo API key
    with st.sidebar:
        st.markdown('**Impostazioni**')
        claude_key = st.text_input('Claude API Key', type='password',
                                   placeholder='sk-ant-...')

    # Header
    st.markdown(
        '<div class="header">'
        '<h1>Quantum Football</h1>'
        '<div class="sub">Analisi pre-match -- Value Betting -- Raccomandazioni AI</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ===========================================================
    # SEZIONE 1 -- CONFIGURA PARTITA
    # ===========================================================
    with st.expander('CONFIGURA PARTITA', expanded=True):
        c1, c2, c3 = st.columns([2,2,2])
        with c1:
            paese = st.selectbox('Paese', list(COMPETITIONS.keys()))
        with c2:
            comp = st.selectbox('Competizione', COMPETITIONS[paese])
        with c3:
            st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)

        c4, c5 = st.columns(2)
        with c4:
            h_name = st.text_input('Squadra Casa', value='')
        with c5:
            a_name = st.text_input('Squadra Trasferta', value='')

        st.markdown('---')
        st.markdown('**Statistiche Casa**')
        hc1,hc2,hc3,hc4 = st.columns(4)
        with hc1: h_gf  = st.number_input('GF/gara',    0.0,10.0,1.4,0.1,key='hgf')
        with hc2: h_ga  = st.number_input('GA/gara',    0.0,10.0,1.1,0.1,key='hga')
        with hc3: h_xg  = st.number_input('xG/gara',    0.0,10.0,1.3,0.1,key='hxg')
        with hc4: h_xga = st.number_input('xGA/gara',   0.0,10.0,1.0,0.1,key='hxga')
        hc5,hc6,hc7 = st.columns(3)
        with hc5: h_cor = st.number_input('Angoli/gara',0.0,20.0,5.0,0.5,key='hcor')
        with hc6: h_crd = st.number_input('Cartellini', 0.0,10.0,2.0,0.5,key='hcrd')
        with hc7: h_sot = st.number_input('Tiri porta', 0.0,20.0,4.5,0.5,key='hsot')
        h_form = st.text_input('Forma (es. WDWLW)', value='', key='hform',
                               help='Inserisci gli ultimi 5 risultati: W=Vinta D=Pareggio L=Persa')

        st.markdown('**Statistiche Trasferta**')
        ac1,ac2,ac3,ac4 = st.columns(4)
        with ac1: a_gf  = st.number_input('GF/gara',    0.0,10.0,1.2,0.1,key='agf')
        with ac2: a_ga  = st.number_input('GA/gara',    0.0,10.0,1.2,0.1,key='aga')
        with ac3: a_xg  = st.number_input('xG/gara',    0.0,10.0,1.1,0.1,key='axg')
        with ac4: a_xga = st.number_input('xGA/gara',   0.0,10.0,1.1,0.1,key='axga')
        ac5,ac6,ac7 = st.columns(3)
        with ac5: a_cor = st.number_input('Angoli/gara',0.0,20.0,4.5,0.5,key='acor')
        with ac6: a_crd = st.number_input('Cartellini', 0.0,10.0,2.0,0.5,key='acrd')
        with ac7: a_sot = st.number_input('Tiri porta', 0.0,20.0,4.0,0.5,key='asot')
        a_form = st.text_input('Forma (es. LWDWW)', value='', key='aform')

    # ===========================================================
    # SEZIONE QUOTE
    # ===========================================================
    with st.expander('QUOTE BOOKMAKER (opzionale ma consigliato)', expanded=False):
        st.markdown('<div style="font-size:.72rem;color:#888;margin-bottom:12px">Inserisci le quote di Sportium per sbloccare Edge% e Raccomandazioni.</div>', unsafe_allow_html=True)
        qc1,qc2,qc3 = st.columns(3)
        with qc1:
            q_home = st.number_input('Quota 1 (Casa)',     1.0,50.0,0.0,0.05,key='qh')
            q_ov15 = st.number_input('Over 1.5',           1.0,50.0,0.0,0.05,key='qo15')
            q_ov25 = st.number_input('Over 2.5',           1.0,50.0,0.0,0.05,key='qo25')
            q_ov35 = st.number_input('Over 3.5',           1.0,50.0,0.0,0.05,key='qo35')
        with qc2:
            q_draw = st.number_input('Quota X (Pareggio)', 1.0,50.0,0.0,0.05,key='qd')
            q_un15 = st.number_input('Under 1.5',          1.0,50.0,0.0,0.05,key='qu15')
            q_un25 = st.number_input('Under 2.5',          1.0,50.0,0.0,0.05,key='qu25')
            q_un35 = st.number_input('Under 3.5',          1.0,50.0,0.0,0.05,key='qu35')
        with qc3:
            q_away  = st.number_input('Quota 2 (Trasf.)',  1.0,50.0,0.0,0.05,key='qa')
            q_bttsy = st.number_input('BTTS Si',           1.0,50.0,0.0,0.05,key='qby')
            q_bttsn = st.number_input('BTTS No',           1.0,50.0,0.0,0.05,key='qbn')
        st.markdown('**Mercati secondari**')
        sc1,sc2,sc3,sc4 = st.columns(4)
        with sc1: q_corn_ov = st.number_input('Angoli Over 9.5',  1.0,50.0,0.0,0.05,key='qcov')
        with sc2: q_corn_un = st.number_input('Angoli Under 9.5', 1.0,50.0,0.0,0.05,key='qcun')
        with sc3: q_card_ov = st.number_input('Cart. Over 3.5',   1.0,50.0,0.0,0.05,key='qkov')
        with sc4: q_card_un = st.number_input('Cart. Under 3.5',  1.0,50.0,0.0,0.05,key='qkun')

    # ===========================================================
    # INFO AGGIUNTIVE
    # ===========================================================
    with st.expander('INFO AGGIUNTIVE (opzionale)', expanded=False):
        ca1, ca2 = st.columns(2)
        with ca1:
            h2h = st.text_area('Testa a Testa (H2H)',
                               placeholder='es. Lazio 2-1 Atalanta, Atalanta 0-0 Lazio...',
                               height=80, key='h2h')
            infortuni = st.text_area('Infortuni / Squalifiche',
                                     placeholder='es. Immobile out, Lookman in dubbio...',
                                     height=80, key='inj')
        with ca2:
            h_stats_ht = st.text_input('Statistiche Casa in casa (GF-GA)',
                                       placeholder='es. 1.8-0.9', key='hhome')
            a_stats_aw = st.text_input('Statistiche Trasferta fuori (GF-GA)',
                                       placeholder='es. 1.1-1.3', key='aaway')
            note_extra = st.text_area('Note extra / contesto',
                                      placeholder='Motivazioni, meteo, arbitro...',
                                      height=60, key='note')

    # PULSANTE ANALIZZA
    col_btn = st.columns([1,2,1])[1]
    with col_btn:
        analizza = st.button('ANALIZZA PARTITA', use_container_width=True)

    if not analizza and 'result_v5' not in st.session_state:
        st.markdown(
            '<div style="text-align:center;color:#555;padding:40px;font-size:.8rem">'
            'Inserisci i dati e clicca ANALIZZA PARTITA</div>',
            unsafe_allow_html=True
        )
        return

    if analizza:
        if not h_name or not a_name:
            st.error('Inserisci il nome di entrambe le squadre!')
            return

        home = TeamInput(
            name=h_name, gf_avg=h_gf, ga_avg=h_ga,
            xg_avg=h_xg, xga_avg=h_xga,
            corners_avg=h_cor, cards_avg=h_crd,
            shots_on_avg=h_sot, form=h_form.upper()
        )
        away = TeamInput(
            name=a_name, gf_avg=a_gf, ga_avg=a_ga,
            xg_avg=a_xg, xga_avg=a_xga,
            corners_avg=a_cor, cards_avg=a_crd,
            shots_on_avg=a_sot, form=a_form.upper()
        )
        odds = {
            'home':q_home,'draw':q_draw,'away':q_away,
            'over15':q_ov15,'under15':q_un15,
            'over25':q_ov25,'under25':q_un25,
            'over35':q_ov35,'under35':q_un35,
            'btts_y':q_bttsy,'btts_n':q_bttsn,
            'corners_over':q_corn_ov,'corners_under':q_corn_un,
            'cards_over':q_card_ov,'cards_under':q_card_un,
        }
        eng   = QuantumEngine(home, away)
        mkts  = build_markets(eng, home, away, odds)
        scores= eng.top_exact_scores(6)
        htft  = eng.p_ht_ft()
        recs  = build_recommendations(mkts, scores)

        st.session_state['result_v5'] = {
            'home':home,'away':away,'comp':comp,'paese':paese,
            'eng':eng,'mkts':mkts,'scores':scores,'htft':htft,'recs':recs,
            'h2h':h2h,'infortuni':infortuni,'note':note_extra,
            'h_stats_ht':h_stats_ht,'a_stats_aw':a_stats_aw,
            'claude_key':claude_key,
        }

    R = st.session_state.get('result_v5')
    if not R: return

    home   = R['home']
    away   = R['away']
    recs   = R['recs']
    mkts   = R['mkts']
    scores = R['scores']
    htft   = R['htft']
    eng    = R['eng']

    # Match title
    st.markdown(
        f'<div class="header" style="padding:14px 20px;margin-top:8px">'
        f'<div class="match-title">{home.name} vs {away.name}</div>'
        f'<div class="sub">{R["paese"]} -- {R["comp"]} | '
        f'Lambda: {eng.lam_h:.2f} vs {eng.lam_a:.2f}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ===========================================================
    # RACCOMANDAZIONI (prima di tutto)
    # ===========================================================
    st.markdown('<div class="section"><div class="section-title">Raccomandazioni</div>', unsafe_allow_html=True)

    r1, r2, r3 = st.columns(3)
    with r1: render_rec_card(recs['best'],  'best')
    with r2: render_rec_card(recs['value'], 'value')
    with r3: render_rec_card(recs['long'],  'long')

    # Combo suggerita
    if len(recs['combo']) >= 2:
        combo_items = ''
        combo_quota = 1.0
        for m in recs['combo']:
            combo_quota *= m.bk_odd if m.bk_odd > 1 else 1.0
            combo_items += (
                f'<div class="combo-item">'
                f'<span style="font-size:.75rem">{m.name}</span>'
                f'<span style="font-size:.75rem;color:var(--yel)">{m.bk_odd:.2f}</span>'
                f'</div>'
            )
        st.markdown(
            f'<div class="combo-card">'
            f'<div class="combo-title">Combo Suggerita</div>'
            f'{combo_items}'
            f'<div style="text-align:right;font-size:.8rem;color:var(--pur);margin-top:8px">'
            f'Quota combo: <strong>{combo_quota:.2f}</strong></div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # ===========================================================
    # TABS DETTAGLI
    # ===========================================================
    t1,t2,t3,t4,t5,t6 = st.tabs([
        '1X2 & O/U',
        'BTTS & Multigoal',
        'Risultato Esatto',
        'Angoli & Cartellini',
        'Squadre & H2H',
        'AI Check',
    ])

    # -- TAB 1: 1X2 + O/U
    with t1:
        st.markdown('<div class="section-title">1X2 -- Esito Finale</div>', unsafe_allow_html=True)
        for m in [x for x in mkts if x.category == '1X2']:
            render_market_row(m)

        st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Over / Under Gol</div>', unsafe_allow_html=True)

        # HT/FT top 3
        ht_sorted = sorted(htft.items(), key=lambda x:-x[1])[:4]
        st.markdown('<div class="section-title" style="margin-top:14px">Primo Tempo / Secondo Tempo (top 4)</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        labels_map = {
            'HH':f'{home.name}/{home.name}','HD':f'{home.name}/X',
            'HA':f'{home.name}/{away.name}','DH':f'X/{home.name}',
            'DD':'X/X','DA':f'X/{away.name}',
            'AH':f'{away.name}/{home.name}','AD':f'{away.name}/X',
            'AA':f'{away.name}/{away.name}',
        }
        for idx,(k,v) in enumerate(ht_sorted):
            with cols[idx]:
                st.markdown(
                    f'<div class="stat-box">'
                    f'<div class="sb-label">{labels_map.get(k,k)}</div>'
                    f'<div class="sb-val">{v*100:.1f}%</div>'
                    f'<div class="sb-sub">Fair: {1/max(v,0.001):.2f}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        for m in [x for x in mkts if x.category == 'Over/Under']:
            render_market_row(m)

    # -- TAB 2: BTTS + Multigoal
    with t2:
        st.markdown('<div class="section-title">BTTS -- Entrambe Segnano</div>', unsafe_allow_html=True)
        for m in [x for x in mkts if x.category == 'BTTS']:
            render_market_row(m)
        st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Multigoal -- Totale Gol</div>', unsafe_allow_html=True)
        for m in [x for x in mkts if x.category == 'Multigoal']:
            render_market_row(m)

    # -- TAB 3: Risultato esatto
    with t3:
        st.markdown('<div class="section-title">Risultati Esatti piu Probabili</div>', unsafe_allow_html=True)
        cols3 = st.columns(3)
        for idx, sc in enumerate(scores):
            with cols3[idx % 3]:
                color = 'grn' if sc['cat']=='Casa' else ('yel' if sc['cat']=='Pareggio' else 'blu')
                st.markdown(
                    f'<div class="stat-box">'
                    f'<div class="sb-label">{sc["cat"]}</div>'
                    f'<div class="sb-val" style="font-size:1.5rem">{sc["score"]}</div>'
                    f'<div class="sb-sub">{sc["prob_pct"]:.2f}% | Fair: {sc["fair_odd"]:.1f}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # -- TAB 4: Angoli + Cartellini
    with t4:
        st.markdown('<div class="section-title">Angoli</div>', unsafe_allow_html=True)
        for m in [x for x in mkts if x.category == 'Angoli']:
            render_market_row(m)
        st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Cartellini</div>', unsafe_allow_html=True)
        for m in [x for x in mkts if x.category == 'Cartellini']:
            render_market_row(m)

        # Tiri in porta info
        st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Tiri in Porta</div>', unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        with tc1:
            st.markdown(
                f'<div class="stat-box">'
                f'<div class="sb-label">{home.name}</div>'
                f'<div class="sb-val">{home.shots_on_avg:.1f}</div>'
                f'<div class="sb-sub">tiri/partita</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with tc2:
            st.markdown(
                f'<div class="stat-box">'
                f'<div class="sb-label">{away.name}</div>'
                f'<div class="sb-val">{away.shots_on_avg:.1f}</div>'
                f'<div class="sb-sub">tiri/partita</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    # -- TAB 5: Squadre + H2H
    with t5:
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown(f'<div class="section-title">{home.name} -- Casa</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="stats-grid">'
                f'<div class="stat-box"><div class="sb-label">GF/gara</div><div class="sb-val">{home.gf_avg:.2f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">GA/gara</div><div class="sb-val">{home.ga_avg:.2f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">xG/gara</div><div class="sb-val">{home.xg_avg:.2f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">Lambda</div><div class="sb-val">{eng.lam_h:.2f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">Angoli</div><div class="sb-val">{home.corners_avg:.1f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">Cartellini</div><div class="sb-val">{home.cards_avg:.1f}</div></div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if home.form:
                st.markdown(f'<div style="margin-top:10px">{form_html(home.form)}</div>', unsafe_allow_html=True)
            if R.get('h_stats_ht'):
                st.markdown(f'<div style="font-size:.7rem;color:#888;margin-top:8px">In casa: {R["h_stats_ht"]}</div>', unsafe_allow_html=True)

        with sc2:
            st.markdown(f'<div class="section-title">{away.name} -- Trasferta</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="stats-grid">'
                f'<div class="stat-box"><div class="sb-label">GF/gara</div><div class="sb-val">{away.gf_avg:.2f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">GA/gara</div><div class="sb-val">{away.ga_avg:.2f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">xG/gara</div><div class="sb-val">{away.xg_avg:.2f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">Lambda</div><div class="sb-val">{eng.lam_a:.2f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">Angoli</div><div class="sb-val">{away.corners_avg:.1f}</div></div>'
                f'<div class="stat-box"><div class="sb-label">Cartellini</div><div class="sb-val">{away.cards_avg:.1f}</div></div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if away.form:
                st.markdown(f'<div style="margin-top:10px">{form_html(away.form)}</div>', unsafe_allow_html=True)
            if R.get('a_stats_aw'):
                st.markdown(f'<div style="font-size:.7rem;color:#888;margin-top:8px">Fuori casa: {R["a_stats_aw"]}</div>', unsafe_allow_html=True)

        if R.get('h2h'):
            st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Testa a Testa (H2H)</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="background:var(--bg2);border:1px solid var(--br1);'
                f'border-radius:8px;padding:12px 16px;font-size:.75rem;color:#ccc;line-height:1.8">'
                f'{R["h2h"]}</div>',
                unsafe_allow_html=True
            )
        if R.get('infortuni'):
            st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Infortuni / Squalifiche</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="background:rgba(255,59,92,.06);border:1px solid rgba(255,59,92,.2);'
                f'border-radius:8px;padding:12px 16px;font-size:.75rem;color:#ff8fa3;line-height:1.8">'
                f'{R["infortuni"]}</div>',
                unsafe_allow_html=True
            )

    # -- TAB 6: AI Check
    with t6:
        st.markdown('<div class="section-title">Analisi Qualitativa (Claude AI)</div>', unsafe_allow_html=True)
        if not R.get('claude_key'):
            st.markdown(
                '<div style="color:#555;font-size:.8rem;padding:20px;text-align:center">'
                'Inserisci la Claude API Key nella sidebar per attivare l\'analisi AI.</div>',
                unsafe_allow_html=True
            )
        else:
            context_parts = []
            if R.get('h2h'):        context_parts.append(f'H2H: {R["h2h"]}')
            if R.get('infortuni'):  context_parts.append(f'Infortuni: {R["infortuni"]}')
            if R.get('note'):       context_parts.append(f'Note: {R["note"]}')

            ph, pd, pa = eng.p_1x2()
            ov25, _ = eng.p_ou(2.5)
            btts, _ = eng.p_btts()
            summary = (
                f'{home.name} vs {away.name} -- {R["comp"]}\n'
                f'1X2: Casa {ph*100:.1f}% | X {pd*100:.1f}% | Trasf {pa*100:.1f}%\n'
                f'Over 2.5: {ov25*100:.1f}% | BTTS: {btts*100:.1f}%\n'
                f'Lambda: {eng.lam_h:.2f} vs {eng.lam_a:.2f}'
            )

            if 'ai_result' not in st.session_state or \
               st.session_state.get('ai_match') != f'{home.name}{away.name}':
                with st.spinner('Claude analizza...'):
                    ai_txt = ai_check(
                        R['claude_key'], home.name, away.name, R['comp'],
                        summary, ' | '.join(context_parts) or 'Nessun contesto aggiuntivo'
                    )
                st.session_state['ai_result'] = ai_txt
                st.session_state['ai_match']  = f'{home.name}{away.name}'

            ai_txt = st.session_state.get('ai_result','')
            if ai_txt:
                lines = [l.strip() for l in ai_txt.split('\n') if l.strip()]
                for line in lines:
                    if line.startswith('-'):
                        st.markdown(
                            f'<div style="background:var(--bg2);border-left:3px solid var(--org);'
                            f'border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px;'
                            f'font-size:.78rem;color:#ddd;line-height:1.5">{line[1:].strip()}</div>',
                            unsafe_allow_html=True
                        )


if __name__ == '__main__':
    main()
