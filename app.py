# -*- coding: utf-8 -*-
# QUANTUM FOOTBALL ANALYTICS v6.1
# Integra engine.py avanzato:
#   - Dixon-Coles, peso partite recenti, stats casa/trasferta
#   - Motivazione slider, infortuni auto, H2H 3 anni
#   - Confronto modello base vs avanzato
#   - 30+ mercati + combo automatiche

import streamlit as st
import numpy as np
import requests, json, re, warnings
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import itertools
warnings.filterwarnings('ignore')

try:
    import google.generativeai as genai
    GENAI_OK = True
except ImportError:
    GENAI_OK = False

FD_KEY     = '5fda2ad3855647748d655990c528d080'
ODDS_KEY   = '6b81cee50aa656a862a58878d6585053'
GEMINI_KEY = 'AIzaSyBKob5v5K4HvJqC8E_uj4OVu0OIu_VTjm8'

# Importa engine avanzato
try:
    from engine import (
        AdvancedEngine, TeamStats, H2HRecord, MatchRecord,
        fetch_advanced_stats, fetch_h2h, h2h_summary,
        estimate_injury_impact, h2h_lambda_adjustment,
        monte_carlo, check_internal_consistency, detect_traps,
        confidence_score, traffic_light, bookmaker_implied_comparison,
        LEAGUE_AVGS,
    )
    ENGINE_OK = True
except ImportError as e:
    ENGINE_OK = False
    ENGINE_ERR = str(e)

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
.header h1{font-size:1.4rem;font-weight:700;color:var(--org);margin:0;}
.header .sub{font-size:.72rem;color:var(--t2);margin-top:5px;}
.section{background:var(--bg1);border:1px solid var(--br1);border-radius:12px;padding:16px 18px;margin-bottom:14px;}
.sec-title{font-size:.62rem;font-weight:600;color:var(--t2);letter-spacing:.18em;
  text-transform:uppercase;padding-bottom:8px;border-bottom:1px solid var(--br1);margin-bottom:12px;}
.banner-ok{background:rgba(0,200,150,.08);border:1px solid rgba(0,200,150,.25);
  border-radius:8px;padding:9px 14px;font-size:.72rem;color:var(--grn);margin:5px 0;}
.banner-err{background:rgba(255,59,92,.08);border:1px solid rgba(255,59,92,.25);
  border-radius:8px;padding:9px 14px;font-size:.72rem;color:var(--red);margin:5px 0;}
.banner-warn{background:rgba(255,209,102,.08);border:1px solid rgba(255,209,102,.25);
  border-radius:8px;padding:9px 14px;font-size:.72rem;color:var(--yel);margin:5px 0;}
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
.rl{font-size:.52rem;color:var(--t2);text-transform:uppercase;letter-spacing:.08em;}
.rv{font-size:.9rem;font-weight:700;margin-top:2px;}
.rv.grn{color:var(--grn);}.rv.yel{color:var(--yel);}.rv.red{color:var(--red);}
.rv.org{color:var(--org);}.rv.blu{color:var(--blu);}
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
.stat-box{background:var(--bg2);border:1px solid var(--br1);border-radius:8px;padding:10px 12px;text-align:center;}
.sb-label{font-size:.55rem;color:var(--t2);text-transform:uppercase;letter-spacing:.08em;}
.sb-val{font-size:1rem;font-weight:700;color:var(--org);margin-top:3px;}
.sb-sub{font-size:.6rem;color:var(--t3);margin-top:2px;}
.form-dot{display:inline-block;width:26px;height:26px;border-radius:50%;
  text-align:center;line-height:26px;font-size:.62rem;font-weight:700;margin-right:3px;}
.form-dot.W{background:rgba(0,200,150,.2);color:var(--grn);}
.form-dot.D{background:rgba(255,209,102,.2);color:var(--yel);}
.form-dot.L{background:rgba(255,59,92,.2);color:var(--red);}
.cmp-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0;}
.cmp-box{border-radius:8px;padding:12px 14px;}
.cmp-box.base{background:rgba(255,255,255,.03);border:1px solid var(--br2);}
.cmp-box.adv{background:rgba(255,107,53,.05);border:1px solid rgba(255,107,53,.2);}
.cmp-label{font-size:.58rem;color:var(--t2);text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px;}
.cmp-val{font-size:.85rem;font-weight:600;color:var(--t1);margin-bottom:4px;}
.note-item{background:var(--bg2);border-left:3px solid var(--org);border-radius:0 6px 6px 0;
  padding:8px 12px;margin-bottom:6px;font-size:.72rem;color:var(--t2);}
.h2h-row{background:var(--bg2);border:1px solid var(--br1);border-radius:6px;
  padding:8px 12px;margin-bottom:5px;font-size:.72rem;display:flex;justify-content:space-between;}
.hist-row{background:var(--bg2);border:1px solid var(--br1);border-radius:8px;
  padding:9px 14px;margin-bottom:5px;font-size:.72rem;}
