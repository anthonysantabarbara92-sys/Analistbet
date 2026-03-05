# -*- coding: utf-8 -*-
# QUANTUM FOOTBALL ANALYTICS v6.0
# Flusso: Cerca Dati Auto -> Modifica -> Analizza -> Reset
# Fonti: The Odds API + Football-Data.org + Transfermarkt + Claude backup
# Mercati: 30+ mercati + combo automatiche (doppiette + terzine)

import streamlit as st
import numpy as np
from scipy.stats import poisson
import requests, json, re, warnings, anthropic
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import itertools
warnings.filterwarnings('ignore')

# ==============================================================================
# CSS
# ==============================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
:root {
  --bg0:#0d0d0d; --bg1:#141414; --bg2:#1a1a1a; --bg3:#222;
  --br1:#2a2a2a; --br2:#333;
  --org:#ff6b35; --grn:#00c896; --red:#ff3b5c;
  --yel:#ffd166; --blu:#4cc9f0; --pur:#9b5de5;
  --t1:#f0f0f0; --t2:#888; --t3:#555;
  --fm:'Inter',sans-serif;
}
html,body,[class*="css"]{font-family:var(--fm)!important;background:var(--bg0)!important;color:var(--t1)!important;}
.stApp{background:var(--bg0)!important;}
[data-testid="stSidebar"]{background:var(--bg1)!important;border-right:1px solid var(--br1)!important;}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);border:1px solid var(--br1);
  border-left:4px solid var(--org);border-radius:12px;padding:20px 24px;margin-bottom:16px;}
.header h1{font-size:1.5rem;font-weight:700;color:var(--org);margin:0;}
.header .sub{font-size:.72rem;color:var(--t2);margin-top:5px;}
.match-badge{display:inline-block;background:rgba(255,107,53,.1);border:1px solid rgba(255,107,53,.3);
  border-radius:20px;padding:4px 14px;font-size:.75rem;color:var(--org);margin-top:8px;}
.section{background:var(--bg1);border:1px solid var(--br1);border-radius:12px;padding:16px 18px;margin-bottom:14px;}
.sec-title{font-size:.62rem;font-weight:600;color:var(--t2);letter-spacing:.18em;
  text-transform:uppercase;padding-bottom:10px;border-bottom:1px solid var(--br1);margin-bottom:12px;}
.banner-ok{background:rgba(0,200,150,.08);border:1px solid rgba(0,200,150,.25);
  border-radius:8px;padding:10px 14px;font-size:.72rem;color:var(--grn);margin:6px 0;}
.banner-err{background:rgba(255,59,92,.08);border:1px solid rgba(255,59,92,.25);
  border-radius:8px;padding:10px 14px;font-size:.72rem;color:var(--red);margin:6px 0;}
.banner-warn{background:rgba(255,209,102,.08);border:1px solid rgba(255,209,102,.25);
  border-radius:8px;padding:10px 14px;font-size:.72rem;color:var(--yel);margin:6px 0;}
.rec-card{border-radius:12px;padding:16px 18px;margin-bottom:10px;}
.rec-card.best{background:linear-gradient(135deg,rgba(0,200,150,.12),rgba(0,200,150,.04));border:1px solid rgba(0,200,150,.3);}
.rec-card.value{background:linear-gradient(135deg,rgba(255,209,102,.1),rgba(255,209,102,.03));border:1px solid rgba(255,209,102,.25);}
.rec-card.long{background:linear-gradient(135deg,rgba(76,201,240,.1),rgba(76,201,240,.03));border:1px solid rgba(76,201,240,.2);}
.rec-card.none{background:rgba(255,59,92,.05);border:1px solid rgba(255,59,92,.15);}
.rec-badge{display:inline-block;font-size:.58rem;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;padding:3px 10px;border-radius:20px;margin-bottom:8px;}
.rec-badge.best{background:rgba(0,200,150,.2);color:var(--grn);}
.rec-badge.value{background:rgba(255,209,102,.2);color:var(--yel);}
.rec-badge.long{background:rgba(76,201,240,.2);color:var(--blu);}
.rec-badge.none{background:rgba(255,59,92,.15);color:var(--red);}
.rec-market{font-size:.95rem;font-weight:600;color:var(--t1);margin-bottom:4px;}
.rec-desc{font-size:.72rem;color:var(--t2);margin-bottom:10px;line-height:1.5;}
.rec-nums{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;}
.rn{background:rgba(255,255,255,.04);border-radius:6px;padding:8px;text-align:center;}
.rn .rl{font-size:.52rem;color:var(--t2);text-transform:uppercase;letter-spacing:.08em;}
.rn .rv{font-size:.9rem;font-weight:700;margin-top:2px;}
.rv.grn{color:var(--grn);} .rv.yel{color:var(--yel);} .rv.red{color:var(--red);}
.rv.org{color:var(--org);} .rv.blu{color:var(--blu);}
.sem{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;vertical-align:middle;}
.sem.verde{background:var(--grn);box-shadow:0 0 6px var(--grn);}
.sem.giallo{background:var(--yel);box-shadow:0 0 6px var(--yel);}
.sem.rosso{background:var(--red);box-shadow:0 0 6px var(--red);}
.mkt-row{background:var(--bg2);border:1px solid var(--br1);border-radius:8px;
  padding:11px 14px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;}
.mkt-row.v-high{border-left:3px solid var(--grn);}
.mkt-row.v-med{border-left:3px solid var(--yel);}
.mkt-row.v-low{border-left:3px solid var(--t3);}
.mkt-row.v-bad{border-left:3px solid var(--red);}
.mkt-name{font-size:.73rem;color:var(--t1);font-weight:500;}
.mkt-sub{font-size:.6rem;color:var(--t2);margin-top:2px;}
.mkt-prob{font-size:.95rem;font-weight:700;}
.combo-card{background:linear-gradient(135deg,rgba(155,93,229,.1),rgba(155,93,229,.03));
  border:1px solid rgba(155,93,229,.25);border-radius:12px;padding:14px 16px;margin-bottom:10px;}
.combo-title{font-size:.6rem;font-weight:700;color:var(--pur);letter-spacing:.12em;
  text-transform:uppercase;margin-bottom:10px;}
.combo-leg{display:flex;justify-content:space-between;padding:5px 0;
  border-bottom:1px solid rgba(255,255,255,.05);font-size:.73rem;}
.combo-leg:last-child{border-bottom:none;}
.combo-footer{display:flex;justify-content:space-between;margin-top:10px;
  padding-top:8px;border-top:1px solid rgba(155,93,229,.2);}
.stat-box{background:var(--bg2);border:1px solid var(--br1);border-radius:8px;
  padding:10px 12px;text-align:center;}
.sb-label{font-size:.55rem;color:var(--t2);text-transform:uppercase;letter-spacing:.08em;}
.sb-val{font-size:1rem;font-weight:700;color:var(--org);margin-top:3px;}
.sb-sub{font-size:.6rem;color:var(--t3);margin-top:2px;}
.form-dot{display:inline-block;width:26px;height:26px;border-radius:50%;
  text-align:center;line-height:26px;font-size:.62rem;font-weight:700;margin-right:3px;}
.form-dot.W{background:rgba(0,200,150,.2);color:var(--grn);}
.form-dot.D{background:rgba(255,209,102,.2);color:var(--yel);}
.form-dot.L{background:rgba(255,59,92,.2);color:var(--red);}
.hist-row{background:var(--bg2);border:1px solid var(--br1);border-radius:8px;
  padding:10px 14px;margin-bottom:6px;font-size:.72rem;}
.stButton>button{background:var(--org)!important;border:none!important;
  color:#fff!important;font-weight:600!important;border-radius:8px!important;
  padding:10px!important;width:100%!important;}
.stButton>button:hover{background:#e55a2b!important;}
button[kind="secondary"]{background:transparent!important;border:1px solid var(--br2)!important;
  color:var(--t2)!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--bg1)!important;border-bottom:1px solid var(--br1)!important;}
.stTabs [data-baseweb="tab"]{font-size:.7rem!important;color:var(--t2)!important;
  background:transparent!important;padding:9px 14px!important;}
.stTabs [aria-selected="true"]{color:var(--org)!important;border-bottom:2px solid var(--org)!important;}
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stSelectbox>div>div{
  background:var(--bg2)!important;border:1px solid var(--br2)!important;
  color:var(--t1)!important;border-radius:8px!important;}
