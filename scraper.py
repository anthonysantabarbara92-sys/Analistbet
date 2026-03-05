# -*- coding: utf-8 -*-
# QUANTUM FOOTBALL SCRAPER v1.0
# Dati automatici da:
#   - Football-Data.org  -> statistiche squadre
#   - The Odds API       -> quote Sportium
#   - Transfermarkt      -> infortuni e rosa

import streamlit as st
import requests
import json
import re
import time
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&display=swap');
:root {
  --bg0:#0a0a0f;--bg1:#0f0f1a;--bg2:#12121e;
  --br1:#1e1e35;--br2:#2a2a50;
  --org:#ff6600;--grn:#00ff88;--red:#ff3355;
  --blu:#00aaff;--yel:#ffcc00;
  --t1:#e8e8f0;--t2:#8888aa;
  --fm:'IBM Plex Mono',monospace;
}
html,body,[class*="css"]{font-family:var(--fm)!important;background:var(--bg0)!important;color:var(--t1)!important;}
.stApp{background:var(--bg0)!important;}
[data-testid="stSidebar"]{background:var(--bg1)!important;border-right:1px solid var(--br1)!important;}
.bh{background:linear-gradient(135deg,var(--bg1),#0d0d20);border:1px solid var(--br1);
  border-left:3px solid var(--org);border-radius:6px;padding:18px 26px;margin-bottom:18px;}
.bh h1{font-family:var(--fm)!important;font-size:1.3rem!important;font-weight:700!important;
  color:var(--org)!important;margin:0!important;text-transform:uppercase;}
.bh .sub{font-size:.6rem;color:var(--t2);margin-top:4px;text-transform:uppercase;letter-spacing:.15em;}
.sh{display:flex;align-items:center;gap:10px;margin:18px 0 9px;padding-bottom:7px;border-bottom:1px solid var(--br1);}
.sh h3{font-family:var(--fm)!important;font-size:.68rem!important;font-weight:600!important;
  color:var(--t2)!important;letter-spacing:.2em!important;text-transform:uppercase!important;margin:0!important;}
.mg{display:grid;gap:10px;margin:12px 0;}
.mg4{grid-template-columns:repeat(4,1fr);}
.mg3{grid-template-columns:repeat(3,1fr);}
.mg2{grid-template-columns:repeat(2,1fr);}
.mc{background:var(--bg2);border:1px solid var(--br1);border-radius:6px;padding:13px 17px;position:relative;}
.mc .lbl{font-size:.55rem;color:var(--t2);letter-spacing:.18em;text-transform:uppercase;margin-bottom:4px;}
.mc .val{font-size:1.2rem;font-weight:700;line-height:1;}
.mc .dlt{font-size:.6rem;margin-top:3px;color:var(--t2);}
.mc .ab{position:absolute;top:0;left:0;width:3px;height:100%;border-radius:6px 0 0 6px;}
.mc.org .val{color:var(--org);}.mc.org .ab{background:var(--org);}
.mc.grn .val{color:var(--grn);}.mc.grn .ab{background:var(--grn);}
.mc.red .val{color:var(--red);}.mc.red .ab{background:var(--red);}
.mc.blu .val{color:var(--blu);}.mc.blu .ab{background:var(--blu);}
.mc.yel .val{color:var(--yel);}.mc.yel .ab{background:var(--yel);}
.inj{background:var(--bg2);border:1px solid var(--br1);border-radius:6px;padding:11px 15px;margin-bottom:7px;}
.inj.out{border-left:3px solid var(--red);}
.inj.doubt{border-left:3px solid var(--yel);}
.inj .pname{font-size:.8rem;font-weight:600;color:var(--t1);}
.inj .pinfo{font-size:.6rem;color:var(--t2);margin-top:3px;}
.stButton>button{background:transparent!important;border:1px solid var(--org)!important;
  color:var(--org)!important;font-family:var(--fm)!important;font-size:.68rem!important;
  font-weight:600!important;letter-spacing:.1em!important;text-transform:uppercase!important;border-radius:4px!important;}
.stButton>button:hover{background:rgba(255,102,0,.1)!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--bg1)!important;border-bottom:1px solid var(--br1)!important;}
.stTabs [data-baseweb="tab"]{font-family:var(--fm)!important;font-size:.62rem!important;
  color:var(--t2)!important;background:transparent!important;text-transform:uppercase!important;padding:9px 13px!important;}