.stButton>button{background:var(--org)!important;border:none!important;
  color:#fff!important;font-weight:600!important;border-radius:8px!important;padding:10px!important;width:100%!important;}
.stButton>button:hover{background:#e55a2b!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--bg1)!important;border-bottom:1px solid var(--br1)!important;}
.stTabs [data-baseweb="tab"]{font-size:.7rem!important;color:var(--t2)!important;
  background:transparent!important;padding:9px 14px!important;}
.stTabs [aria-selected="true"]{color:var(--org)!important;border-bottom:2px solid var(--org)!important;}
.stTextInput>div>div>input,.stSelectbox>div>div{
  background:var(--bg2)!important;border:1px solid var(--br2)!important;
  color:var(--t1)!important;border-radius:8px!important;}
#MainMenu,footer,header,.stDeployButton{visibility:hidden!important;display:none!important;}
</style>
"""

# ==============================================================================
# COMPETITIONS
# ==============================================================================
COMPETITIONS = {
    'Italia':           ['Serie A','Serie B','Coppa Italia'],
    'Germania':         ['Bundesliga','2. Bundesliga','DFB-Pokal'],
    'Inghilterra':      ['Premier League','EFL Championship','FA Cup'],
    'Francia':          ['Ligue 1','Ligue 2','Coupe de France'],
    'Spagna':           ['La Liga','LaLiga Hypermotion','Copa del Rey'],
    'Portogallo':       ['Liga Portugal','Liga Portugal 2'],
    'Olanda':           ['Eredivisie','Eerste Divisie'],
    'Belgio':           ['Pro League','Challenger Pro League'],
    'Scozia':           ['Scottish Premiership','Scottish Championship'],
    'Svezia':           ['Allsvenskan','Superettan'],
    'Norvegia':         ['Eliteserien','1. divisjon'],
    'Champions League': ['Champions League'],
    'Europa League':    ['Europa League'],
    'Conference League':['Conference League'],
}

COMP_FD = {
    'Serie A':'SA','Serie B':'SB','Premier League':'PL',
    'EFL Championship':'ELC','Bundesliga':'BL1','2. Bundesliga':'BL2',
    'Ligue 1':'FL1','Ligue 2':'FL2','La Liga':'PD','LaLiga Hypermotion':'SD',
    'Eredivisie':'DED','Pro League':'BSA','Liga Portugal':'PPL',
    'Champions League':'CL','Europa League':'EL',
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

BK_PRIORITY = ['sportium','bet365','unibet','bwin','betway','william_hill','marathonbet']
REQ_H = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept':'application/json, */*',
}

# ==============================================================================
# MARKET RESULT
# ==============================================================================
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
# MARKET BUILDER
# ==============================================================================
def make_mkt(name, emoji, prob, bk, cat, key, desc=''):
    fair = round(1/max(prob,0.001),2)
    edge = round((prob*bk)-1,4) if bk>1.01 else 0.0
    if bk<1.5 and bk>1.01: sem='rosso'
    elif edge>=0.08: sem='verde'
    elif edge>=0.0: sem='giallo'
    else: sem='rosso'
    return MarketResult(name=name,emoji=emoji,prob=prob,fair=fair,
                        bk=bk,edge=edge,sem=sem,desc=desc,cat=cat,key=key)

def build_markets(eng:AdvancedEngine, h:TeamStats, a:TeamStats, odds:Dict) -> List[MarketResult]:
    mk=[]
    ph,pd,pa = eng.p1x2()
    p1x,p12,px2 = eng.pdoppia()
    dnb_h,dnb_a = eng.pdnb()
    ov05,un05=eng.pou(0.5); ov15,un15=eng.pou(1.5)
    ov25,un25=eng.pou(2.5); ov35,un35=eng.pou(3.5); ov45,un45=eng.pou(4.5)
    btts_y,btts_n=eng.pbtts()
    ov05_ht,un05_ht=eng.pou_ht(0.5); ov15_ht,un15_ht=eng.pou_ht(1.5)
    btts_ht_y,_=eng.pbtts_ht(); btts_2t_y,_=eng.pbtts_2t()
    corn_ov,corn_un=eng.p_corners(h.corners_avg,a.corners_avg,9.5)
    card_ov,card_un=eng.p_cards(h.cards_avg,a.cards_avg,3.5)
    h_both=eng.p_team_scores_both_halves(True)
    a_both=eng.p_team_scores_both_halves(False)
    g=odds.get; o=lambda k: g(k,0.0)

    mk+=[make_mkt(f'1 - {h.name}','⚽',ph,o('home'),'1X2','home',f'{h.name} vince. λ={eng.lh:.2f}'),
         make_mkt('X - Pareggio','🤝',pd,o('draw'),'1X2','draw',f'Pareggio prob: {pd*100:.1f}%'),
         make_mkt(f'2 - {a.name}','⚽',pa,o('away'),'1X2','away',f'{a.name} vince. λ={eng.la:.2f}')]
    mk+=[make_mkt(f'1X','🔄',p1x,o('dc_1x'),'Doppia Chance','dc_1x',f'{h.name} non perde. {p1x*100:.1f}%'),
         make_mkt(f'12','🔄',p12,o('dc_12'),'Doppia Chance','dc_12',f'Una delle due vince. {p12*100:.1f}%'),
         make_mkt(f'X2','🔄',px2,o('dc_x2'),'Doppia Chance','dc_x2',f'{a.name} non perde. {px2*100:.1f}%')]
    mk+=[make_mkt(f'DNB {h.name}','🛡️',dnb_h,o('dnb_home'),'Draw No Bet','dnb_home',f'Rimborso se X. {dnb_h*100:.1f}%'),
         make_mkt(f'DNB {a.name}','🛡️',dnb_a,o('dnb_away'),'Draw No Bet','dnb_away',f'Rimborso se X. {dnb_a*100:.1f}%')]
    mk+=[make_mkt('Over 0.5','📈',ov05,o('over05'),'Over/Under','over05','Almeno 1 gol'),
         make_mkt('Under 0.5','📉',un05,o('under05'),'Over/Under','under05','0 gol'),
         make_mkt('Over 1.5','📈',ov15,o('over15'),'Over/Under','over15','Almeno 2 gol'),
         make_mkt('Under 1.5','📉',un15,o('under15'),'Over/Under','under15','Max 1 gol'),
         make_mkt('Over 2.5','📈',ov25,o('over25'),'Over/Under','over25','Almeno 3 gol'),
         make_mkt('Under 2.5','📉',un25,o('under25'),'Over/Under','under25','Max 2 gol'),
         make_mkt('Over 3.5','📈',ov35,o('over35'),'Over/Under','over35','Almeno 4 gol'),
         make_mkt('Under 3.5','📉',un35,o('under35'),'Over/Under','under35','Max 3 gol'),
         make_mkt('Over 4.5','📈',ov45,o('over45'),'Over/Under','over45','Almeno 5 gol')]
    mk+=[make_mkt('BTTS Si','⚽⚽',btts_y,o('btts_y'),'BTTS','btts_y','Entrambe segnano'),
         make_mkt('BTTS No','🚫',btts_n,o('btts_n'),'BTTS','btts_n','Almeno una non segna')]
    mk+=[make_mkt('Over 0.5 1T','📈',ov05_ht,o('over05_ht'),'Primo Tempo','over05_ht','Gol nel 1T'),
         make_mkt('Over 1.5 1T','📈',ov15_ht,o('over15_ht'),'Primo Tempo','over15_ht','2+ gol nel 1T'),
         make_mkt('Nessun gol 1T','🚫',un05_ht,o('no_gol_ht'),'Primo Tempo','no_gol_ht','0-0 al 45min'),
         make_mkt('BTTS 1T','⚽⚽',btts_ht_y,o('btts_ht'),'Primo Tempo','btts_ht','Entrambe 1T'),
         make_mkt('BTTS 2T','⚽⚽',btts_2t_y,o('btts_2t'),'Secondo Tempo','btts_2t','Entrambe 2T')]
    mk+=[make_mkt(f'{h.name} segna entrambi tempi','⚽',h_both,o('h_both'),'Speciali','h_both',''),
         make_mkt(f'{a.name} segna entrambi tempi','⚽',a_both,o('a_both'),'Speciali','a_both','')]
    for label,lo,hi,key in [('0-1',0,1,'mg01'),('2-3',2,3,'mg23'),('3-4',3,4,'mg34'),('4-5',4,5,'mg45'),('5+',5,99,'mg5p')]:
        p=eng.pmultigoal(lo,hi)
        mk.append(make_mkt(f'Multigoal {label}','🎯',p,o(f'mg_{key}'),'Multigoal Totale',f'mg_{key}',f'Totale: {label}'))
    for n,key in [(0,'h0'),(1,'h1'),(2,'h2'),(3,'h3')]:
        mk.append(make_mkt(f'{h.name} {n} gol','🏠',eng.p_team_goals(n,True),o(f'hg{key}'),'Gol Casa',f'hg{key}',''))
    mk.append(make_mkt(f'{h.name} 2+ gol','🏠',eng.p_team_goals_range(2,99,True),o('hg2p'),'Gol Casa','hg2p',''))
    for n,key in [(0,'a0'),(1,'a1'),(2,'a2'),(3,'a3')]:
        mk.append(make_mkt(f'{a.name} {n} gol','✈️',eng.p_team_goals(n,False),o(f'ag{key}'),'Gol Ospite',f'ag{key}',''))
    mk.append(make_mkt(f'{a.name} 2+ gol','✈️',eng.p_team_goals_range(2,99,False),o('ag2p'),'Gol Ospite','ag2p',''))
    for n in range(6):
        mk.append(make_mkt(f'Esattamente {n} gol','🔢',eng.p_exact_gol(n),o(f'exact{n}'),'Gol Esatti',f'exact{n}',''))
    for hdp,lbl in [(-1,'Casa -1'),(1,'Ospite -1'),(-2,'Casa -2')]:
        is_home=hdp<0
        mk.append(make_mkt(f'EH {lbl}','⚖️',eng.phandicap_eu(abs(hdp),is_home),o(f'eh_{hdp}'),'Handicap',f'eh_{hdp}',''))
    for margin in [1,2,3]:
        for is_home,tn in [(True,h.name),(False,a.name)]:
            p=sum(eng.p_winning_margin(m,is_home) for m in range(3,8)) if margin==3 else eng.p_winning_margin(margin,is_home)
            mk.append(make_mkt(f'{tn} vince di {margin}{"+" if margin==3 else ""}','🏆',p,
                               o(f'wm_{is_home}_{margin}'),'Winning Margin',f'wm_{is_home}_{margin}',''))
    mk+=[make_mkt('Angoli Over 9.5','📐',corn_ov,o('corn_ov'),'Angoli','corn_ov',''),
         make_mkt('Angoli Under 9.5','📐',corn_un,o('corn_un'),'Angoli','corn_un',''),
         make_mkt('Cartellini Over 3.5','🟨',card_ov,o('card_ov'),'Cartellini','card_ov',''),
         make_mkt('Cartellini Under 3.5','🟨',card_un,o('card_un'),'Cartellini','card_un','')]
    return mk

# ==============================================================================
# COMBO BUILDER
# ==============================================================================
def build_combos(markets:List[MarketResult], h_name:str, a_name:str) -> List[ComboResult]:
    combos=[]
    def make_combo(keys, tipo):
        legs=[m for m in markets if m.key in keys]
        if len(legs)<2: return None
        prob=1.0
        for l in legs: prob*=l.prob
        quota=1.0
        for l in legs: quota*=(l.bk if l.bk>1.01 else l.fair)
        edge=(prob*quota)-1
        return ComboResult(legs=legs,tipo=tipo,prob_combo=prob,quota_combo=round(quota,2),edge_combo=round(edge,4))

    pairs=[
        (['home','over25'],'1X2 + Over 2.5'),(['home','over15'],'1X2 + Over 1.5'),
        (['home','btts_y'],'1X2 + BTTS Si'),(['away','over25'],'2 + Over 2.5'),
        (['away','btts_y'],'2 + BTTS Si'),(['dc_1x','under25'],'1X + Under 2.5'),
        (['dc_x2','under25'],'X2 + Under 2.5'),(['dc_12','over15'],'12 + Over 1.5'),
        (['btts_y','over25'],'BTTS Si + Over 2.5'),(['btts_y','over15'],'BTTS Si + Over 1.5'),
        (['btts_n','under25'],'BTTS No + Under 2.5'),
        (['mg_mg23','btts_y'],'Multigoal 2-3 + BTTS Si'),(['mg_mg23','home'],'Multigoal 2-3 + Casa'),
        (['mg_mg34','btts_y'],'Multigoal 3-4 + BTTS Si'),(['mg_mg01','btts_n'],'Multigoal 0-1 + BTTS No'),
        (['hgh1','aga0'],f'{h_name} 1 + {a_name} 0'),(['hgh1','aga1'],f'{h_name} 1 + {a_name} 1'),
        (['hgh2','aga0'],f'{h_name} 2 + {a_name} 0'),(['hg2p','aga0'],f'{h_name} 2+ + {a_name} 0'),
        (['hg2p','ag2p'],f'Entrambe 2+ gol'),
    ]
    for keys,tipo in pairs:
        c=make_combo(keys,tipo)
        if c: combos.append(c)

    # Terzine automatiche
    mkt_with_bk=[m for m in markets if m.bk>1.01]
    top8=sorted(mkt_with_bk,key=lambda x:-x.prob)[:8]
    for trio in itertools.combinations(top8,3):
        cats={t.cat for t in trio}
        if len(cats)>=2:
            prob=trio[0].prob*trio[1].prob*trio[2].prob
            quota=trio[0].bk*trio[1].bk*trio[2].bk
            edge=(prob*quota)-1
            combos.append(ComboResult(
                legs=list(trio),tipo=' + '.join(t.name for t in trio),
                prob_combo=prob,quota_combo=round(quota,2),edge_combo=round(edge,4)
            ))

    combos.sort(key=lambda x:-x.prob_combo)
    return combos[:20]

# ==============================================================================
# RACCOMANDAZIONI
# ==============================================================================
def build_recs(markets:List[MarketResult]) -> Dict:
    with_bk=[m for m in markets if m.bk>1.01]
    by_edge=sorted(with_bk,key=lambda x:-x.edge)
    best=next((m for m in by_edge if m.edge>0 and m.bk>=1.50 and m.prob>=0.35),None)
    value=next((m for m in by_edge if m.edge>0 and m.bk>=1.80 and 0.25<=m.prob<=0.65 and m!=best),None)
    long_s=next((m for m in by_edge if m.edge>0 and m.bk>=2.50 and m!=best and m!=value),None)
    return {'best':best,'value':value,'long':long_s,'all':by_edge}

# ==============================================================================
# FETCH ODDS
# ==============================================================================
def fetch_odds(odds_key, sport_key, home, away):
    try:
        p={'apiKey':odds_key,'regions':'eu','markets':'h2h,totals,btts',
           'oddsFormat':'decimal','bookmakers':','.join(BK_PRIORITY)}
        r=requests.get(f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds',
                       params=p,headers=REQ_H,timeout=12)
        if r.status_code!=200: return {},f'Odds API HTTP {r.status_code}'
        data=r.json()
        if not isinstance(data,list): return {},'Formato non valido'
        hl,al=home.lower(),away.lower()
        event=None
        for ev in data:
            eh=ev.get('home_team','').lower(); ea=ev.get('away_team','').lower()
            if (hl in eh or eh in hl) and (al in ea or ea in al): event=ev; break
        if not event: return {},f'{home} vs {away} non trovata'
        bks=event.get('bookmakers',[])
        chosen=None
        for prio in BK_PRIORITY:
            for bk in bks:
                if bk.get('key','')==prio: chosen=bk; break
            if chosen: break
        if not chosen and bks: chosen=bks[0]
        if not chosen: return {},'Nessun bookmaker'
        odds={'_bk':chosen.get('title',chosen.get('key',''))}
        for mkt in chosen.get('markets',[]):
            key=mkt.get('key','')
            outs={o['name']:o['price'] for o in mkt.get('outcomes',[])}
            if key=='h2h':
                odds['home']=outs.get(event.get('home_team',''),0.0)
                odds['away']=outs.get(event.get('away_team',''),0.0)
                odds['draw']=outs.get('Draw',0.0)
            elif key=='totals':
                for o in mkt.get('outcomes',[]):
                    pt=o.get('point',0);nm=o.get('name','');pr=o.get('price',0)
                    if pt==2.5:
                        if nm=='Over': odds['over25']=pr
                        else: odds['under25']=pr
                    elif pt==3.5:
                        if nm=='Over': odds['over35']=pr
                        else: odds['under35']=pr
            elif key=='btts':
                odds['btts_y']=outs.get('Yes',0.0); odds['btts_n']=outs.get('No',0.0)
        return odds,'ok'
    except Exception as e: return {},str(e)

def fetch_injuries_tm(team_name):
    try:
        h={**REQ_H,'Referer':'https://www.transfermarkt.it'}
        r=requests.get('https://www.transfermarkt.it/schnellsuche/ergebnis/schnellsuche',
                       headers=h,params={'query':team_name},timeout=10)
        if r.status_code!=200: return [],'TM non raggiungibile'
        m=re.search(r'href="(/[^"]+/startseite/verein/\d+[^"]*)"',r.text)
        if not m: return [],f'{team_name} non trovata su TM'
        inj_url='https://www.transfermarkt.it'+re.sub(r'/startseite/','/verletzungen/',m.group(1))
        r2=requests.get(inj_url,headers=h,timeout=10)
        if r2.status_code!=200: return [],'Pagina infortuni non raggiungibile'
        rows=re.findall(r'<tr[^>]*class="[^"]*(?:odd|even)[^"]*"[^>]*>(.*?)</tr>',r2.text,re.DOTALL)
        injuries=[]
        for row in rows[:20]:
            txt=re.sub(r'<[^>]+',' ',row); txt=re.sub(r'\s+',' ',txt).strip()
            if len(txt)<5: continue
            if any(kw in txt.lower() for kw in ['infort','lesion','dubbio','sospett','assent']):
                parts=txt.split()
                if len(parts)>=2:
                    injuries.append({'name':' '.join(parts[:2]),
                                     'status':'out' if 'out' in txt.lower() else 'doubt',
                                     'info':txt[:80]})
        return injuries,'ok'
    except Exception as e: return [],str(e)

def gemini_backup(home, away, comp, what):
    if not GENAI_OK: return {}
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = (f'Trova dati per {home} vs {away} ({comp}). Cerco: {what}. '
                  f'Rispondi SOLO JSON senza markdown. '
                  f'Per stats: {{"gf_home":x,"ga_home":x,"gf_away":x,"ga_away":x}} '
                  f'Per quote: {{"home":x,"draw":x,"away":x,"over25":x,"under25":x,"btts_y":x,"btts_n":x}}')
        resp = model.generate_content(prompt)
        txt = re.sub(r'```json|```','', resp.text).strip()
        return json.loads(txt)
    except: return {}

# ==============================================================================
# UI HELPERS
# ==============================================================================
def sem_html(color): return f'<span class="sem {color}"></span>'
def form_html(s): return ''.join(f'<span class="form-dot {c}">{c}</span>' for c in s[-5:]) if s else '<span style="color:#555;font-size:.7rem">N/D</span>'

def render_rec(m, tipo):
    labels={'best':('🥇 BEST BET','best'),'value':('💰 VALUE BET','value'),'long':('🎲 LONG SHOT','long')}
    lbl,css=labels[tipo]
    if m is None:
        st.markdown(f'<div class="rec-card none"><span class="rec-badge none">Nessuna</span>'
                    f'<div class="rec-market">Quota non inserita o edge negativo</div></div>',unsafe_allow_html=True)
        return
    ec='grn' if m.edge>0.08 else ('yel' if m.edge>0 else 'red')
    pc='grn' if m.prob>0.5 else ('yel' if m.prob>0.3 else 'red')
    warn='<div style="font-size:.65rem;color:var(--red);margin-top:8px">⚠️ Quota bassa</div>' if m.bk<1.5 and m.bk>1 else ''
    st.markdown(
        f'<div class="rec-card {css}"><span class="rec-badge {css}">{lbl}</span>'
        f'<div class="rec-market">{sem_html(m.sem)}{m.emoji} {m.name}</div>'
        f'<div class="rec-desc">{m.desc}</div>'
        f'<div class="rec-nums">'
        f'<div class="rn"><div class="rl">Probabilita</div><div class="rv {pc}">{m.prob*100:.1f}%</div></div>'
        f'<div class="rn"><div class="rl">Quota Fair</div><div class="rv org">{m.fair:.2f}</div></div>'
        f'<div class="rn"><div class="rl">Edge %</div><div class="rv {ec}">{m.edge*100:+.1f}%</div></div>'
        f'</div>{warn}</div>',unsafe_allow_html=True)

def render_mkt(m:MarketResult, show_traffic:bool=False):
    if m.bk<=1.01: css='v-low'; qs='N/D'; ft=''
    elif m.bk<1.5: css='v-bad'; qs=f'{m.bk:.2f}'; ft='<span style="font-size:.58rem;color:var(--red);margin-left:6px">⚠️ Bassa</span>'
    elif m.edge>=0.08: css='v-high'; qs=f'{m.bk:.2f}'; ft=f'<span style="font-size:.58rem;color:var(--grn);margin-left:6px">✅ +{m.edge*100:.1f}%</span>'
    elif m.edge>=0: css='v-med'; qs=f'{m.bk:.2f}'; ft=f'<span style="font-size:.58rem;color:var(--yel);margin-left:6px">⚡ +{m.edge*100:.1f}%</span>'
    else: css='v-low'; qs=f'{m.bk:.2f}'; ft=f'<span style="font-size:.58rem;color:var(--t3);margin-left:6px">{m.edge*100:+.1f}%</span>'
    pc='var(--grn)' if m.prob>0.5 else ('var(--yel)' if m.prob>0.3 else 'var(--t2)')
    tl = getattr(m,'traffic','')
    tl_map = {'SCOMMETTI':'<span style="font-size:.6rem;font-weight:700;color:var(--grn);background:rgba(0,200,150,.15);padding:2px 8px;border-radius:10px">🟢 SCOMMETTI</span>',
              'ASPETTA':'<span style="font-size:.6rem;font-weight:700;color:var(--yel);background:rgba(255,209,102,.15);padding:2px 8px;border-radius:10px">🟡 ASPETTA</span>',
              'EVITA':'<span style="font-size:.6rem;font-weight:700;color:var(--red);background:rgba(255,59,92,.15);padding:2px 8px;border-radius:10px">🔴 EVITA</span>'}
    tl_html = tl_map.get(tl,'') if show_traffic else ''
    st.markdown(
        f'<div class="mkt-row {css}"><div>'
        f'<div class="mkt-name">{sem_html(m.sem)}{m.emoji} {m.name} {tl_html}</div>'
        f'<div class="mkt-sub">Fair: {m.fair:.2f} | Bk: {qs}{ft}</div></div>'
        f'<div style="text-align:right"><div class="mkt-prob" style="color:{pc}">{m.prob*100:.1f}%</div></div>'
        f'</div>',unsafe_allow_html=True)

def render_combo(c:ComboResult):
    ec='var(--grn)' if c.edge_combo>0.05 else ('var(--yel)' if c.edge_combo>0 else 'var(--t2)')
    legs_html=''.join(f'<div class="combo-leg"><span>{l.emoji} {l.name}</span>'
                      f'<span style="color:var(--yel)">{l.bk:.2f if l.bk>1.01 else l.fair:.2f}</span></div>'
                      for l in c.legs)
    st.markdown(
        f'<div class="combo-card"><div class="combo-title">{c.tipo}</div>'
        f'{legs_html}'
        f'<div class="combo-footer">'
        f'<span style="font-size:.7rem;color:var(--t2)">Prob: {c.prob_combo*100:.1f}%</span>'
        f'<span style="font-size:.8rem;font-weight:700;color:{ec}">Quota: {c.quota_combo:.2f}</span>'
        f'</div></div>',unsafe_allow_html=True)

def render_comparison(cmp:Dict):
    if not cmp.get('significant'):
        st.markdown('<div class="banner-warn">⚡ Differenza modello base vs avanzato &lt; 5% — risultati simili</div>',
                    unsafe_allow_html=True)
        return
    b=cmp['base']; adv=cmp['advanced']
    st.markdown(
        f'<div class="cmp-grid">'
        f'<div class="cmp-box base"><div class="cmp-label">Modello Base (Poisson semplice)</div>'
        f'<div class="cmp-val">λ casa: {b["lh"]} | λ trasf: {b["la"]}</div>'
        f'<div class="cmp-val">1: {b["ph"]}% | X: {b["pd"]}% | 2: {b["pa"]}%</div>'
        f'<div class="cmp-val">Over 2.5: {b["ov25"]}%</div></div>'
        f'<div class="cmp-box adv"><div class="cmp-label">Modello Avanzato (Dixon-Coles + peso + casa/trasf)</div>'
        f'<div class="cmp-val">λ casa: {adv["lh"]} | λ trasf: {adv["la"]}</div>'
        f'<div class="cmp-val">1: {adv["ph"]}% | X: {adv["pd"]}% | 2: {adv["pa"]}%</div>'
        f'<div class="cmp-val">Over 2.5: {adv["ov25"]}%</div></div>'
        f'</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="banner-warn">📊 Differenza media: {cmp["diff_pct"]:.1f}% — il modello avanzato e\' significativamente diverso</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sec-title" style="margin-top:12px">Correzioni applicate</div>',unsafe_allow_html=True)
    for note in cmp.get('notes',[]):
        st.markdown(f'<div class="note-item">{note}</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="note-item">Dixon-Coles rho: {cmp["rho"]:.3f} (correzione partite 0-0 e 1-1)</div>',
                unsafe_allow_html=True)

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    st.set_page_config(page_title='Quantum Football v7.0',page_icon='QF',
                       layout='wide',initial_sidebar_state='collapsed')
    st.markdown(CSS,unsafe_allow_html=True)

    if not ENGINE_OK:
        st.error(f'engine.py non trovato: {ENGINE_ERR}. Assicurati che engine.py sia nella stessa cartella di app.py.')
        return

    if 'history' not in st.session_state: st.session_state['history']=[]
    if 'step' not in st.session_state: st.session_state['step']='input'

    with st.sidebar:
        st.markdown('### Impostazioni')
        st.markdown('**Filtro Edge Minimo**')
        edge_min = st.slider('Mostra solo scommesse con edge ≥', 0, 20, 5, 1,
                             help='5% = moderato consigliato. Sotto soglia → EVITA automatico.',
                             key='edge_min_slider')
        st.markdown(f'<div style="font-size:.68rem;color:#ff6b35">Soglia attiva: {edge_min}%</div>',
                    unsafe_allow_html=True)
        st.divider()
        st.markdown('<div style="font-size:.62rem;color:#555">v7.0 FINAL — Gemini AI | Monte Carlo | Stanchezza | Arbitro</div>',unsafe_allow_html=True)
    fd_key = FD_KEY
    odds_key = ODDS_KEY

    st.markdown(
        '<div class="header"><h1>⚽ Quantum Football v7.0 FINAL</h1>'
        '<div class="sub">Motore avanzato: Dixon-Coles • Peso recenti • Stats casa/trasf • H2H 3 anni • Infortuni auto • 30+ mercati • Combo</div></div>',
        unsafe_allow_html=True)

    # ======================================================
    # STEP 1 — INPUT
    # ======================================================
    if st.session_state['step']=='input':
        st.markdown('<div class="section"><div class="sec-title">Inserisci Partita</div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1: paese=st.selectbox('Paese',list(COMPETITIONS.keys()),key='paese_sel')
        with c2: comp=st.selectbox('Competizione',COMPETITIONS[paese],key='comp_sel')
        c3,c4=st.columns(2)
        with c3: h_name=st.text_input('Squadra Casa',placeholder='es. Napoli',key='h_name_in')
        with c4: a_name=st.text_input('Squadra Trasferta',placeholder='es. Torino',key='a_name_in')
        st.markdown('</div>',unsafe_allow_html=True)

        if not fd_key or not odds_key:
            st.markdown('<div class="banner-warn">⚠️ Inserisci le API Key nella sidebar per dati automatici</div>',unsafe_allow_html=True)

        col=st.columns([1,2,1])[1]
        with col: cerca=st.button('🔍 CERCA DATI',use_container_width=True)

        if cerca and h_name and a_name:
            st.session_state.update({'h_name':h_name,'a_name':a_name,'comp':comp,'paese':paese})
            banners=[]; raw={'h_stats':None,'a_stats':None,'odds':{},'inj_h':[],'inj_a':[],'h2h':[]}

            with st.spinner(f'Stats avanzate {h_name}...'):
                hs,msg=fetch_advanced_stats(fd_key,h_name,True) if fd_key else (None,'No FD key')
                if hs: banners.append(('ok',f'✅ {h_name}: {hs.matches_n} partite | GF: {hs.gf_avg:.2f} | xG: {hs.xg_avg:.2f} | Casa: {hs.gf_home:.2f} | Trasf: {hs.gf_away:.2f}')); raw['h_stats']=hs
                else:
                    banners.append(('warn',f'⚠️ {h_name}: {msg}'))
                    bk=gemini_backup(h_name,a_name,comp,'statistiche')
                    if bk:
                        raw['h_stats']=TeamStats(name=h_name,gf_avg=bk.get('gf_home',1.3),ga_avg=bk.get('ga_home',1.1),source='Gemini AI')
                        banners.append(('ok',f'✅ {h_name} da Gemini AI (backup)'))

            with st.spinner(f'Stats avanzate {a_name}...'):
                as_,msg=fetch_advanced_stats(fd_key,a_name,False) if fd_key else (None,'No FD key')
                if as_: banners.append(('ok',f'✅ {a_name}: {as_.matches_n} partite | GF: {as_.gf_avg:.2f} | xG: {as_.xg_avg:.2f} | Casa: {as_.gf_home:.2f} | Trasf: {as_.gf_away:.2f}')); raw['a_stats']=as_
                else:
                    banners.append(('warn',f'⚠️ {a_name}: {msg}'))
                    bk=gemini_backup(h_name,a_name,comp,'statistiche')
                    if bk:
                        raw['a_stats']=TeamStats(name=a_name,gf_avg=bk.get('gf_away',1.1),ga_avg=bk.get('ga_away',1.2),source='Gemini AI')
                        banners.append(('ok',f'✅ {a_name} da Gemini AI (backup)'))

            sport_key=COMP_ODDS.get(comp)
            if sport_key and odds_key:
                with st.spinner(f'Quote {h_name} vs {a_name}...'):
                    odds_data,msg=fetch_odds(odds_key,sport_key,h_name,a_name)
                    if odds_data:
                        banners.append(('ok',f'✅ Quote da {odds_data.get("_bk","")} — 1:{odds_data.get("home","?")} X:{odds_data.get("draw","?")} 2:{odds_data.get("away","?")}'))
                        raw['odds']=odds_data
                    else:
                        banners.append(('err',f'❌ Quote: {msg}'))
                        with st.spinner('Gemini cerca le quote...'):
                            bk=gemini_backup(h_name,a_name,comp,'quote bookmaker')
                            if bk: raw['odds']=bk; banners.append(('ok','✅ Quote da Gemini AI (backup)'))
            else:
                banners.append(('warn','⚠️ Competizione non supportata per le quote automatiche'))

            with st.spinner(f'H2H storico {h_name} vs {a_name} (3 anni)...'):
                h2h_recs,msg=fetch_h2h(fd_key,h_name,a_name,3) if fd_key else ([],'No FD key')
                raw['h2h']=h2h_recs
                if h2h_recs: banners.append(('ok',f'✅ H2H: {len(h2h_recs)} partite negli ultimi 3 anni'))
                else: banners.append(('warn',f'⚠️ H2H: {msg}'))

            with st.spinner(f'Infortuni {h_name}...'):
                inj_h,msg=fetch_injuries_tm(h_name)
                raw['inj_h']=inj_h
                if inj_h: banners.append(('ok',f'✅ {len(inj_h)} infortuni {h_name}'))

            with st.spinner(f'Infortuni {a_name}...'):
                inj_a,msg=fetch_injuries_tm(a_name)
                raw['inj_a']=inj_a
                if inj_a: banners.append(('ok',f'✅ {len(inj_a)} infortuni {a_name}'))

            st.session_state.update({'raw':raw,'banners':banners,'step':'review'})
            st.rerun()

    # ======================================================
    # STEP 2 — REVIEW + MOTIVAZIONE
    # ======================================================
    elif st.session_state['step']=='review':
        raw=st.session_state.get('raw',{})
        banners=st.session_state.get('banners',[])
        h_name=st.session_state.get('h_name','Casa')
        a_name=st.session_state.get('a_name','Trasferta')
        comp=st.session_state.get('comp','')

        for btype,msg in banners:
            css='banner-ok' if btype=='ok' else ('banner-err' if btype=='err' else 'banner-warn')
            st.markdown(f'<div class="{css}">{msg}</div>',unsafe_allow_html=True)

        h_raw:TeamStats=raw.get('h_stats') or TeamStats(name=h_name)
        a_raw:TeamStats=raw.get('a_stats') or TeamStats(name=a_name)
        odds_raw:Dict=raw.get('odds',{})
        inj_h=raw.get('inj_h',[])
        inj_a=raw.get('inj_a',[])
        h2h_recs=raw.get('h2h',[])

        st.markdown('<div class="section"><div class="sec-title">Fattori Partita</div>',unsafe_allow_html=True)
        st.markdown('<div style="font-size:.65rem;color:var(--t2);margin-bottom:8px">MOTIVAZIONE</div>',unsafe_allow_html=True)
        mc1,mc2=st.columns(2)
        with mc1: motiv_h=st.slider(f'{h_name}',-20,20,0,1,key='motiv_h',help='-20% gia salva | +20% deve vincere')
        with mc2: motiv_a=st.slider(f'{a_name}',-20,20,0,1,key='motiv_a')
        st.markdown('<div style="font-size:.65rem;color:var(--t2);margin:10px 0 6px">STANCHEZZA (giorni riposo)</div>',unsafe_allow_html=True)
        sc1,sc2=st.columns(2)
        with sc1:
            days_h=st.slider(f'{h_name} riposo',1,14,7,1,key='days_h')
            if days_h<3: st.markdown('<div class="banner-err">⚡ Stanca: -8%</div>',unsafe_allow_html=True)
            elif days_h<5: st.markdown('<div class="banner-warn">⚡ Semi-fatica: -4%</div>',unsafe_allow_html=True)
        with sc2:
            days_a=st.slider(f'{a_name} riposo',1,14,7,1,key='days_a')
            if days_a<3: st.markdown('<div class="banner-err">⚡ Stanca: -8%</div>',unsafe_allow_html=True)
            elif days_a<5: st.markdown('<div class="banner-warn">⚡ Semi-fatica: -4%</div>',unsafe_allow_html=True)
        st.markdown('<div style="font-size:.65rem;color:var(--t2);margin:10px 0 6px">PRESSIONE PSICOLOGICA</div>',unsafe_allow_html=True)
        pc1,pc2=st.columns(2)
        with pc1: pressure_h=st.slider(f'{h_name} pressione',-10,10,0,1,key='pres_h')
        with pc2: pressure_a=st.slider(f'{a_name} pressione',-10,10,0,1,key='pres_a')
        st.markdown('<div style="font-size:.65rem;color:var(--t2);margin:10px 0 6px">ARBITRO</div>',unsafe_allow_html=True)
        ref1,ref2=st.columns(2)
        with ref1: ref_name=st.text_input('Nome arbitro (opzionale)',placeholder='es. Orsato',key='ref_name')
        with ref2:
            ref_style=st.select_slider('Stile',options=['Molto permissivo','Permissivo','Normale','Rigido','Molto rigido'],value='Normale',key='ref_style')
            ref_mult={'Molto permissivo':0.7,'Permissivo':0.85,'Normale':1.0,'Rigido':1.2,'Molto rigido':1.4}[ref_style]
            if ref_mult!=1.0: st.markdown(f'<div class="banner-warn">🟨 Cartellini x{ref_mult:.1f}</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)

        # Infortuni rilevati
        if inj_h or inj_a:
            st.markdown('<div class="section"><div class="sec-title">Infortuni Rilevati (impatto automatico)</div>',unsafe_allow_html=True)
            ci1,ci2=st.columns(2)
            with ci1:
                imp_h=estimate_injury_impact(inj_h,h_name)
                if inj_h:
                    st.markdown(f'<div class="banner-err">🏥 {h_name}: -{imp_h*100:.1f}% attacco stimato</div>',unsafe_allow_html=True)
                    for inj in inj_h[:5]:
                        st.markdown(f'<div class="note-item">{"❌" if inj["status"]=="out" else "⚠️"} {inj["name"]} — {inj["info"]}</div>',unsafe_allow_html=True)
            with ci2:
                imp_a=estimate_injury_impact(inj_a,a_name)
                if inj_a:
                    st.markdown(f'<div class="banner-err">🏥 {a_name}: -{imp_a*100:.1f}% attacco stimato</div>',unsafe_allow_html=True)
                    for inj in inj_a[:5]:
                        st.markdown(f'<div class="note-item">{"❌" if inj["status"]=="out" else "⚠️"} {inj["name"]} — {inj["info"]}</div>',unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)

        # Dati modificabili
        with st.expander(f'📊 Dati {h_name} — modifica se necessario',expanded=False):
            r1,r2,r3,r4=st.columns(4)
            with r1: h_gf =st.number_input('GF/gara', 0.0,15.0,float(h_raw.gf_avg), 0.1,key='h_gf')
            with r2: h_ga =st.number_input('GA/gara', 0.0,15.0,float(h_raw.ga_avg), 0.1,key='h_ga')
            with r3: h_xg =st.number_input('xG/gara', 0.0,15.0,float(h_raw.xg_avg), 0.1,key='h_xg')
            with r4: h_xga=st.number_input('xGA/gara',0.0,15.0,float(h_raw.xga_avg),0.1,key='h_xga')
            r5,r6,r7,r8=st.columns(4)
            with r5: h_cor=st.number_input('Angoli',  0.0,20.0,float(h_raw.corners_avg),0.5,key='h_cor')
            with r6: h_crd=st.number_input('Cartellini',0.0,10.0,float(h_raw.cards_avg),0.5,key='h_crd')
            with r7: h_sot=st.number_input('Tiri porta',0.0,20.0,float(h_raw.shots_ot_avg),0.5,key='h_sot')
            with r8: h_form=st.text_input('Forma',value=h_raw.form,key='h_form')

        with st.expander(f'📊 Dati {a_name} — modifica se necessario',expanded=False):
            r1,r2,r3,r4=st.columns(4)
            with r1: a_gf =st.number_input('GF/gara', 0.0,15.0,float(a_raw.gf_avg), 0.1,key='a_gf')
            with r2: a_ga =st.number_input('GA/gara', 0.0,15.0,float(a_raw.ga_avg), 0.1,key='a_ga')
            with r3: a_xg =st.number_input('xG/gara', 0.0,15.0,float(a_raw.xg_avg), 0.1,key='a_xg')
            with r4: a_xga=st.number_input('xGA/gara',0.0,15.0,float(a_raw.xga_avg),0.1,key='a_xga')
            r5,r6,r7,r8=st.columns(4)
            with r5: a_cor=st.number_input('Angoli',  0.0,20.0,float(a_raw.corners_avg),0.5,key='a_cor')
            with r6: a_crd=st.number_input('Cartellini',0.0,10.0,float(a_raw.cards_avg),0.5,key='a_crd')
            with r7: a_sot=st.number_input('Tiri porta',0.0,20.0,float(a_raw.shots_ot_avg),0.5,key='a_sot')
            with r8: a_form=st.text_input('Forma',value=a_raw.form,key='a_form')

        with st.expander('💰 Quote — modifica se necessario',expanded=False):
            q1,q2,q3=st.columns(3)
            with q1:
                q_home=st.number_input('1 Casa',   0.0,50.0,float(odds_raw.get('home',0.0)),0.05,key='q_home')
                q_ov25=st.number_input('Over 2.5', 0.0,50.0,float(odds_raw.get('over25',0.0)),0.05,key='q_ov25')
                q_btts=st.number_input('BTTS Si',  0.0,50.0,float(odds_raw.get('btts_y',0.0)),0.05,key='q_btts')
            with q2:
                q_draw=st.number_input('X Pari',   0.0,50.0,float(odds_raw.get('draw',0.0)),0.05,key='q_draw')
                q_un25=st.number_input('Under 2.5',0.0,50.0,float(odds_raw.get('under25',0.0)),0.05,key='q_un25')
                q_bttsn=st.number_input('BTTS No', 0.0,50.0,float(odds_raw.get('btts_n',0.0)),0.05,key='q_bttsn')
            with q3:
                q_away=st.number_input('2 Trasf.', 0.0,50.0,float(odds_raw.get('away',0.0)),0.05,key='q_away')
                q_ov35=st.number_input('Over 3.5', 0.0,50.0,float(odds_raw.get('over35',0.0)),0.05,key='q_ov35')
                q_un35=st.number_input('Under 3.5',0.0,50.0,float(odds_raw.get('under35',0.0)),0.05,key='q_un35')

        cb1,cb2=st.columns(2)
        with cb1: analizza=st.button('⚡ ANALIZZA',use_container_width=True)
        with cb2:
            if st.button('🔄 RESET',use_container_width=True):
                for k in ['step','raw','banners','result_v6','h_name','a_name']:
                    st.session_state.pop(k,None)
                st.rerun()

        if analizza:
            h=TeamStats(name=h_name,gf_avg=h_gf,ga_avg=h_ga,xg_avg=h_xg,xga_avg=h_xga,
                        corners_avg=h_cor,cards_avg=h_crd,shots_ot_avg=h_sot,
                        form=h_form.upper() if 'h_form' in dir() else h_raw.form,
                        gf_home=h_raw.gf_home,ga_home=h_raw.ga_home,
                        gf_away=h_raw.gf_away,ga_away=h_raw.ga_away,
                        xg_home=h_raw.xg_home,xg_away=h_raw.xg_away,
                        records=h_raw.records)
            a=TeamStats(name=a_name,gf_avg=a_gf,ga_avg=a_ga,xg_avg=a_xg,xga_avg=a_xga,
                        corners_avg=a_cor,cards_avg=a_crd,shots_ot_avg=a_sot,
                        form=a_form.upper() if 'a_form' in dir() else a_raw.form,
                        gf_home=a_raw.gf_home,ga_home=a_raw.ga_home,
                        gf_away=a_raw.gf_away,ga_away=a_raw.ga_away,
                        xg_home=a_raw.xg_home,xg_away=a_raw.xg_away,
                        records=a_raw.records)
            odds={'home':q_home,'draw':q_draw,'away':q_away,
                  'over25':q_ov25,'under25':q_un25,'over35':q_ov35,'under35':q_un35,
                  'btts_y':q_btts,'btts_n':q_bttsn}
            eng=AdvancedEngine(h,a,motiv_h,motiv_a,inj_h,inj_a,h2h_recs,
                               days_rest_h=days_h,days_rest_a=days_a,
                               pressure_h=pressure_h,pressure_a=pressure_a,
                               league_name=comp,referee_cards_mult=ref_mult)
            mkts=build_markets(eng,h,a,odds)
            combos=build_combos(mkts,h_name,a_name)
            scores=eng.top_scores(6)
            recs=build_recs(mkts)
            htft=eng.htft_probs()
            cmp=eng.comparison_report()
            h2h_sum=h2h_summary(h2h_recs,h_name)
            # Monte Carlo 50k simulazioni
            with st.spinner('Monte Carlo 50.000 simulazioni...'):
                mc = monte_carlo(eng.lh, eng.la, eng.rho, n_sim=50000)

            # Controlli incrociati
            edge_thr = st.session_state.get('edge_min_slider', 5) / 100.0
            consistency_warns = check_internal_consistency(mkts, eng.lh, eng.la)
            traps = detect_traps(mkts, eng.lh, eng.la)
            conf = confidence_score(h, a, h2h_recs, inj_h, inj_a, odds)
            bk_comparison = bookmaker_implied_comparison(mkts)

            # Semaforo per ogni mercato
            for m in mkts:
                m.traffic = traffic_light(m, edge_thr, mc, conf['score'], traps, consistency_warns)

            result=dict(h=h,a=a,comp=comp,eng=eng,mkts=mkts,combos=combos,
                        scores=scores,recs=recs,htft=htft,cmp=cmp,
                        inj_h=inj_h,inj_a=inj_a,h2h_recs=h2h_recs,h2h_sum=h2h_sum,
                        mc=mc, consistency_warns=consistency_warns, traps=traps,
                        conf=conf, bk_comparison=bk_comparison, edge_thr=edge_thr)
            st.session_state['result_v6']=result
            hist=st.session_state.get('history',[])
            hist.insert(0,{'match':f'{h_name} vs {a_name}','comp':comp,
                           'ts':datetime.now().strftime('%d/%m %H:%M'),
                           'lh':eng.lh,'la':eng.la,'diff':cmp['diff_pct']})
            st.session_state['history']=hist[:5]
            st.session_state['step']='results'
            st.rerun()

    # ======================================================
    # STEP 3 — RISULTATI
    # ======================================================
    elif st.session_state['step']=='results':
        R=st.session_state.get('result_v6',{})
        if not R: st.session_state['step']='input'; st.rerun(); return

        h:TeamStats=R['h']; a:TeamStats=R['a']; eng:AdvancedEngine=R['eng']
        mkts=R['mkts']; combos=R['combos']; scores=R['scores']
        recs=R['recs']; htft=R['htft']; cmp=R['cmp']
        inj_h=R['inj_h']; inj_a=R['inj_a']
        h2h_recs=R['h2h_recs']; h2h_sum=R['h2h_sum']
        mc=R.get('mc',{}); conf=R.get('conf',{'score':50,'color':'giallo','verdict':'N/D','details':[]})
        traps=R.get('traps',[]); consistency_warns=R.get('consistency_warns',[])
        bk_comparison=R.get('bk_comparison',[]); edge_thr=R.get('edge_thr',0.05)

        st.markdown(
            f'<div class="header" style="padding:14px 20px">'
            f'<div style="font-size:1.1rem;font-weight:700">{h.name} vs {a.name}</div>'
            f'<div class="sub">{R["comp"]} | λ avanzato: {eng.lh:.2f} vs {eng.la:.2f} | '
            f'DC rho: {eng.rho:.3f}</div></div>',
            unsafe_allow_html=True)

        # CONFIDENCE SCORE
        conf_color_map = {'verde':'#00c896','giallo':'#ffd166','rosso':'#ff3b5c'}
        cc = conf_color_map.get(conf['color'],'#888')
        st.markdown(
            f'<div style="background:var(--bg1);border:1px solid var(--br1);border-radius:10px;'
            f'padding:12px 18px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center">'
            f'<div><div style="font-size:.62rem;color:var(--t2);text-transform:uppercase;letter-spacing:.12em">Confidenza Modello</div>'
            f'<div style="font-size:.85rem;color:{cc};font-weight:600;margin-top:4px">{conf["verdict"]}</div></div>'
            f'<div style="text-align:center">'
            f'<div style="font-size:2rem;font-weight:700;color:{cc}">{conf["score"]}</div>'
            f'<div style="font-size:.58rem;color:var(--t2)">/100</div></div>'
            f'<div style="text-align:right">'
            f'<div style="font-size:.62rem;color:var(--t2)">Filtro edge attivo</div>'
            f'<div style="font-size:.85rem;color:var(--org);font-weight:600">&gt;{edge_thr*100:.0f}%</div></div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # ALERTS TRAPPOLE
        if traps:
            for t in traps[:3]:
                css = 'banner-err' if t['level']=='danger' else 'banner-warn'
                st.markdown(f'<div class="{css}">{t["msg"]}</div>', unsafe_allow_html=True)

        # ALERTS COERENZA
        if consistency_warns:
            for w in consistency_warns[:2]:
                st.markdown(f'<div class="banner-warn">{w["msg"]}</div>', unsafe_allow_html=True)

        if st.button('🔄 Nuova Partita'):
            for k in ['step','raw','banners','result_v6','h_name','a_name']:
                st.session_state.pop(k,None)
            st.session_state['step']='input'; st.rerun()

        # RACCOMANDAZIONI
        st.markdown('<div class="section"><div class="sec-title">🎯 Raccomandazioni</div>',unsafe_allow_html=True)
        r1,r2,r3=st.columns(3)
        with r1: render_rec(recs['best'],'best')
        with r2: render_rec(recs['value'],'value')
        with r3: render_rec(recs['long'],'long')
        st.markdown('</div>',unsafe_allow_html=True)

        # TABS
        tabs=st.tabs(['1X2 & DC','O/U & Tempi','BTTS & Multi','Gol Squadre',
                      'Speciali','Combo','H2H & Squadre','Confronto Modello','🛡️ Safety Check'])

        def get_cat(cat): return sorted([m for m in mkts if m.cat==cat],key=lambda x:-abs(x.edge) if x.bk>1.01 else -x.prob)

        with tabs[0]:
            st.markdown('<div class="sec-title">1X2</div>',unsafe_allow_html=True)
            for m in get_cat('1X2'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Doppia Chance</div>',unsafe_allow_html=True)
            for m in get_cat('Doppia Chance'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Draw No Bet</div>',unsafe_allow_html=True)
            for m in get_cat('Draw No Bet'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">HT/FT Top 4</div>',unsafe_allow_html=True)
            top_htft=sorted(htft.items(),key=lambda x:-x[1])[:4]
            cols=st.columns(4)
            for idx,(k,v) in enumerate(top_htft):
                with cols[idx]:
                    st.markdown(f'<div class="stat-box"><div class="sb-label">{k}</div><div class="sb-val">{v*100:.1f}%</div><div class="sb-sub">Fair: {1/max(v,0.001):.1f}</div></div>',unsafe_allow_html=True)

        with tabs[1]:
            st.markdown('<div class="sec-title">Over / Under</div>',unsafe_allow_html=True)
            for m in get_cat('Over/Under'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Primo Tempo</div>',unsafe_allow_html=True)
            for m in get_cat('Primo Tempo'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Secondo Tempo</div>',unsafe_allow_html=True)
            for m in get_cat('Secondo Tempo'): render_mkt(m)

        with tabs[2]:
            st.markdown('<div class="sec-title">BTTS</div>',unsafe_allow_html=True)
            for m in get_cat('BTTS'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Multigoal Totale</div>',unsafe_allow_html=True)
            for m in get_cat('Multigoal Totale'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Gol Esatti</div>',unsafe_allow_html=True)
            for m in get_cat('Gol Esatti'): render_mkt(m)

        with tabs[3]:
            ch,ca=st.columns(2)
            with ch:
                st.markdown(f'<div class="sec-title">Gol {h.name}</div>',unsafe_allow_html=True)
                for m in get_cat('Gol Casa'): render_mkt(m)
            with ca:
                st.markdown(f'<div class="sec-title">Gol {a.name}</div>',unsafe_allow_html=True)
                for m in get_cat('Gol Ospite'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Segna entrambi i tempi</div>',unsafe_allow_html=True)
            for m in get_cat('Speciali'): render_mkt(m)

        with tabs[4]:
            st.markdown('<div class="sec-title">Risultati Esatti</div>',unsafe_allow_html=True)
            cols=st.columns(3)
            for idx,sc in enumerate(scores):
                with cols[idx%3]:
                    cmap={'Casa':'var(--org)','Pari':'var(--yel)','Trasf':'var(--blu)'}
                    c=cmap.get(sc['cat'],'var(--t1)')
                    st.markdown(f'<div class="stat-box"><div class="sb-label">{sc["cat"]}</div>'
                                f'<div class="sb-val" style="font-size:1.5rem;color:{c}">{sc["score"]}</div>'
                                f'<div class="sb-sub">{sc["prob_pct"]:.2f}% | Fair: {sc["fair"]:.1f}</div></div>',unsafe_allow_html=True)
            st.markdown('<div class="sec-title" style="margin-top:14px">Handicap & Winning Margin</div>',unsafe_allow_html=True)
            for m in get_cat('Handicap')+get_cat('Winning Margin'): render_mkt(m)
            st.markdown('<div class="sec-title" style="margin-top:14px">Angoli & Cartellini</div>',unsafe_allow_html=True)
            for m in get_cat('Angoli')+get_cat('Cartellini'): render_mkt(m)

        with tabs[5]:
            st.markdown('<div class="sec-title">Combo (ordinate per probabilita)</div>',unsafe_allow_html=True)
            if combos:
                for c in combos[:15]: render_combo(c)
            else:
                st.markdown('<div class="banner-warn">⚠️ Inserisci le quote per combo con edge</div>',unsafe_allow_html=True)

        with tabs[6]:
            sh,sa=st.columns(2)
            with sh:
                st.markdown(f'<div class="sec-title">{h.name}</div>',unsafe_allow_html=True)
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">'
                    f'<div class="stat-box"><div class="sb-label">GF/gara</div><div class="sb-val">{h.gf_avg:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">GF Casa</div><div class="sb-val">{h.gf_home:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">GF Trasf</div><div class="sb-val">{h.gf_away:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">xG/gara</div><div class="sb-val">{h.xg_avg:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">λ avanzato</div><div class="sb-val">{eng.lh:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">Angoli</div><div class="sb-val">{h.corners_avg:.1f}</div></div>'
                    f'</div>',unsafe_allow_html=True)
                if h.form: st.markdown(f'<div style="margin-top:10px">{form_html(h.form)}</div>',unsafe_allow_html=True)
                if inj_h:
                    st.markdown('<div class="sec-title" style="margin-top:12px">Infortuni</div>',unsafe_allow_html=True)
                    for inj in inj_h:
                        c='var(--red)' if inj['status']=='out' else 'var(--yel)'
                        st.markdown(f'<div style="background:var(--bg2);border-left:3px solid {c};border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:5px;font-size:.72rem"><strong>{inj["name"]}</strong> — {inj["info"]}</div>',unsafe_allow_html=True)
            with sa:
                st.markdown(f'<div class="sec-title">{a.name}</div>',unsafe_allow_html=True)
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">'
                    f'<div class="stat-box"><div class="sb-label">GF/gara</div><div class="sb-val">{a.gf_avg:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">GF Casa</div><div class="sb-val">{a.gf_home:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">GF Trasf</div><div class="sb-val">{a.gf_away:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">xG/gara</div><div class="sb-val">{a.xg_avg:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">λ avanzato</div><div class="sb-val">{eng.la:.2f}</div></div>'
                    f'<div class="stat-box"><div class="sb-label">Angoli</div><div class="sb-val">{a.corners_avg:.1f}</div></div>'
                    f'</div>',unsafe_allow_html=True)
                if a.form: st.markdown(f'<div style="margin-top:10px">{form_html(a.form)}</div>',unsafe_allow_html=True)
                if inj_a:
                    st.markdown('<div class="sec-title" style="margin-top:12px">Infortuni</div>',unsafe_allow_html=True)
                    for inj in inj_a:
                        c='var(--red)' if inj['status']=='out' else 'var(--yel)'
                        st.markdown(f'<div style="background:var(--bg2);border-left:3px solid {c};border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:5px;font-size:.72rem"><strong>{inj["name"]}</strong> — {inj["info"]}</div>',unsafe_allow_html=True)

            # H2H
            if h2h_recs:
                st.markdown('<div class="sec-title" style="margin-top:14px">Testa a Testa — ultimi 3 anni</div>',unsafe_allow_html=True)
                if h2h_sum:
                    hc1,hc2,hc3,hc4=st.columns(4)
                    with hc1: st.markdown(f'<div class="stat-box"><div class="sb-label">Partite</div><div class="sb-val">{h2h_sum["n"]}</div></div>',unsafe_allow_html=True)
                    with hc2: st.markdown(f'<div class="stat-box"><div class="sb-label">{h.name} W</div><div class="sb-val" style="color:var(--grn)">{h2h_sum["w"]}</div></div>',unsafe_allow_html=True)
                    with hc3: st.markdown(f'<div class="stat-box"><div class="sb-label">Pareggi</div><div class="sb-val" style="color:var(--yel)">{h2h_sum["d"]}</div></div>',unsafe_allow_html=True)
                    with hc4: st.markdown(f'<div class="stat-box"><div class="sb-label">{a.name} W</div><div class="sb-val" style="color:var(--blu)">{h2h_sum["l"]}</div></div>',unsafe_allow_html=True)
                for rec in h2h_recs[:6]:
                    res_col='var(--grn)' if rec.score_h>rec.score_a else ('var(--yel)' if rec.score_h==rec.score_a else 'var(--red)')
                    st.markdown(
                        f'<div class="h2h-row">'
                        f'<span style="color:var(--t2)">{rec.date}</span>'
                        f'<span>{rec.home} vs {rec.away}</span>'
                        f'<span style="font-weight:700;color:{res_col}">{rec.score_h}-{rec.score_a}</span>'
                        f'<span style="color:var(--t3);font-size:.62rem">peso: {rec.year_weight:.1f}</span>'
                        f'</div>',unsafe_allow_html=True)

        with tabs[7]:
            st.markdown('<div class="sec-title">Confronto Modello Base vs Avanzato</div>',unsafe_allow_html=True)
            render_comparison(cmp)

        # TAB SAFETY CHECK (tab index 8)
        with tabs[8]:
            st.markdown('<div class="sec-title">🛡️ Safety Check — Analisi Rischio Completa</div>', unsafe_allow_html=True)

            # Confidenza dettaglio
            st.markdown('<div class="sec-title" style="margin-top:4px">Confidenza Modello</div>', unsafe_allow_html=True)
            for d in conf.get('details',[]):
                bg = 'rgba(0,200,150,.06)' if '✅' in d else ('rgba(255,59,92,.06)' if '❌' in d else 'rgba(255,209,102,.06)')
                st.markdown(f'<div style="background:{bg};border-radius:6px;padding:8px 12px;margin-bottom:5px;font-size:.73rem">{d}</div>', unsafe_allow_html=True)

            # Monte Carlo
            if mc:
                st.markdown('<div class="sec-title" style="margin-top:14px">Monte Carlo — {:,} Simulazioni</div>'.format(mc.get('n_sim',0)), unsafe_allow_html=True)
                mc1,mc2,mc3,mc4 = st.columns(4)
                with mc1: st.markdown(f'<div class="stat-box"><div class="sb-label">Media Gol Casa</div><div class="sb-val">{mc.get("avg_goals_h",0):.2f}</div></div>', unsafe_allow_html=True)
                with mc2: st.markdown(f'<div class="stat-box"><div class="sb-label">Media Gol Trasf</div><div class="sb-val">{mc.get("avg_goals_a",0):.2f}</div></div>', unsafe_allow_html=True)
                with mc3: st.markdown(f'<div class="stat-box"><div class="sb-label">Media Totale</div><div class="sb-val">{mc.get("avg_total",0):.2f}</div></div>', unsafe_allow_html=True)
                with mc4: st.markdown(f'<div class="stat-box"><div class="sb-label">BTTS Simulato</div><div class="sb-val">{mc.get("btts",0)*100:.1f}%</div></div>', unsafe_allow_html=True)

                st.markdown('<div style="margin-top:10px"></div>', unsafe_allow_html=True)
                ci = mc.get('ci', {})
                ci_items = [
                    ('Casa vince','home_win'),('Pareggio','draw'),('Trasf vince','away_win'),
                    ('Over 2.5','over25'),('BTTS','btts'),
                ]
                for label, key in ci_items:
                    if key in ci:
                        lo, hi = ci[key]
                        mid = mc.get(key.replace('home_win','home_win').replace('away_win','away_win'), (lo+hi)/2)
                        if key == 'home_win': mid = mc.get('home_win',(lo+hi)/2)
                        elif key == 'away_win': mid = mc.get('away_win',(lo+hi)/2)
                        elif key == 'draw': mid = mc.get('draw',(lo+hi)/2)
                        elif key == 'over25': mid = mc.get('over25',(lo+hi)/2)
                        elif key == 'btts': mid = mc.get('btts',(lo+hi)/2)
                        st.markdown(
                            f'<div style="background:var(--bg2);border:1px solid var(--br1);border-radius:8px;padding:10px 14px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center">'
                            f'<span style="font-size:.73rem">{label}</span>'
                            f'<span style="font-size:.73rem;color:var(--t2)">CI 90%: {lo*100:.1f}% — {hi*100:.1f}%</span>'
                            f'<span style="font-size:.85rem;font-weight:700;color:var(--org)">{mid*100:.1f}%</span>'
                            f'</div>', unsafe_allow_html=True)

            # Confronto prob modello vs bookmaker
            if bk_comparison:
                st.markdown('<div class="sec-title" style="margin-top:14px">Confronto Modello vs Bookmaker</div>', unsafe_allow_html=True)
                for cmp_item in bk_comparison:
                    sig_color = 'var(--grn)' if cmp_item['signal']=='value' else 'var(--red)'
                    st.markdown(
                        f'<div style="background:var(--bg2);border:1px solid var(--br1);border-radius:8px;padding:10px 14px;margin-bottom:6px">'
                        f'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
                        f'<span style="font-size:.75rem;font-weight:600">{cmp_item["name"]}</span>'
                        f'<span style="font-size:.75rem;color:{sig_color};font-weight:700">{cmp_item["diff_pct"]:+.1f}%</span>'
                        f'</div>'
                        f'<div style="font-size:.65rem;color:var(--t2)">'
                        f'Modello: {cmp_item["model_prob"]}% | Bookmaker implicita: {cmp_item["implied_prob"]}% | Quota: {cmp_item["bk"]:.2f}</div>'
                        f'<div style="font-size:.65rem;color:{sig_color};margin-top:3px">{cmp_item["interpretation"]}</div>'
                        f'</div>', unsafe_allow_html=True)

            # Semaforo su tutti i mercati con quota
            st.markdown('<div class="sec-title" style="margin-top:14px">Semaforo Scommesse</div>', unsafe_allow_html=True)
            mkt_with_bk = [m for m in mkts if m.bk > 1.01]
            scommetti = [m for m in mkt_with_bk if getattr(m,'traffic','')=='SCOMMETTI']
            aspetta = [m for m in mkt_with_bk if getattr(m,'traffic','')=='ASPETTA']
            evita = [m for m in mkt_with_bk if getattr(m,'traffic','')=='EVITA']

            if scommetti:
                st.markdown('<div style="font-size:.65rem;font-weight:600;color:var(--grn);margin:8px 0 4px">🟢 SCOMMETTI</div>', unsafe_allow_html=True)
                for m in scommetti: render_mkt(m, show_traffic=False)
            if aspetta:
                st.markdown('<div style="font-size:.65rem;font-weight:600;color:var(--yel);margin:8px 0 4px">🟡 ASPETTA / RIVALUTA</div>', unsafe_allow_html=True)
                for m in aspetta: render_mkt(m, show_traffic=False)
            if evita:
                st.markdown('<div style="font-size:.65rem;font-weight:600;color:var(--red);margin:8px 0 4px">🔴 EVITA</div>', unsafe_allow_html=True)
                for m in evita[:5]: render_mkt(m, show_traffic=False)

    # Storico
    history=st.session_state.get('history',[])
    if history:
        with st.expander('📋 Ultime 5 partite analizzate',expanded=False):
            for item in history:
                diff_str=f' | Diff modello: {item["diff"]:.1f}%' if item.get('diff',0)>0 else ''
                st.markdown(
                    f'<div class="hist-row"><strong>{item["match"]}</strong> — {item["comp"]}'
                    f'<span style="float:right;color:var(--t2)">{item["ts"]} | λ {item["lh"]} vs {item["la"]}{diff_str}</span></div>',
                    unsafe_allow_html=True)

if __name__=='__main__':
    main()