#MainMenu,footer,header,.stDeployButton{visibility:hidden!important;display:none!important;}
</style>
"""

# ==============================================================================
# COMPETITIONS
# ==============================================================================
COMPETITIONS = {
    'Italia':      ['Serie A','Serie B','Coppa Italia'],
    'Germania':    ['Bundesliga','2. Bundesliga','DFB-Pokal'],
    'Inghilterra': ['Premier League','EFL Championship','FA Cup'],
    'Francia':     ['Ligue 1','Ligue 2','Coupe de France'],
    'Spagna':      ['La Liga','LaLiga Hypermotion','Copa del Rey'],
    'Portogallo':  ['Liga Portugal','Liga Portugal 2','Taca de Portugal'],
    'Olanda':      ['Eredivisie','Eerste Divisie'],
    'Belgio':      ['Pro League','Challenger Pro League'],
    'Scozia':      ['Scottish Premiership','Scottish Championship'],
    'Svezia':      ['Allsvenskan','Superettan'],
    'Norvegia':    ['Eliteserien','1. divisjon'],
    'Champions League': ['Champions League'],
    'Europa League':    ['Europa League'],
    'Conference League':['Conference League'],
}

COMP_FD = {
    'Serie A':'SA','Serie B':'SB','Premier League':'PL',
    'EFL Championship':'ELC','Bundesliga':'BL1','2. Bundesliga':'BL2',
    'Ligue 1':'FL1','Ligue 2':'FL2','La Liga':'PD','LaLiga Hypermotion':'SD',
    'Eredivisie':'DED','Pro League':'BSA','Liga Portugal':'PPL',
    'Champions League':'CL','Europa League':'EL','DFB-Pokal':'DFB',
    'FA Cup':'FAC','Copa del Rey':'CDR',
}

COMP_ODDS = {
    'Serie A':'soccer_italy_serie_a','Serie B':'soccer_italy_serie_b',
    'Premier League':'soccer_epl','EFL Championship':'soccer_efl_champ',
    'Bundesliga':'soccer_germany_bundesliga','2. Bundesliga':'soccer_germany_bundesliga2',
    'Ligue 1':'soccer_france_ligue_one','Ligue 2':'soccer_france_ligue_two',
    'La Liga':'soccer_spain_la_liga','LaLiga Hypermotion':'soccer_spain_segunda_division',
    'Eredivisie':'soccer_netherlands_eredivisie','Pro League':'soccer_belgium_first_div',
    'Liga Portugal':'soccer_portugal_primeira_liga',
    'Champions League':'soccer_uefa_champs_league',
    'Europa League':'soccer_uefa_europa_league',
    'Conference League':'soccer_uefa_europa_conference_league',
}

SQUADRE_DEFAULT = ['Lazio','Roma','Inter','Milan','Juventus','Napoli','Atalanta','Fiorentina']
BK_PRIORITY = ['sportium','bet365','unibet','bwin','betway','william_hill','marathonbet']
REQ_H = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept':'application/json, */*','Accept-Language':'it-IT,it;q=0.9',
}

# ==============================================================================
# DATA CLASSES
# ==============================================================================
@dataclass
class TeamData:
    name:str=''; gf:float=1.3; ga:float=1.1; xg:float=1.3; xga:float=1.1
    corners:float=5.0; cards:float=2.0; shots:float=4.5; form:str=''
    matches:int=0; source:str=''

@dataclass
class MarketResult:
    name:str; emoji:str; prob:float; fair:float
    bk:float=0.0; edge:float=0.0; sem:str='grigio'
    desc:str=''; cat:str=''; key:str=''

@dataclass
class ComboResult:
    legs:List[MarketResult]; tipo:str
    prob_combo:float=0.0; quota_combo:float=0.0; edge_combo:float=0.0

# ==============================================================================
# ENGINE
# ==============================================================================
class Engine:
    N = 11
    def __init__(self, h:TeamData, a:TeamData):
        self.h = h; self.a = a
        self.lh = max(0.1, h.gf*0.55 + h.xg*0.35 + a.ga*0.05 + a.xga*0.05)
        self.la = max(0.1, a.gf*0.50 + a.xg*0.35 + h.ga*0.08 + h.xga*0.07)
        self._mat = None

    def mat(self):
        if self._mat is None:
            m = np.array([[poisson.pmf(i,self.lh)*poisson.pmf(j,self.la)
                           for j in range(self.N)] for i in range(self.N)])
            self._mat = m / m.sum()
        return self._mat

    def p1x2(self):
        m = self.mat()
        ph = float(np.tril(m,-1).sum())
        pd = float(np.diag(m).sum())
        pa = float(np.triu(m,1).sum())
        return ph,pd,pa

    def pou(self, line):
        m = self.mat()
        ov = float(sum(m[i,j] for i in range(self.N) for j in range(self.N) if i+j>line))
        return ov, 1-ov

    def pbtts(self):
        m = self.mat()
        y = float(sum(m[i,j] for i in range(1,self.N) for j in range(1,self.N)))
        return y, 1-y

    def pmultigoal(self, lo, hi):
        m = self.mat()
        return float(sum(m[i,j] for i in range(self.N) for j in range(self.N)
                         if lo <= i+j <= (hi if hi<99 else 99)))

    def pdoppia(self):
        ph,pd,pa = self.p1x2()
        return ph+pd, ph+pa, pd+pa

    def pdnb(self):
        ph,pd,pa = self.p1x2()
        tot_nodraw = ph+pa
        return ph/tot_nodraw if tot_nodraw>0 else 0, pa/tot_nodraw if tot_nodraw>0 else 0

    def pht(self):
        lh2,la2 = self.lh/2, self.la/2
        N2=7
        m2 = np.array([[poisson.pmf(i,lh2)*poisson.pmf(j,la2)
                         for j in range(N2)] for i in range(N2)])
        m2 /= m2.sum()
        ph_ht = float(np.tril(m2,-1).sum())
        pd_ht = float(np.diag(m2).sum())
        pa_ht = float(np.triu(m2,1).sum())
        return ph_ht, pd_ht, pa_ht

    def pou_ht(self, line):
        lh2,la2 = self.lh/2, self.la/2
        N2=7
        m2 = np.array([[poisson.pmf(i,lh2)*poisson.pmf(j,la2)
                         for j in range(N2)] for i in range(N2)])
        m2 /= m2.sum()
        ov = float(sum(m2[i,j] for i in range(N2) for j in range(N2) if i+j>line))
        return ov, 1-ov

    def pbtts_ht(self):
        lh2,la2 = self.lh/2, self.la/2
        N2=7
        m2 = np.array([[poisson.pmf(i,lh2)*poisson.pmf(j,la2)
                         for j in range(N2)] for i in range(N2)])
        m2 /= m2.sum()
        y = float(sum(m2[i,j] for i in range(1,N2) for j in range(1,N2)))
        return y, 1-y

    def pbtts_2t(self):
        # Second half: approximate with same lambda split
        lh2,la2 = self.lh/2, self.la/2
        N2=7
        m2 = np.array([[poisson.pmf(i,lh2)*poisson.pmf(j,la2)
                         for j in range(N2)] for i in range(N2)])
        m2 /= m2.sum()
        y = float(sum(m2[i,j] for i in range(1,N2) for j in range(1,N2)))
        return y, 1-y

    def pgol_no_gol_ht(self):
        ov, un = self.pou_ht(0.5)
        return ov, un

    def p_team_scores_both_halves(self, is_home:bool):
        lam = self.lh if is_home else self.la
        lh2 = lam / 2
        p_score_ht = 1 - poisson.pmf(0, lh2)
        p_score_2t = 1 - poisson.pmf(0, lh2)
        return float(p_score_ht * p_score_2t)

    def p_exact_gol(self, n:int):
        m = self.mat()
        return float(sum(m[i,j] for i in range(self.N) for j in range(self.N) if i+j==n))

    def phandicap_eu(self, handicap:int, is_home:bool):
        m = self.mat()
        p = 0.0
        for i in range(self.N):
            for j in range(self.N):
                diff = (i-j) if is_home else (j-i)
                if diff + handicap > 0: p += m[i,j]
        return float(p)

    def p_winning_margin(self, margin:int, is_home:bool):
        m = self.mat()
        p = 0.0
        for i in range(self.N):
            for j in range(self.N):
                diff = (i-j) if is_home else (j-i)
                if diff == margin: p += m[i,j]
        return float(p)

    def p_corners(self, h_avg, a_avg, line=9.5):
        lam = h_avg + a_avg
        ov = 1 - sum(poisson.pmf(k,lam) for k in range(int(line)+1))
        return float(ov), float(1-ov)

    def p_cards(self, h_avg, a_avg, line=3.5):
        lam = h_avg + a_avg
        ov = 1 - sum(poisson.pmf(k,lam) for k in range(int(line)+1))
        return float(ov), float(1-ov)

    def top_scores(self, n=6):
        m = self.mat()
        sc = [{'score':f'{i}-{j}','prob':float(m[i,j]),
               'prob_pct':round(float(m[i,j])*100,2),
               'fair':round(1/max(float(m[i,j]),1e-5),1),
               'cat':'Casa' if i>j else ('Pari' if i==j else 'Trasf')}
              for i in range(self.N) for j in range(self.N) if float(m[i,j])>1e-5]
        sc.sort(key=lambda x:-x['prob'])
        return sc[:n]

    def p_team_goals(self, n:int, is_home:bool):
        lam = self.lh if is_home else self.la
        return float(poisson.pmf(n, lam))

    def p_team_goals_range(self, lo:int, hi:int, is_home:bool):
        lam = self.lh if is_home else self.la
        return float(sum(poisson.pmf(k,lam) for k in range(lo, min(hi+1,self.N))))

    def p_goalscorer(self, player_goals_avg:float):
        # Prob of scoring at least 1 goal given avg per game
        return float(1 - poisson.pmf(0, player_goals_avg))

    def htft_probs(self):
        ph_ht,pd_ht,pa_ht = self.pht()
        ph,pd,pa = self.p1x2()
        return {
            'C/C':ph_ht*ph,'C/X':ph_ht*pd,'C/T':ph_ht*pa,
            'X/C':pd_ht*ph,'X/X':pd_ht*pd,'X/T':pd_ht*pa,
            'T/C':pa_ht*ph,'T/X':pa_ht*pd,'T/T':pa_ht*pa,
        }

# ==============================================================================
# MARKET BUILDER
# ==============================================================================
def make_mkt(name, emoji, prob, bk, cat, key, desc=''):
    fair = round(1/max(prob,0.001),2)
    edge = round((prob*bk)-1, 4) if bk > 1.01 else 0.0
    if bk < 1.5 and bk > 1.01: sem = 'rosso'
    elif edge >= 0.08: sem = 'verde'
    elif edge >= 0.0: sem = 'giallo'
    else: sem = 'rosso'
    return MarketResult(name=name,emoji=emoji,prob=prob,fair=fair,
                        bk=bk,edge=edge,sem=sem,desc=desc,cat=cat,key=key)

def build_markets(eng:Engine, h:TeamData, a:TeamData, odds:Dict) -> List[MarketResult]:
    mk = []
    ph,pd,pa = eng.p1x2()
    p1x,p12,px2 = eng.pdoppia()
    dnb_h,dnb_a = eng.pdnb()
    ov05,un05 = eng.pou(0.5)
    ov15,un15 = eng.pou(1.5)
    ov25,un25 = eng.pou(2.5)
    ov35,un35 = eng.pou(3.5)
    ov45,un45 = eng.pou(4.5)
    btts_y,btts_n = eng.pbtts()
    ov05_ht,un05_ht = eng.pou_ht(0.5)
    ov15_ht,un15_ht = eng.pou_ht(1.5)
    btts_ht_y,_ = eng.pbtts_ht()
    btts_2t_y,_ = eng.pbtts_2t()
    corn_ov,corn_un = eng.p_corners(h.corners, a.corners, 9.5)
    card_ov,card_un = eng.p_cards(h.cards, a.cards, 3.5)
    ph_ht,pd_ht,pa_ht = eng.pht()
    h_both = eng.p_team_scores_both_halves(True)
    a_both = eng.p_team_scores_both_halves(False)

    g = odds.get
    o = lambda k: g(k, 0.0)

    # 1X2
    mk += [
        make_mkt(f'1 - {h.name}','⚽',ph,o('home'),'1X2','home',
                 f'{h.name} vince. Lambda casa: {eng.lh:.2f}'),
        make_mkt('X - Pareggio','🤝',pd,o('draw'),'1X2','draw',
                 f'Partita equilibrata. Prob pari: {pd*100:.1f}%'),
        make_mkt(f'2 - {a.name}','⚽',pa,o('away'),'1X2','away',
                 f'{a.name} vince in trasferta. Lambda trasf: {eng.la:.2f}'),
    ]
    # Doppia Chance
    mk += [
        make_mkt(f'1X - {h.name} o Pari','🔄',p1x,o('dc_1x'),'Doppia Chance','dc_1x',
                 f'{h.name} non perde. Prob: {p1x*100:.1f}%'),
        make_mkt(f'12 - {h.name} o {a.name}','🔄',p12,o('dc_12'),'Doppia Chance','dc_12',
                 f'Una delle due squadre vince. Prob: {p12*100:.1f}%'),
        make_mkt(f'X2 - Pari o {a.name}','🔄',px2,o('dc_x2'),'Doppia Chance','dc_x2',
                 f'{a.name} non perde. Prob: {px2*100:.1f}%'),
    ]
    # DNB
    mk += [
        make_mkt(f'DNB {h.name}','🛡️',dnb_h,o('dnb_home'),'Draw No Bet','dnb_home',
                 f'Rimborso se pareggio. Prob vittoria netta: {dnb_h*100:.1f}%'),
        make_mkt(f'DNB {a.name}','🛡️',dnb_a,o('dnb_away'),'Draw No Bet','dnb_away',
                 f'Rimborso se pareggio. Prob vittoria netta: {dnb_a*100:.1f}%'),
    ]
    # Over/Under
    mk += [
        make_mkt('Over 0.5','📈',ov05,o('over05'),'Over/Under','over05','Almeno 1 gol'),
        make_mkt('Under 0.5','📉',un05,o('under05'),'Over/Under','under05','Nessun gol'),
        make_mkt('Over 1.5','📈',ov15,o('over15'),'Over/Under','over15','Almeno 2 gol'),
        make_mkt('Under 1.5','📉',un15,o('under15'),'Over/Under','under15','Massimo 1 gol'),
        make_mkt('Over 2.5','📈',ov25,o('over25'),'Over/Under','over25','Almeno 3 gol'),
        make_mkt('Under 2.5','📉',un25,o('under25'),'Over/Under','under25','Massimo 2 gol'),
        make_mkt('Over 3.5','📈',ov35,o('over35'),'Over/Under','over35','Almeno 4 gol'),
        make_mkt('Under 3.5','📉',un35,o('under35'),'Over/Under','under35','Massimo 3 gol'),
        make_mkt('Over 4.5','📈',ov45,o('over45'),'Over/Under','over45','Almeno 5 gol'),
    ]
    # BTTS
    mk += [
        make_mkt('BTTS Si','⚽⚽',btts_y,o('btts_y'),'BTTS','btts_y','Entrambe segnano'),
        make_mkt('BTTS No','🚫',btts_n,o('btts_n'),'BTTS','btts_n','Almeno una non segna'),
    ]
    # Primo Tempo
    mk += [
        make_mkt('Over 0.5 1T','📈',ov05_ht,o('over05_ht'),'Primo Tempo','over05_ht','Almeno 1 gol nel 1T'),
        make_mkt('Over 1.5 1T','📈',ov15_ht,o('over15_ht'),'Primo Tempo','over15_ht','Almeno 2 gol nel 1T'),
        make_mkt('Nessun gol 1T','🚫',un05_ht,o('no_gol_ht'),'Primo Tempo','no_gol_ht','0-0 al 45min'),
        make_mkt('BTTS 1T','⚽⚽',btts_ht_y,o('btts_ht'),'Primo Tempo','btts_ht','Entrambe segnano nel 1T'),
        make_mkt('BTTS 2T','⚽⚽',btts_2t_y,o('btts_2t'),'Secondo Tempo','btts_2t','Entrambe segnano nel 2T'),
    ]
    # Squadra segna in entrambi i tempi
    mk += [
        make_mkt(f'{h.name} segna entrambi tempi','⚽',h_both,o('h_both_halves'),'Speciali','h_both',
                 f'{h.name} segna sia nel 1T che nel 2T'),
        make_mkt(f'{a.name} segna entrambi tempi','⚽',a_both,o('a_both_halves'),'Speciali','a_both',
                 f'{a.name} segna sia nel 1T che nel 2T'),
    ]
    # Multigoal totale
    for label,lo,hi,key in [('0-1',0,1,'mg01'),('2-3',2,3,'mg23'),
                              ('3-4',3,4,'mg34'),('4-5',4,5,'mg45'),('5+',5,99,'mg5p')]:
        p = eng.pmultigoal(lo,hi)
        mk.append(make_mkt(f'Multigoal {label}','🎯',p,o(f'mg_{key}'),
                           'Multigoal Totale',f'mg_{key}',f'Totale gol: {label}'))
    # Multigoal Casa
    for n,key in [(0,'h0'),(1,'h1'),(2,'h2'),(3,'h3')]:
        p = eng.p_team_goals(n, True)
        mk.append(make_mkt(f'{h.name} {n} gol','🏠',p,o(f'hg{key}'),
                           'Gol Casa',f'hg{key}',f'{h.name} segna esattamente {n} gol'))
    p_h2p = eng.p_team_goals_range(2,99,True)
    mk.append(make_mkt(f'{h.name} 2+ gol','🏠',p_h2p,o('hg2p'),
                       'Gol Casa','hg2p',f'{h.name} segna almeno 2 gol'))
    # Multigoal Ospite
    for n,key in [(0,'a0'),(1,'a1'),(2,'a2'),(3,'a3')]:
        p = eng.p_team_goals(n, False)
        mk.append(make_mkt(f'{a.name} {n} gol','✈️',p,o(f'ag{key}'),
                           'Gol Ospite',f'ag{key}',f'{a.name} segna esattamente {n} gol'))
    p_a2p = eng.p_team_goals_range(2,99,False)
    mk.append(make_mkt(f'{a.name} 2+ gol','✈️',p_a2p,o('ag2p'),
                       'Gol Ospite','ag2p',f'{a.name} segna almeno 2 gol'))
    # Numero esatto gol totali
    for n in range(6):
        p = eng.p_exact_gol(n)
        mk.append(make_mkt(f'Esattamente {n} gol','🔢',p,o(f'exact{n}'),
                           'Gol Esatti',f'exact{n}',f'Totale esatto: {n} gol'))
    # Handicap europeo
    for hdp,lbl in [(-1,'Casa -1'),(1,'Ospite -1'),(-2,'Casa -2')]:
        is_home = hdp < 0
        p = eng.phandicap_eu(abs(hdp), is_home)
        team = h.name if is_home else a.name
        mk.append(make_mkt(f'EH {lbl}','⚖️',p,o(f'eh_{hdp}'),
                           'Handicap',f'eh_{hdp}',f'{team} vince con {abs(hdp)} gol di scarto'))
    # Winning margin
    for margin,lbl in [(1,'Vince di 1'),(2,'Vince di 2'),(3,'Vince di 3+')]:
        for is_home,team_lbl in [(True,h.name),(False,a.name)]:
            if margin == 3:
                p = sum(eng.p_winning_margin(m,is_home) for m in range(3,8))
            else:
                p = eng.p_winning_margin(margin,is_home)
            mk.append(make_mkt(f'{team_lbl} {lbl}','🏆',p,o(f'wm_{team_lbl}_{margin}'),
                               'Winning Margin',f'wm_{is_home}_{margin}',
                               f'{team_lbl} vince con scarto {lbl.lower()}'))
    # Angoli
    mk += [
        make_mkt('Angoli Over 9.5','📐',corn_ov,o('corn_ov'),'Angoli','corn_ov',
                 f'Oltre 9 angoli. Media: {h.corners:.1f}+{a.corners:.1f}={h.corners+a.corners:.1f}'),
        make_mkt('Angoli Under 9.5','📐',corn_un,o('corn_un'),'Angoli','corn_un','Meno di 10 angoli'),
    ]
    # Cartellini
    mk += [
        make_mkt('Cartellini Over 3.5','🟨',card_ov,o('card_ov'),'Cartellini','card_ov',
                 f'Oltre 3 cartellini. Media: {h.cards:.1f}+{a.cards:.1f}={h.cards+a.cards:.1f}'),
        make_mkt('Cartellini Under 3.5','🟨',card_un,o('card_un'),'Cartellini','card_un','Meno di 4 cartellini'),
    ]
    return mk

# ==============================================================================
# COMBO BUILDER
# ==============================================================================
def build_combos(markets:List[MarketResult], h_name:str, a_name:str) -> List[ComboResult]:
    combos = []

    def make_combo(keys, tipo):
        legs = [m for m in markets if m.key in keys]
        if len(legs) < 2: return None
        prob = 1.0
        for l in legs: prob *= l.prob
        quota = 1.0
        for l in legs: quota *= l.bk if l.bk > 1.01 else l.fair
        edge = (prob * quota) - 1
        return ComboResult(legs=legs, tipo=tipo,
                          prob_combo=prob, quota_combo=round(quota,2),
                          edge_combo=round(edge,4))

    # Combo classiche 2 esiti
    pairs = [
        (['home','over25'],'1X2 + Over 2.5'),
        (['home','over15'],'1X2 + Over 1.5'),
        (['home','btts_y'],'1X2 + BTTS Si'),
        (['away','over25'],'1X2 + Over 2.5'),
        (['away','btts_y'],'1X2 + BTTS Si'),
        (['dc_1x','under25'],'Doppia Chance + Under 2.5'),
        (['dc_x2','under25'],'Doppia Chance + Under 2.5'),
        (['dc_12','over15'],'Doppia Chance + Over 1.5'),
        (['btts_y','over25'],'BTTS + Over 2.5'),
        (['btts_y','over15'],'BTTS + Over 1.5'),
        (['btts_n','under25'],'BTTS No + Under 2.5'),
    ]
    for keys,tipo in pairs:
        c = make_combo(keys, tipo)
        if c: combos.append(c)

    # Combo multigoal totale
    mg_combos = [
        (['mg_mg23','btts_y'],'Multigoal 2-3 + BTTS Si'),
        (['mg_mg23','home'],'Multigoal 2-3 + Casa vince'),
        (['mg_mg23','over05_ht'],'Multigoal 2-3 + Gol 1T'),
        (['mg_mg34','btts_y'],'Multigoal 3-4 + BTTS Si'),
        (['mg_mg01','btts_n'],'Multigoal 0-1 + BTTS No'),
    ]
    for keys,tipo in mg_combos:
        c = make_combo(keys, tipo)
        if c: combos.append(c)

    # Combo gol per squadra
    team_combos = [
        (['hgh1','aga0'],f'{h_name} 1 gol + {a_name} 0 gol'),
        (['hgh1','aga1'],f'{h_name} 1 gol + {a_name} 1 gol'),
        (['hgh2','aga0'],f'{h_name} 2 gol + {a_name} 0 gol'),
        (['hgh2','aga1'],f'{h_name} 2 gol + {a_name} 1 gol'),
        (['hg2p','aga0'],f'{h_name} 2+ gol + {a_name} 0 gol'),
        (['hg2p','ag2p'],f'Entrambe 2+ gol'),
        (['hgh1','ag2p'],f'{h_name} 1 gol + {a_name} 2+ gol'),
    ]
    for keys,tipo in team_combos:
        c = make_combo(keys, tipo)
        if c: combos.append(c)

    # Terzine automatiche - trova le migliori
    mkt_with_bk = [m for m in markets if m.bk > 1.01]
    # Prendi i top 8 per prob
    top8 = sorted(mkt_with_bk, key=lambda x: -x.prob)[:8]
    for trio in itertools.combinations(top8, 3):
        cats = {t.cat for t in trio}
        # Terzine interessanti: mercati diversi
        if len(cats) >= 2:
            prob = trio[0].prob * trio[1].prob * trio[2].prob
            quota = trio[0].bk * trio[1].bk * trio[2].bk
            edge = (prob * quota) - 1
            tipo = ' + '.join(t.name for t in trio)
            combos.append(ComboResult(
                legs=list(trio), tipo=tipo,
                prob_combo=prob, quota_combo=round(quota,2),
                edge_combo=round(edge,4)
            ))

    # Ordina per prob_combo decrescente
    combos.sort(key=lambda x: -x.prob_combo)
    return combos[:20]  # top 20

# ==============================================================================
# RACCOMANDAZIONI
# ==============================================================================
def build_recs(markets:List[MarketResult]) -> Dict:
    with_bk = [m for m in markets if m.bk > 1.01]
    by_edge = sorted(with_bk, key=lambda x: -x.edge)

    best = next((m for m in by_edge
                 if m.edge > 0 and m.bk >= 1.50 and m.prob >= 0.35), None)
    value = next((m for m in by_edge
                  if m.edge > 0 and m.bk >= 1.80 and 0.25 <= m.prob <= 0.65
                  and m != best), None)
    long_s = next((m for m in by_edge
                   if m.edge > 0 and m.bk >= 2.50
                   and m != best and m != value), None)
    return {'best':best,'value':value,'long':long_s,'all':by_edge}

# ==============================================================================
# DATA FETCHING
# ==============================================================================
def fetch_fd(fd_key, team_name):
    try:
        h = {**REQ_H,'X-Auth-Token':fd_key}
        r = requests.get('https://api.football-data.org/v4/teams',
                         headers=h, params={'name':team_name}, timeout=10)
        if r.status_code != 200: return None, f'FD HTTP {r.status_code}'
        teams = r.json().get('teams',[])
        if not teams:
            r2 = requests.get('https://api.football-data.org/v4/teams',
                              headers=h, params={'name':team_name[:5]}, timeout=10)
            if r2.status_code == 200:
                tl = team_name.lower()
                teams = [t for t in r2.json().get('teams',[])
                         if tl in t.get('name','').lower()]
        if not teams: return None, f'Squadra {team_name} non trovata'
        tid = teams[0]['id']
        r3 = requests.get(f'https://api.football-data.org/v4/teams/{tid}/matches',
                          headers=h, params={'status':'FINISHED','limit':12}, timeout=10)
        if r3.status_code != 200: return None, f'Matches HTTP {r3.status_code}'
        matches = r3.json().get('matches',[])
        if not matches: return None, 'Nessuna partita trovata'
        gf_l,ga_l,form_l = [],[],[]
        tn = team_name.lower()
        for m in matches[-10:]:
            ht = m.get('homeTeam',{}).get('name','').lower()
            sc = m.get('score',{}).get('fullTime',{})
            hg,ag = sc.get('home'),sc.get('away')
            if hg is None or ag is None: continue
            is_home = tn in ht or ht in tn
            gf = hg if is_home else ag
            ga = ag if is_home else hg
            gf_l.append(gf); ga_l.append(ga)
            form_l.append('W' if gf>ga else ('D' if gf==ga else 'L'))
        if not gf_l: return None, 'Nessuna partita valida'
        n = len(gf_l)
        return TeamData(
            name=team_name, gf=round(sum(gf_l)/n,2), ga=round(sum(ga_l)/n,2),
            xg=round(sum(gf_l)/n*0.93,2), xga=round(sum(ga_l)/n*0.93,2),
            form=''.join(form_l[-5:]), matches=n, source='football-data.org'
        ), 'ok'
    except Exception as e:
        return None, str(e)

def fetch_odds(odds_key, sport_key, home, away):
    try:
        p = {'apiKey':odds_key,'regions':'eu','markets':'h2h,totals,btts',
             'oddsFormat':'decimal','bookmakers':','.join(BK_PRIORITY)}
        r = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds',
                         params=p, headers=REQ_H, timeout=12)
        if r.status_code != 200: return {}, f'Odds API HTTP {r.status_code}'
        data = r.json()
        if not isinstance(data,list): return {}, 'Formato non valido'
        hl,al = home.lower(), away.lower()
        event = None
        for ev in data:
            eh = ev.get('home_team','').lower()
            ea = ev.get('away_team','').lower()
            if (hl in eh or eh in hl) and (al in ea or ea in al):
                event = ev; break
        if not event: return {}, f'{home} vs {away} non trovata'
        bks = event.get('bookmakers',[])
        chosen = None
        for prio in BK_PRIORITY:
            for bk in bks:
                if bk.get('key','') == prio: chosen = bk; break
            if chosen: break
        if not chosen and bks: chosen = bks[0]
        if not chosen: return {}, 'Nessun bookmaker trovato'
        odds = {'_bk': chosen.get('title', chosen.get('key',''))}
        for mkt in chosen.get('markets',[]):
            key = mkt.get('key','')
            outs = {o['name']:o['price'] for o in mkt.get('outcomes',[])}
            if key == 'h2h':
                odds['home'] = outs.get(event.get('home_team',''),0.0)
                odds['away'] = outs.get(event.get('away_team',''),0.0)
                odds['draw'] = outs.get('Draw',0.0)
            elif key == 'totals':
                for o in mkt.get('outcomes',[]):
                    pt = o.get('point',0); nm = o.get('name',''); pr = o.get('price',0)
                    if pt==2.5:
                        if nm=='Over': odds['over25']=pr
                        else: odds['under25']=pr
                    elif pt==3.5:
                        if nm=='Over': odds['over35']=pr
                        else: odds['under35']=pr
            elif key == 'btts':
                odds['btts_y'] = outs.get('Yes',0.0)
                odds['btts_n'] = outs.get('No',0.0)
        return odds, 'ok'
    except Exception as e:
        return {}, str(e)

def fetch_injuries_tm(team_name):
    try:
        h = {**REQ_H,'Referer':'https://www.transfermarkt.it'}
        r = requests.get('https://www.transfermarkt.it/schnellsuche/ergebnis/schnellsuche',
                         headers=h, params={'query':team_name}, timeout=10)
        if r.status_code != 200: return [], 'TM non raggiungibile'
        m = re.search(r'href="(/[^"]+/startseite/verein/\d+[^"]*)"', r.text)
        if not m: return [], f'{team_name} non trovata su TM'
        inj_url = 'https://www.transfermarkt.it' + re.sub(r'/startseite/','/verletzungen/',m.group(1))
        r2 = requests.get(inj_url, headers=h, timeout=10)
        if r2.status_code != 200: return [], 'Pagina infortuni non raggiungibile'
        rows = re.findall(r'<tr[^>]*class="[^"]*(?:odd|even)[^"]*"[^>]*>(.*?)</tr>', r2.text, re.DOTALL)
        injuries = []
        for row in rows[:20]:
            txt = re.sub(r'<[^>]+>',' ', row)
            txt = re.sub(r'\s+',' ',txt).strip()
            if len(txt)<5: continue
            if any(kw in txt.lower() for kw in ['infort','lesion','dubbio','sospett','assent']):
                parts = txt.split()
                if len(parts)>=2:
                    injuries.append({'name':' '.join(parts[:2]),
                                     'status':'out' if 'out' in txt.lower() else 'doubt',
                                     'info':txt[:80]})
        return injuries, 'ok'
    except Exception as e:
        return [], str(e)

def claude_search_backup(claude_key, home, away, comp, what):
    if not claude_key: return {}
    try:
        client = anthropic.Anthropic(api_key=claude_key)
        prompt = (
            f'Trova i dati per {home} vs {away} ({comp}). '
            f'Cosa cerco: {what}. '
            f'Rispondi SOLO con JSON, niente altro. '
            f'Per le statistiche: {{"gf_home":x,"ga_home":x,"gf_away":x,"ga_away":x}} '
            f'Per le quote: {{"home":x,"draw":x,"away":x,"over25":x,"under25":x,"btts_y":x,"btts_n":x}}'
        )
        msg = client.messages.create(
            model='claude-opus-4-5', max_tokens=500,
            messages=[{'role':'user','content':prompt}]
        )
        txt = re.sub(r'```json|```','',msg.content[0].text).strip()
        return json.loads(txt)
    except:
        return {}

# ==============================================================================
# UI HELPERS
# ==============================================================================
def sem_html(color):
    return f'<span class="sem {color}"></span>'

def form_html(form_str):
    if not form_str: return '<span style="color:#555;font-size:.7rem">N/D</span>'
    return ''.join(f'<span class="form-dot {c}">{c}</span>' for c in form_str[-5:])

def render_rec(m, tipo):
    labels = {
        'best':  ('🥇 BEST BET','best','La scommessa con miglior equilibrio probabilita + valore'),
        'value': ('💰 VALUE BET','value','Buon valore, quota interessante'),
        'long':  ('🎲 LONG SHOT','long','Alto rischio, alta quota — gioca solo una parte'),
    }
    lbl,css,subtitle = labels[tipo]
    if m is None:
        st.markdown(
            f'<div class="rec-card none"><span class="rec-badge none">Nessuna scommessa</span>'
            f'<div class="rec-market">Quota non inserita o edge negativo</div></div>',
            unsafe_allow_html=True
        )
        return
    ec = 'grn' if m.edge>0.08 else ('yel' if m.edge>0 else 'red')
    pc = 'grn' if m.prob>0.5 else ('yel' if m.prob>0.3 else 'red')
    warn = '<div style="font-size:.65rem;color:var(--red);margin-top:8px">⚠️ Quota bassa — attento</div>' if m.bk<1.5 and m.bk>1 else ''
    st.markdown(
        f'<div class="rec-card {css}">'
        f'<span class="rec-badge {css}">{lbl}</span>'
        f'<div style="font-size:.62rem;color:var(--t2);margin-bottom:6px">{subtitle}</div>'
        f'<div class="rec-market">{sem_html(m.sem)}{m.emoji} {m.name}</div>'
        f'<div class="rec-desc">{m.desc}</div>'
        f'<div class="rec-nums">'
        f'<div class="rn"><div class="rl">Probabilita</div><div class="rv {pc}">{m.prob*100:.1f}%</div></div>'
        f'<div class="rn"><div class="rl">Quota Fair</div><div class="rv org">{m.fair:.2f}</div></div>'
        f'<div class="rn"><div class="rl">Edge %</div><div class="rv {ec}">{m.edge*100:+.1f}%</div></div>'
        f'</div>{warn}</div>',
        unsafe_allow_html=True
    )

def render_mkt(m:MarketResult):
    if m.bk <= 1.01:
        css = 'v-low'; quota_str = 'Quota N/D'; fair_tag = ''
    elif m.bk < 1.5:
        css = 'v-bad'; quota_str = f'{m.bk:.2f}'
        fair_tag = '<span style="font-size:.58rem;color:var(--red);margin-left:6px">⚠️ Quota bassa</span>'
    elif m.edge >= 0.08:
        css = 'v-high'; quota_str = f'{m.bk:.2f}'
        fair_tag = f'<span style="font-size:.58rem;color:var(--grn);margin-left:6px">✅ +{m.edge*100:.1f}%</span>'
    elif m.edge >= 0:
        css = 'v-med'; quota_str = f'{m.bk:.2f}'
        fair_tag = f'<span style="font-size:.58rem;color:var(--yel);margin-left:6px">⚡ +{m.edge*100:.1f}%</span>'
    else:
        css = 'v-low'; quota_str = f'{m.bk:.2f}'
        fair_tag = f'<span style="font-size:.58rem;color:var(--t3);margin-left:6px">{m.edge*100:+.1f}%</span>'
    pc = 'var(--grn)' if m.prob>0.5 else ('var(--yel)' if m.prob>0.3 else 'var(--t2)')
    st.markdown(
        f'<div class="mkt-row {css}">'
        f'<div><div class="mkt-name">{sem_html(m.sem)}{m.emoji} {m.name}</div>'
        f'<div class="mkt-sub">Fair: {m.fair:.2f} | Bk: {quota_str}{fair_tag}</div></div>'
        f'<div style="text-align:right">'
        f'<div class="mkt-prob" style="color:{pc}">{m.prob*100:.1f}%</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

def render_combo(c:ComboResult):
    ec = 'var(--grn)' if c.edge_combo>0.05 else ('var(--yel)' if c.edge_combo>0 else 'var(--t2)')
    legs_html = ''
    for l in c.legs:
        legs_html += (
            f'<div class="combo-leg">'
            f'<span>{l.emoji} {l.name}</span>'
            f'<span style="color:var(--yel)">{l.bk:.2f if l.bk>1.01 else l.fair:.2f}</span>'
            f'</div>'
        )
    st.markdown(
        f'<div class="combo-card">'
        f'<div class="combo-title">{c.tipo}</div>'
        f'{legs_html}'
        f'<div class="combo-footer">'
        f'<span style="font-size:.7rem;color:var(--t2)">Prob: {c.prob_combo*100:.1f}%</span>'
        f'<span style="font-size:.8rem;font-weight:700;color:{ec}">Quota: {c.quota_combo:.2f}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    st.set_page_config(page_title='Quantum Football v6',page_icon='QF',
                       layout='wide',initial_sidebar_state='collapsed')
    st.markdown(CSS, unsafe_allow_html=True)

    if 'history' not in st.session_state: st.session_state['history'] = []
    if 'step' not in st.session_state: st.session_state['step'] = 'input'

    # Sidebar API keys
    with st.sidebar:
        st.markdown('### Impostazioni')
        fd_key    = st.text_input('Football-Data.org Key', type='password', key='fd_key')
        odds_key  = st.text_input('The Odds API Key', type='password', key='odds_key')
        claude_key= st.text_input('Claude API Key', type='password', key='claude_key')

    # Header
    st.markdown(
        '<div class="header"><h1>⚽ Quantum Football v6.0</h1>'
        '<div class="sub">Dati automatici • 30+ mercati • Combo intelligenti • Value Betting</div></div>',
        unsafe_allow_html=True
    )

    # ===========================================================================
    # STEP 1 — INPUT
    # ===========================================================================
    if st.session_state['step'] == 'input':
        st.markdown('<div class="section"><div class="sec-title">Inserisci Partita</div>', unsafe_allow_html=True)

        c1,c2,c3 = st.columns([2,2,2])
        with c1:
            paese = st.selectbox('Paese', list(COMPETITIONS.keys()), key='paese')
        with c2:
            comp = st.selectbox('Competizione', COMPETITIONS[paese], key='comp')
        with c3:
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        c4,c5 = st.columns(2)
        with c4:
            h_opts = SQUADRE_DEFAULT + ['Altra squadra...']
            h_sel = st.selectbox('Squadra Casa', h_opts, key='h_sel')
            if h_sel == 'Altra squadra...':
                h_name = st.text_input('Nome squadra casa', key='h_custom')
            else:
                h_name = h_sel
        with c5:
            a_opts = SQUADRE_DEFAULT + ['Altra squadra...']
            a_sel = st.selectbox('Squadra Trasferta', a_opts, key='a_sel')
            if a_sel == 'Altra squadra...':
                a_name = st.text_input('Nome squadra trasferta', key='a_custom')
            else:
                a_name = a_sel

        st.markdown('</div>', unsafe_allow_html=True)

        if not fd_key or not odds_key:
            st.markdown(
                '<div class="banner-warn">⚠️ Inserisci le API Key nella sidebar per la raccolta dati automatica</div>',
                unsafe_allow_html=True
            )

        col_btn = st.columns([1,2,1])[1]
        with col_btn:
            cerca = st.button('🔍 CERCA DATI', use_container_width=True)

        if cerca and h_name and a_name:
            st.session_state['h_name'] = h_name
            st.session_state['a_name'] = a_name
            st.session_state['comp']   = comp
            st.session_state['paese']  = paese

            banners = []
            raw = {'h_data':None,'a_data':None,'odds':{},'inj_h':[],'inj_a':[]}

            with st.spinner(f'Statistiche {h_name}...'):
                h_data, msg = fetch_fd(fd_key, h_name) if fd_key else (None,'No FD key')
                if h_data:
                    banners.append(('ok',f'✅ Statistiche {h_name} da football-data.org ({h_data.matches} partite)'))
                    raw['h_data'] = h_data
                else:
                    banners.append(('warn',f'⚠️ Stats {h_name}: {msg} — uso dati default'))
                    if claude_key:
                        backup = claude_search_backup(claude_key,h_name,a_name,comp,'statistiche')
                        if backup:
                            raw['h_data'] = TeamData(name=h_name,gf=backup.get('gf_home',1.3),
                                                      ga=backup.get('ga_home',1.1),source='Claude AI')
                            banners.append(('ok',f'✅ Stats {h_name} da Claude AI (backup)'))

            with st.spinner(f'Statistiche {a_name}...'):
                a_data, msg = fetch_fd(fd_key, a_name) if fd_key else (None,'No FD key')
                if a_data:
                    banners.append(('ok',f'✅ Statistiche {a_name} da football-data.org ({a_data.matches} partite)'))
                    raw['a_data'] = a_data
                else:
                    banners.append(('warn',f'⚠️ Stats {a_name}: {msg} — uso dati default'))
                    if claude_key:
                        backup = claude_search_backup(claude_key,h_name,a_name,comp,'statistiche')
                        if backup:
                            raw['a_data'] = TeamData(name=a_name,gf=backup.get('gf_away',1.1),
                                                      ga=backup.get('ga_away',1.2),source='Claude AI')
                            banners.append(('ok',f'✅ Stats {a_name} da Claude AI (backup)'))

            sport_key = COMP_ODDS.get(comp)
            if sport_key and odds_key:
                with st.spinner(f'Quote Sportium {h_name} vs {a_name}...'):
                    odds_data, msg = fetch_odds(odds_key, sport_key, h_name, a_name)
                    if odds_data:
                        bk = odds_data.get('_bk','')
                        banners.append(('ok',f'✅ Quote da {bk}'))
                        raw['odds'] = odds_data
                    else:
                        banners.append(('err',f'❌ Quote: {msg}'))
                        if claude_key:
                            with st.spinner('Claude cerca le quote...'):
                                backup_odds = claude_search_backup(claude_key,h_name,a_name,comp,'quote bookmaker')
                                if backup_odds:
                                    raw['odds'] = backup_odds
                                    banners.append(('ok','✅ Quote trovate da Claude AI (backup)'))
            else:
                banners.append(('warn',f'⚠️ Competizione non supportata per le quote automatiche'))

            with st.spinner(f'Infortuni {h_name}...'):
                inj_h, msg = fetch_injuries_tm(h_name)
                raw['inj_h'] = inj_h
                if inj_h:
                    banners.append(('ok',f'✅ {len(inj_h)} infortuni {h_name} da Transfermarkt'))
                elif 'ok' not in msg:
                    banners.append(('warn',f'⚠️ Infortuni {h_name}: {msg}'))

            with st.spinner(f'Infortuni {a_name}...'):
                inj_a, msg = fetch_injuries_tm(a_name)
                raw['inj_a'] = inj_a
                if inj_a:
                    banners.append(('ok',f'✅ {len(inj_a)} infortuni {a_name} da Transfermarkt'))

            st.session_state['raw']     = raw
            st.session_state['banners'] = banners
            st.session_state['step']    = 'review'
            st.rerun()

    # ===========================================================================
    # STEP 2 — REVIEW & MODIFICA
    # ===========================================================================
    elif st.session_state['step'] == 'review':
        raw     = st.session_state.get('raw',{})
        banners = st.session_state.get('banners',[])
        h_name  = st.session_state.get('h_name','Casa')
        a_name  = st.session_state.get('a_name','Trasferta')
        comp    = st.session_state.get('comp','')

        for btype,msg in banners:
            css = 'banner-ok' if btype=='ok' else ('banner-err' if btype=='err' else 'banner-warn')
            st.markdown(f'<div class="{css}">{msg}</div>', unsafe_allow_html=True)

        # Dati casa
        h_raw:Optional[TeamData] = raw.get('h_data') or TeamData(name=h_name)
        a_raw:Optional[TeamData] = raw.get('a_data') or TeamData(name=a_name)
        odds_raw:Dict = raw.get('odds',{})

        with st.expander(f'📊 Dati {h_name} — modifica se necessario', expanded=False):
            r1,r2,r3,r4 = st.columns(4)
            with r1: h_gf  = st.number_input('GF/gara',0.0,15.0,float(h_raw.gf),0.1,key='h_gf')
            with r2: h_ga  = st.number_input('GA/gara',0.0,15.0,float(h_raw.ga),0.1,key='h_ga')
            with r3: h_xg  = st.number_input('xG/gara',0.0,15.0,float(h_raw.xg),0.1,key='h_xg')
            with r4: h_xga = st.number_input('xGA/gara',0.0,15.0,float(h_raw.xga),0.1,key='h_xga')
            r5,r6,r7 = st.columns(3)
            with r5: h_cor = st.number_input('Angoli/gara',0.0,20.0,float(h_raw.corners),0.5,key='h_cor')
            with r6: h_crd = st.number_input('Cartellini',0.0,10.0,float(h_raw.cards),0.5,key='h_crd')
            with r7: h_sot = st.number_input('Tiri porta',0.0,20.0,float(h_raw.shots),0.5,key='h_sot')
            h_form = st.text_input('Forma (es. WDWLW)',value=h_raw.form,key='h_form')
        with st.expander(f'📊 Dati {a_name} — modifica se necessario', expanded=False):
            r1,r2,r3,r4 = st.columns(4)
            with r1: a_gf  = st.number_input('GF/gara',0.0,15.0,float(a_raw.gf),0.1,key='a_gf')
            with r2: a_ga  = st.number_input('GA/gara',0.0,15.0,float(a_raw.ga),0.1,key='a_ga')
            with r3: a_xg  = st.number_input('xG/gara',0.0,15.0,float(a_raw.xg),0.1,key='a_xg')
            with r4: a_xga = st.number_input('xGA/gara',0.0,15.0,float(a_raw.xga),0.1,key='a_xga')
            r5,r6,r7 = st.columns(3)
            with r5: a_cor = st.number_input('Angoli/gara',0.0,20.0,float(a_raw.corners),0.5,key='a_cor')
            with r6: a_crd = st.number_input('Cartellini',0.0,10.0,float(a_raw.cards),0.5,key='a_crd')
            with r7: a_sot = st.number_input('Tiri porta',0.0,20.0,float(a_raw.shots),0.5,key='a_sot')
            a_form = st.text_input('Forma (es. LWDWW)',value=a_raw.form,key='a_form')
        with st.expander('💰 Quote — modifica se necessario', expanded=False):
            q1,q2,q3 = st.columns(3)
            with q1:
                q_home  = st.number_input('1 Casa',   0.0,50.0,float(odds_raw.get('home',0.0)),0.05,key='q_home')
                q_ov25  = st.number_input('Over 2.5', 0.0,50.0,float(odds_raw.get('over25',0.0)),0.05,key='q_ov25')
                q_btts  = st.number_input('BTTS Si',  0.0,50.0,float(odds_raw.get('btts_y',0.0)),0.05,key='q_btts')
            with q2:
                q_draw  = st.number_input('X Pari',   0.0,50.0,float(odds_raw.get('draw',0.0)),0.05,key='q_draw')
                q_un25  = st.number_input('Under 2.5',0.0,50.0,float(odds_raw.get('under25',0.0)),0.05,key='q_un25')
                q_bttsn = st.number_input('BTTS No',  0.0,50.0,float(odds_raw.get('btts_n',0.0)),0.05,key='q_bttsn')
            with q3:
                q_away  = st.number_input('2 Trasf.', 0.0,50.0,float(odds_raw.get('away',0.0)),0.05,key='q_away')
                q_ov35  = st.number_input('Over 3.5', 0.0,50.0,float(odds_raw.get('over35',0.0)),0.05,key='q_ov35')
                q_un35  = st.number_input('Under 3.5',0.0,50.0,float(odds_raw.get('under35',0.0)),0.05,key='q_un35')

        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            analizza = st.button('⚡ ANALIZZA', use_container_width=True)
        with c_btn2:
            reset = st.button('🔄 RESET', use_container_width=True)

        if reset:
            for k in ['step','raw','banners','result_v6','h_name','a_name']:
                st.session_state.pop(k, None)
            st.rerun()

        if analizza:
            h = TeamData(name=h_name,gf=h_gf,ga=h_ga,xg=h_xg,xga=h_xga,
                         corners=h_cor,cards=h_crd,shots=h_sot,form=h_form.upper())
            a = TeamData(name=a_name,gf=a_gf,ga=a_ga,xg=a_xg,xga=a_xga,
                         corners=a_cor,cards=a_crd,shots=a_sot,form=a_form.upper())
            odds = {'home':q_home,'draw':q_draw,'away':q_away,
                    'over25':q_ov25,'under25':q_un25,'over35':q_ov35,'under35':q_un35,
                    'btts_y':q_btts,'btts_n':q_bttsn}
            eng  = Engine(h,a)
            mkts = build_markets(eng,h,a,odds)
            combos = build_combos(mkts,h_name,a_name)
            scores = eng.top_scores(6)
            recs   = build_recs(mkts)
            htft   = eng.htft_probs()
            inj_h  = raw.get('inj_h',[])
            inj_a  = raw.get('inj_a',[])

            result = dict(h=h,a=a,comp=comp,eng=eng,mkts=mkts,
                          combos=combos,scores=scores,recs=recs,
                          htft=htft,inj_h=inj_h,inj_a=inj_a)
            st.session_state['result_v6'] = result
            st.session_state['step'] = 'results'

            # Salva storico
            hist = st.session_state.get('history',[])
            hist.insert(0,{'match':f'{h_name} vs {a_name}',
                           'comp':comp,'ts':datetime.now().strftime('%d/%m %H:%M'),
                           'lh':round(eng.lh,2),'la':round(eng.la,2)})
            st.session_state['history'] = hist[:5]
            st.rerun()

    # ===========================================================================
    # STEP 3 — RISULTATI
    # ===========================================================================
    elif st.session_state['step'] == 'results':
        R = st.session_state.get('result_v6',{})
        if not R:
            st.session_state['step'] = 'input'
            st.rerun()
            return

        h:TeamData   = R['h']
        a:TeamData   = R['a']
        eng:Engine   = R['eng']
        mkts         = R['mkts']
        combos       = R['combos']
        scores       = R['scores']
        recs         = R['recs']
        htft         = R['htft']
        inj_h        = R['inj_h']
        inj_a        = R['inj_a']

        # Match header
        st.markdown(
            f'<div class="header" style="padding:14px 20px">'
            f'<div style="font-size:1.1rem;font-weight:700">{h.name} vs {a.name}</div>'
            f'<div class="sub">{R["comp"]} | Lambda: {eng.lh:.2f} vs {eng.la:.2f}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Reset button
        if st.button('🔄 Nuova Partita', use_container_width=False):
            for k in ['step','raw','banners','result_v6','h_name','a_name']:
                st.session_state.pop(k, None)
            st.session_state['step'] = 'input'
            st.rerun()

        # =======================
        # RACCOMANDAZIONI
        # =======================
        st.markdown('<div class="section"><div class="sec-title">🎯 Raccomandazioni</div>', unsafe_allow_html=True)
        r1,r2,r3 = st.columns(3)
        with r1: render_rec(recs['best'],'best')
        with r2: render_rec(recs['value'],'value')
        with r3: render_rec(recs['long'],'long')
        st.markdown('</div>', unsafe_allow_html=True)

        # =======================
        # TABS MERCATI
        # =======================
        tabs = st.tabs(['1X2 & DC','O/U & Tempi','BTTS & Multi',
                        'Gol Squadre','Speciali','Combo','Info'])

        def get_cat(cat):
            return sorted([m for m in mkts if m.cat==cat],key=lambda x:-abs(x.edge) if x.bk>1.01 else -x.prob)

        # Tab 1X2
        with tabs[0]:
            st.markdown('<div class="sec-title">1X2</div>', unsafe_allow_html=True)
            for m in get_cat('1X2'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Doppia Chance</div>', unsafe_allow_html=True)
            for m in get_cat('Doppia Chance'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Draw No Bet</div>', unsafe_allow_html=True)
            for m in get_cat('Draw No Bet'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">HT/FT Top 4</div>', unsafe_allow_html=True)
            top_htft = sorted(htft.items(),key=lambda x:-x[1])[:4]
            cols = st.columns(4)
            for idx,(k,v) in enumerate(top_htft):
                with cols[idx]:
                    st.markdown(f'<div class="stat-box"><div class="sb-label">{k}</div>'
                                f'<div class="sb-val">{v*100:.1f}%</div>'
                                f'<div class="sb-sub">Fair: {1/max(v,0.001):.1f}</div></div>',
                                unsafe_allow_html=True)

        # Tab O/U
        with tabs[1]:
            st.markdown('<div class="sec-title">Over / Under</div>', unsafe_allow_html=True)
            for m in get_cat('Over/Under'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Primo Tempo</div>', unsafe_allow_html=True)
            for m in get_cat('Primo Tempo'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Secondo Tempo</div>', unsafe_allow_html=True)
            for m in get_cat('Secondo Tempo'): render_mkt(m)

        # Tab BTTS
        with tabs[2]:
            st.markdown('<div class="sec-title">BTTS</div>', unsafe_allow_html=True)
            for m in get_cat('BTTS'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Multigoal Totale</div>', unsafe_allow_html=True)
            for m in get_cat('Multigoal Totale'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Gol Esatti Totali</div>', unsafe_allow_html=True)
            for m in get_cat('Gol Esatti'): render_mkt(m)

        # Tab Gol Squadre
        with tabs[3]:
            c_h, c_a = st.columns(2)
            with c_h:
                st.markdown(f'<div class="sec-title">Gol {h.name}</div>', unsafe_allow_html=True)
                for m in get_cat('Gol Casa'): render_mkt(m)
            with c_a:
                st.markdown(f'<div class="sec-title">Gol {a.name}</div>', unsafe_allow_html=True)
                for m in get_cat('Gol Ospite'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Squadra segna in entrambi i tempi</div>', unsafe_allow_html=True)
            for m in get_cat('Speciali'): render_mkt(m)

        # Tab Speciali
        with tabs[4]:
            st.markdown('<div class="sec-title">Risultati Esatti piu Probabili</div>', unsafe_allow_html=True)
            cols = st.columns(3)
            for idx,sc in enumerate(scores):
                with cols[idx%3]:
                    col_map = {'Casa':'var(--org)','Pari':'var(--yel)','Trasf':'var(--blu)'}
                    c = col_map.get(sc['cat'],'var(--t1)')
                    st.markdown(
                        f'<div class="stat-box"><div class="sb-label">{sc["cat"]}</div>'
                        f'<div class="sb-val" style="font-size:1.6rem;color:{c}">{sc["score"]}</div>'
                        f'<div class="sb-sub">{sc["prob_pct"]:.2f}% | Fair: {sc["fair"]:.1f}</div></div>',
                        unsafe_allow_html=True
                    )
            st.markdown('<div class="sec-title" style="margin-top:14px">Handicap Europeo</div>', unsafe_allow_html=True)
            for m in get_cat('Handicap'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Winning Margin</div>', unsafe_allow_html=True)
            for m in get_cat('Winning Margin'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Angoli & Cartellini</div>', unsafe_allow_html=True)
            for m in get_cat('Angoli')+get_cat('Cartellini'): render_mkt(m)

        # Tab Combo
        with tabs[5]:
            st.markdown('<div class="sec-title">Combo piu Probabili (ordinate per prob)</div>', unsafe_allow_html=True)
            if combos:
                for c in combos[:15]:
                    render_combo(c)
            else:
                st.markdown('<div class="banner-warn">⚠️ Inserisci le quote per vedere le combo con edge</div>',
                            unsafe_allow_html=True)

        # Tab Info
        with tabs[6]:
            c_h,c_a = st.columns(2)
            with c_h:
                st.markdown(f'<div class="sec-title">{h.name}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">'
                    f'<div class="stat-box"><div class="sb-label">GF/gara</div><div class="sb-val">{h.gf:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">GA/gara</div><div class="sb-val">{h.ga:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">Lambda</div><div class="sb-val">{eng.lh:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">xG/gara</div><div class="sb-val">{h.xg:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">Angoli</div><div class="sb-val">{h.corners:.1f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">Cartellini</div><div class="sb-val">{h.cards:.1f}</div></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if h.form:
                    st.markdown(f'<div style="margin-top:10px">{form_html(h.form)}</div>', unsafe_allow_html=True)
                if inj_h:
                    st.markdown('<div class="sec-title" style="margin-top:12px">Infortuni</div>', unsafe_allow_html=True)
                    for inj in inj_h:
                        css = 'var(--red)' if inj['status']=='out' else 'var(--yel)'
                        st.markdown(
                            f'<div style="background:var(--bg2);border-left:3px solid {css};'
                            f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:5px;font-size:.72rem">'
                            f'<strong>{inj["name"]}</strong> — {inj["info"]}</div>',
                            unsafe_allow_html=True
                        )
            with c_a:
                st.markdown(f'<div class="sec-title">{a.name}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">'
                    f'<div class="stat-box"><div class="sb-label">GF/gara</div><div class="sb-val">{a.gf:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">GA/gara</div><div class="sb-val">{a.ga:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">Lambda</div><div class="sb-val">{eng.la:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">xG/gara</div><div class="sb-val">{a.xg:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">Angoli</div><div class="sb-val">{a.corners:.1f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">Cartellini</div><div class="sb-val">{a.cards:.1f}</div></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if a.form:
                    st.markdown(f'<div style="margin-top:10px">{form_html(a.form)}</div>', unsafe_allow_html=True)
                if inj_a:
                    st.markdown('<div class="sec-title" style="margin-top:12px">Infortuni</div>', unsafe_allow_html=True)
                    for inj in inj_a:
                        css = 'var(--red)' if inj['status']=='out' else 'var(--yel)'
                        st.markdown(
                            f'<div style="background:var(--bg2);border-left:3px solid {css};'
                            f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:5px;font-size:.72rem">'
                            f'<strong>{inj["name"]}</strong> — {inj["info"]}</div>',
                            unsafe_allow_html=True
                        )

        # AI Check
        claude_key = st.session_state.get('claude_key','')
        if claude_key:
            with st.expander('🤖 AI Check (Claude)', expanded=False):
                if st.button('Analisi qualitativa AI', use_container_width=True):
                    ph,pd,pa = eng.p1x2()
                    ov25,_ = eng.pou(2.5)
                    btts,_ = eng.pbtts()
                    summary = (f'{h.name} vs {a.name} — {R["comp"]}\n'
                               f'1X2: {ph*100:.1f}%/{pd*100:.1f}%/{pa*100:.1f}%\n'
                               f'Over 2.5: {ov25*100:.1f}% | BTTS: {btts*100:.1f}%\n'
                               f'Lambda: {eng.lh:.2f} vs {eng.la:.2f}')
                    inj_txt = ''
                    if inj_h: inj_txt += f'{h.name}: '+', '.join(i["name"] for i in inj_h)
                    if inj_a: inj_txt += f' | {a.name}: '+', '.join(i["name"] for i in inj_a)
                    try:
                        client = anthropic.Anthropic(api_key=claude_key)
                        msg = client.messages.create(
                            model='claude-opus-4-5', max_tokens=600,
                            system='Sei un analista sportivo esperto. Dai 5 considerazioni brevi in italiano. Formato: - [CATEGORIA] testo (max 15 parole). Categorie: INFORTUNI | FORMA | MOTIVAZIONE | TATTICA | VALORE',
                            messages=[{'role':'user','content':f'Partita: {summary}\nInfortuni: {inj_txt or "nessuno noto"}'}]
                        )
                        for line in msg.content[0].text.split('\n'):
                            if line.strip().startswith('-'):
                                st.markdown(
                                    f'<div style="background:var(--bg2);border-left:3px solid var(--org);'
                                    f'border-radius:0 8px 8px 0;padding:9px 14px;margin-bottom:7px;font-size:.78rem">'
                                    f'{line[1:].strip()}</div>',
                                    unsafe_allow_html=True
                                )
                    except Exception as e:
                        st.error(f'AI non disponibile: {e}')

    # Storico
    history = st.session_state.get('history',[])
    if history:
        with st.expander('📋 Ultime 5 partite analizzate', expanded=False):
            for h_item in history:
                st.markdown(
                    f'<div class="hist-row">'
                    f'<strong>{h_item["match"]}</strong> — {h_item["comp"]}'
                    f'<span style="float:right;color:var(--t2)">{h_item["ts"]} | '
                    f'L: {h_item["lh"]} vs {h_item["la"]}</span></div>',
                    unsafe_allow_html=True
                )

if __name__ == '__main__':
    main()