.stTabs [aria-selected="true"]{color:var(--org)!important;border-bottom:2px solid var(--org)!important;}
.ok-box{background:rgba(0,255,136,.06);border:1px solid rgba(0,255,136,.25);border-radius:6px;padding:12px 18px;margin:10px 0;font-size:.72rem;color:var(--grn);}
.warn-box{background:rgba(255,204,0,.06);border:1px solid rgba(255,204,0,.25);border-radius:6px;padding:12px 18px;margin:10px 0;font-size:.72rem;color:var(--yel);}
.err-box{background:rgba(255,51,85,.06);border:1px solid rgba(255,51,85,.25);border-radius:6px;padding:12px 18px;margin:10px 0;font-size:.72rem;color:var(--red);}
#MainMenu,footer,header,.stDeployButton{visibility:hidden!important;display:none!important;}
</style>
"""

COMP_FD = {
    'Serie A':'SA','Serie B':'SB','Premier League':'PL',
    'EFL Championship':'ELC','Bundesliga':'BL1','2. Bundesliga':'BL2',
    'Ligue 1':'FL1','Ligue 2':'FL2','La Liga':'PD',
    'LaLiga Hypermotion':'SD','Eredivisie':'DED','Pro League':'BSA',
    'Liga Portugal':'PPL','Champions League':'CL','Europa League':'EL',
    'Copa del Rey':'CDR','DFB-Pokal':'DFB','FA Cup':'FAC',
}

COMP_ODDS = {
    'Serie A':'soccer_italy_serie_a','Serie B':'soccer_italy_serie_b',
    'Premier League':'soccer_epl','EFL Championship':'soccer_efl_champ',
    'Bundesliga':'soccer_germany_bundesliga','2. Bundesliga':'soccer_germany_bundesliga2',
    'Ligue 1':'soccer_france_ligue_one','Ligue 2':'soccer_france_ligue_two',
    'La Liga':'soccer_spain_la_liga','LaLiga Hypermotion':'soccer_spain_segunda_division',
    'Eredivisie':'soccer_netherlands_eredivisie','Pro League':'soccer_belgium_first_div',
    'Liga Portugal':'soccer_portugal_primeira_liga',
    'Champions League':'soccer_uefa_champs_league','Europa League':'soccer_uefa_europa_league',
}

BK_PRIORITY = ['sportium','bet365','unibet','bwin','betway','william_hill','marathonbet']

REQ_HEADERS = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept':'application/json, text/html, */*',
    'Accept-Language':'it-IT,it;q=0.9,en;q=0.8',
}

@dataclass
class TeamStats:
    name:str=''; gf_avg:float=0.0; ga_avg:float=0.0
    xg_avg:float=0.0; xga_avg:float=0.0
    form:str=''; matches_n:int=0; source:str=''

@dataclass
class OddsData:
    home:float=0.0; draw:float=0.0; away:float=0.0
    over25:float=0.0; under25:float=0.0
    over35:float=0.0; under35:float=0.0
    btts_y:float=0.0; btts_n:float=0.0; bookmaker:str=''

@dataclass
class Injury:
    name:str=''; pos:str=''; status:str=''; reason:str=''; team:str=''

class FootballDataClient:
    BASE = 'https://api.football-data.org/v4'
    def __init__(self, key):
        self._h = {**REQ_HEADERS, 'X-Auth-Token': key}
    def _get(self, ep, params=None):
        try:
            r = requests.get(f'{self.BASE}{ep}', headers=self._h, params=params, timeout=12)
            if r.status_code == 200: return r.json()
            if r.status_code == 429: return {'_err':'Rate limit -- aspetta 1 minuto'}
            if r.status_code == 403: return {'_err':'API Key football-data non valida'}
            return {'_err': f'HTTP {r.status_code}'}
        except Exception as e: return {'_err': str(e)}
    def find_team(self, name):
        d = self._get('/teams', {'name': name})
        if d and 'teams' in d and d['teams']: return d['teams'][0]
        d2 = self._get('/teams', {'name': name[:6]})
        if d2 and 'teams' in d2:
            nl = name.lower()
            for t in d2['teams']:
                if nl in t.get('name','').lower(): return t
        return None
    def get_matches(self, tid, limit=12):
        d = self._get(f'/teams/{tid}/matches', {'status':'FINISHED','limit':limit})
        return d.get('matches', []) if d and 'matches' in d else []
    def compute_stats(self, matches, team_name):
        gf_l, ga_l, form_l = [], [], []
        tn = team_name.lower()
        for m in matches[-10:]:
            ht = m.get('homeTeam',{}).get('name','').lower()
            at = m.get('awayTeam',{}).get('name','').lower()
            sc = m.get('score',{}).get('fullTime',{})
            hg, ag = sc.get('home'), sc.get('away')
            if hg is None or ag is None: continue
            is_home = (tn in ht or ht in tn)
            gf = hg if is_home else ag
            ga = ag if is_home else hg
            gf_l.append(gf); ga_l.append(ga)
            form_l.append('W' if gf>ga else ('D' if gf==ga else 'L'))
        if not gf_l: return TeamStats(name=team_name, source='football-data.org')
        n = len(gf_l)
        return TeamStats(
            name=team_name,
            gf_avg=round(sum(gf_l)/n,3), ga_avg=round(sum(ga_l)/n,3),
            xg_avg=round(sum(gf_l)/n*0.93,3), xga_avg=round(sum(ga_l)/n*0.93,3),
            form=''.join(form_l[-5:]), matches_n=n, source='football-data.org'
        )
    def get_team_stats(self, name):
        team = self.find_team(name)
        if not team: return None, f"Squadra '{name}' non trovata"
        matches = self.get_matches(team['id'])
        if not matches: return None, f"Nessuna partita trovata per '{name}'"
        return self.compute_stats(matches, name), 'ok'

class OddsAPIClient:
    BASE = 'https://api.the-odds-api.com/v4'
    def __init__(self, key): self._key = key
    def _get(self, ep, params=None):
        try:
            p = {'apiKey': self._key, **(params or {})}
            r = requests.get(f'{self.BASE}{ep}', params=p, headers=REQ_HEADERS, timeout=12)
            if r.status_code == 200: return r.json()
            if r.status_code == 401: return {'_err':'API Key The Odds API non valida'}
            if r.status_code == 422: return {'_err':'Competizione non supportata'}
            if r.status_code == 429: return {'_err':'Quota The Odds API esaurita'}
            return {'_err': f'HTTP {r.status_code}'}
        except Exception as e: return {'_err': str(e)}
    def get_remaining(self):
        try:
            r = requests.get(f'{self.BASE}/sports', params={'apiKey':self._key}, timeout=8)
            return int(r.headers.get('x-requests-remaining',-1))
        except: return -1
    def get_odds(self, sport_key, home, away):
        data = self._get(f'/sports/{sport_key}/odds', {
            'regions':'eu','markets':'h2h,totals,btts',
            'oddsFormat':'decimal','bookmakers':','.join(BK_PRIORITY)
        })
        if not data: return None, 'Nessun dato ricevuto'
        if isinstance(data, dict) and '_err' in data: return None, data['_err']
        if not isinstance(data, list): return None, 'Formato risposta errato'
        hl, al = home.lower(), away.lower()
        event = None
        for ev in data:
            eh = ev.get('home_team','').lower()
            ea = ev.get('away_team','').lower()
            if (hl in eh or eh in hl) and (al in ea or ea in al):
                event = ev; break
        if not event: return None, f"Partita '{home} vs {away}' non trovata"
        return self._extract(event), 'ok'
    def _extract(self, event):
        od = OddsData()
        bks = event.get('bookmakers', [])
        if not bks: return od
        chosen = None
        for prio in BK_PRIORITY:
            for bk in bks:
                if bk.get('key','') == prio: chosen = bk; break
            if chosen: break
        if not chosen: chosen = bks[0]
        od.bookmaker = chosen.get('title', chosen.get('key',''))
        for mkt in chosen.get('markets',[]):
            key = mkt.get('key','')
            outs = {o['name']:o['price'] for o in mkt.get('outcomes',[])}
            if key == 'h2h':
                od.home = outs.get(event.get('home_team',''), 0.0)
                od.away = outs.get(event.get('away_team',''), 0.0)
                od.draw = outs.get('Draw', 0.0)
            elif key == 'totals':
                for o in mkt.get('outcomes',[]):
                    pt = o.get('point',0); nm = o.get('name',''); pr = o.get('price',0)
                    if pt == 2.5:
                        if nm == 'Over': od.over25 = pr
                        else: od.under25 = pr
                    elif pt == 3.5:
                        if nm == 'Over': od.over35 = pr
                        else: od.under35 = pr
            elif key == 'btts':
                od.btts_y = outs.get('Yes', 0.0)
                od.btts_n = outs.get('No', 0.0)
        return od

class TransfermarktScraper:
    BASE = 'https://www.transfermarkt.it'
    def _get(self, url):
        try:
            h = {**REQ_HEADERS, 'Referer': self.BASE}
            r = requests.get(url, headers=h, timeout=12)
            return r.text if r.status_code == 200 else None
        except: return None
    def _search(self, name):
        try:
            r = requests.get(f'{self.BASE}/schnellsuche/ergebnis/schnellsuche',
                             headers={**REQ_HEADERS,'Referer':self.BASE},
                             params={'query':name}, timeout=12)
            if r.status_code != 200: return None
            m = re.search(r'href="(/[^"]+/startseite/verein/\d+[^"]*)"', r.text)
            return self.BASE + m.group(1) if m else None
        except: return None
    def get_injuries(self, team_name):
        url = self._search(team_name)
        if not url: return [], f"'{team_name}' non trovata su Transfermarkt"
        inj_url = re.sub(r'/startseite/', '/verletzungen/', url)
        html = self._get(inj_url)
        if not html: return [], 'Pagina infortuni non raggiungibile'
        injuries = []
        rows = re.findall(
            r'<tr[^>]*class="[^"]*(?:odd|even)[^"]*"[^>]*>(.*?)</tr>',
            html, re.DOTALL
        )
        for row in rows[:25]:
            text = re.sub(r'<[^>]+>',' ', row)
            text = re.sub(r'\s+',' ', text).strip()
            if not text or len(text) < 5: continue
            if any(kw in text.lower() for kw in ['infortu','lesion','sospett','dubbio','out','assent','recuper']):
                parts = text.split()
                if len(parts) >= 2:
                    injuries.append(Injury(
                        name=' '.join(parts[:2]),
                        status='out' if 'out' in text.lower() else 'doubt',
                        reason=text[:100], team=team_name
                    ))
        return injuries, 'ok'

def mc_(label, val, delta='', color='org'):
    d = f'<div class="dlt">{delta}</div>' if delta else ''
    return (f'<div class="mc {color}"><div class="ab"></div>'
            f'<div class="lbl">{label}</div><div class="val">{val}</div>{d}</div>')

def sh_(title):
    return f'<div class="sh"><span style="color:#ff6600">[>]</span><h3>{title}</h3></div>'

def ok_box(msg): return f'<div class="ok-box">[OK] {msg}</div>'
def warn_box(msg): return f'<div class="warn-box">[WARN] {msg}</div>'
def err_box(msg): return f'<div class="err-box">[ERR] {msg}</div>'

def render_stats(stats, label, color):
    st.markdown(sh_(label), unsafe_allow_html=True)
    st.markdown(
        f'<div class="mg mg4">'
        f'{mc_("GF/partita", f"{stats.gf_avg:.2f}", "", color)}'
        f'{mc_("GA/partita", f"{stats.ga_avg:.2f}", "", color)}'
        f'{mc_("xG/partita", f"{stats.xg_avg:.2f}", "", color)}'
        f'{mc_("xGA/partita", f"{stats.xga_avg:.2f}", "", color)}'
        f'</div>'
        f'<div class="mg mg2">'
        f'{mc_("Forma (ultimi 5)", stats.form or "N/D", f"{stats.matches_n} partite", color)}'
        f'{mc_("Fonte", stats.source, "", "yel")}'
        f'</div>',
        unsafe_allow_html=True
    )

def render_odds(od):
    st.markdown(sh_(f'QUOTE -- {od.bookmaker.upper()}'), unsafe_allow_html=True)
    st.markdown(
        f'<div class="mg mg3">'
        f'{mc_("1 CASA", f"{od.home:.2f}" if od.home else "N/D", "", "org")}'
        f'{mc_("X PAREGGIO", f"{od.draw:.2f}" if od.draw else "N/D", "", "yel")}'
        f'{mc_("2 TRASFERTA", f"{od.away:.2f}" if od.away else "N/D", "", "blu")}'
        f'</div>'
        f'<div class="mg mg4">'
        f'{mc_("OVER 2.5", f"{od.over25:.2f}" if od.over25 else "N/D", "", "grn")}'
        f'{mc_("UNDER 2.5", f"{od.under25:.2f}" if od.under25 else "N/D", "", "red")}'
        f'{mc_("OVER 3.5", f"{od.over35:.2f}" if od.over35 else "N/D", "", "grn")}'
        f'{mc_("UNDER 3.5", f"{od.under35:.2f}" if od.under35 else "N/D", "", "red")}'
        f'</div>'
        f'<div class="mg mg2">'
        f'{mc_("BTTS SI", f"{od.btts_y:.2f}" if od.btts_y else "N/D", "", "grn")}'
        f'{mc_("BTTS NO", f"{od.btts_n:.2f}" if od.btts_n else "N/D", "", "red")}'
        f'</div>',
        unsafe_allow_html=True
    )

def render_injuries(injuries, team):
    if not injuries:
        st.markdown(ok_box(f'Nessun infortunio rilevato per {team}'), unsafe_allow_html=True)
        return
    st.markdown(sh_(f'INFORTUNI -- {team.upper()}'), unsafe_allow_html=True)
    for inj in injuries:
        css = inj.status if inj.status in ('out','doubt') else 'doubt'
        badge = 'INDISPONIBILE' if css == 'out' else 'IN DUBBIO'
        st.markdown(
            f'<div class="inj {css}">'
            f'<div class="pname">{inj.name} '
            f'<span style="font-size:.6rem;color:var(--t2)">[{badge}]</span></div>'
            f'<div class="pinfo">{inj.reason[:100]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

def export_to_app(result, home, away):
    rp = st.session_state.get('rp', {})
    po = st.session_state.get('podds', {})
    hs = result.get('home_stats')
    aws = result.get('away_stats')
    od = result.get('odds')
    if hs:
        rp['hn']=home; rp['home_gf']=hs.gf_avg; rp['home_ga']=hs.ga_avg
        rp['home_xg']=hs.xg_avg; rp['home_xga']=hs.xga_avg
    if aws:
        rp['an']=away; rp['away_gf']=aws.gf_avg; rp['away_ga']=aws.ga_avg
        rp['away_xg']=aws.xg_avg; rp['away_xga']=aws.xga_avg
    if od:
        po['home']=od.home; po['draw']=od.draw; po['away']=od.away
        po['over25']=od.over25; po['under25']=od.under25
        po['over35']=od.over35; po['under35']=od.under35
        po['btts_y']=od.btts_y; po['btts_n']=od.btts_n
    st.session_state['rp'] = rp
    st.session_state['podds'] = po

def main():
    st.set_page_config(page_title='QF Scraper', page_icon='S',
                       layout='wide', initial_sidebar_state='expanded')
    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="bh"><h1>QUANTUM FOOTBALL SCRAPER</h1>'
        '<div class="sub">Dati automatici -- football-data.org + The Odds API + Transfermarkt</div></div>',
        unsafe_allow_html=True
    )

    with st.sidebar:
        st.markdown('### API KEYS')
        fd_key = st.text_input('Football-Data.org Key', type='password',
                               placeholder='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
        odds_key = st.text_input('The Odds API Key', type='password',
                                 placeholder='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
        st.divider()
        if odds_key:
            rem = OddsAPIClient(odds_key).get_remaining()
            if rem >= 0:
                color = 'grn' if rem > 100 else ('yel' if rem > 20 else 'red')
                st.markdown(
                    mc_('Richieste rimanenti', str(rem), '', color),
                    unsafe_allow_html=True
                )
        st.divider()
        st.markdown(
            '<div style="font-size:.58rem;color:#8888aa;line-height:1.8">'
            'Fonti:<br>-- football-data.org<br>-- the-odds-api.com<br>-- transfermarkt.it</div>',
            unsafe_allow_html=True
        )

    st.markdown(sh_('INSERISCI PARTITA'), unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2,2,2])
    with c1: home = st.text_input('Squadra Casa', placeholder='es. Lazio')
    with c2: away = st.text_input('Squadra Trasferta', placeholder='es. Atalanta')
    with c3: competition = st.selectbox('Competizione', list(COMP_FD.keys()))

    if not fd_key or not odds_key:
        st.markdown(warn_box('Inserisci entrambe le API Key nella sidebar'), unsafe_allow_html=True)
        return
    if not home or not away:
        st.markdown(warn_box('Inserisci il nome di entrambe le squadre'), unsafe_allow_html=True)
        return

    fetch = st.button('[FETCH] CARICA DATI AUTOMATICAMENTE', use_container_width=True)

    if fetch:
        result = {}
        errors = []; warnings = []; sources = []

        fd = FootballDataClient(fd_key)
        oa = OddsAPIClient(odds_key)
        tm = TransfermarktScraper()

        with st.spinner(f'Statistiche {home}...'):
            hs, msg = fd.get_team_stats(home)
            if hs: result['home_stats'] = hs; sources.append('football-data.org')
            else: warnings.append(f'Stats casa: {msg}')

        with st.spinner(f'Statistiche {away}...'):
            aws, msg = fd.get_team_stats(away)
            if aws: result['away_stats'] = aws
            else: warnings.append(f'Stats trasferta: {msg}')

        sport_key = COMP_ODDS.get(competition)
        if sport_key:
            with st.spinner(f'Quote Sportium {home} vs {away}...'):
                od, msg = oa.get_odds(sport_key, home, away)
                if od: result['odds'] = od; sources.append(f'The Odds API ({od.bookmaker})')
                else: warnings.append(f'Quote: {msg}')
        else:
            warnings.append(f"Competizione '{competition}' non supportata per le quote")

        with st.spinner(f'Infortuni {home}...'):
            inj_h, msg = tm.get_injuries(home)
            result['inj_home'] = inj_h
            if msg != 'ok': warnings.append(f'Infortuni casa: {msg}')

        with st.spinner(f'Infortuni {away}...'):
            inj_a, msg = tm.get_injuries(away)
            result['inj_away'] = inj_a
            if msg != 'ok': warnings.append(f'Infortuni trasferta: {msg}')

        result['errors'] = errors
        result['warnings'] = warnings
        result['sources'] = sources
        st.session_state['scraper_result'] = result
        st.session_state['scraper_home'] = home
        st.session_state['scraper_away'] = away

    result = st.session_state.get('scraper_result')
    if not result:
        return

    home = st.session_state.get('scraper_home', home)
    away = st.session_state.get('scraper_away', away)

    for e in result.get('errors',[]): st.markdown(err_box(e), unsafe_allow_html=True)
    for w in result.get('warnings',[]): st.markdown(warn_box(w), unsafe_allow_html=True)
    if result.get('sources'):
        st.markdown(ok_box('Dati da: ' + ', '.join(result['sources'])), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(['[STATS] STATISTICHE','[ODDS] QUOTE','[INJ] INFORTUNI','[EXPORT] ESPORTA'])

    with t1:
        hs = result.get('home_stats')
        aws = result.get('away_stats')
        if hs: render_stats(hs, f'CASA -- {home.upper()}', 'org')
        else: st.markdown(warn_box(f'Stats non disponibili per {home}'), unsafe_allow_html=True)
        st.divider()
        if aws: render_stats(aws, f'TRASFERTA -- {away.upper()}', 'blu')
        else: st.markdown(warn_box(f'Stats non disponibili per {away}'), unsafe_allow_html=True)

    with t2:
        od = result.get('odds')
        if od: render_odds(od)
        else: st.markdown(warn_box('Quote non disponibili'), unsafe_allow_html=True)

    with t3:
        ch, ca = st.columns(2)
        with ch: render_injuries(result.get('inj_home',[]), home)
        with ca: render_injuries(result.get('inj_away',[]), away)

    with t4:
        st.markdown(sh_('ESPORTA IN APP.PY'), unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:.7rem;color:#8888aa;margin-bottom:12px">'
            'Clicca il bottone per copiare i dati nella sessione di app.py.<br>'
            'Apri app.py nella stessa finestra -- i campi saranno gia\' compilati.</div>',
            unsafe_allow_html=True
        )
        if st.button('[EXPORT] ESPORTA IN APP.PY', use_container_width=True):
            export_to_app(result, home, away)
            st.markdown(ok_box('Esportato! Apri app.py -- i campi sono gia\' compilati.'), unsafe_allow_html=True)

        # Preview
        st.markdown(sh_('ANTEPRIMA DATI'), unsafe_allow_html=True)
        preview = {}
        hs = result.get('home_stats')
        aws = result.get('away_stats')
        od = result.get('odds')
        if hs:
            preview[f'{home} GF/avg']=hs.gf_avg; preview[f'{home} GA/avg']=hs.ga_avg
            preview[f'{home} xG/avg']=hs.xg_avg
        if aws:
            preview[f'{away} GF/avg']=aws.gf_avg; preview[f'{away} GA/avg']=aws.ga_avg
            preview[f'{away} xG/avg']=aws.xg_avg
        if od:
            preview['1 Casa']=od.home; preview['X Pari']=od.draw
            preview['2 Trasferta']=od.away; preview['Over 2.5']=od.over25
        if preview:
            st.dataframe(
                pd.DataFrame(list(preview.items()), columns=['Campo','Valore']),
                use_container_width=True, hide_index=True
            )

if __name__ == '__main__':
    main()
