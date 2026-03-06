# -*- coding: utf-8 -*-
# QUANTUM FOOTBALL ENGINE v6.1 - Modulo Statistico Avanzato
# Caratteristiche:
#   - Poisson con correzione Dixon-Coles (0-0 overcorrection)
#   - Peso decrescente partite recenti (ultime 5 doppio peso)
#   - Stats casa/trasferta separate
#   - xG + tiri + tiri in porta per partita
#   - Aggiustamento motivazione (-20% / +20%)
#   - Stima automatica impatto infortuni
#   - H2H storico 3 anni con decadimento annuale
#   - Confronto modello base vs avanzato

import numpy as np
from scipy.stats import poisson
from scipy.optimize import minimize
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import requests, re
from datetime import datetime, timedelta

REQ_H = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, */*',
}

# ==============================================================================
# DATA CLASSES
# ==============================================================================
@dataclass
class MatchRecord:
    date:     str
    gf:       int
    ga:       int
    xg:       float
    xga:      float
    shots:    int
    shots_ot: int
    is_home:  bool
    weight:   float = 1.0   # peso temporale

@dataclass
class TeamStats:
    name:       str   = ''
    # Medie ponderate
    gf_avg:     float = 1.3
    ga_avg:     float = 1.1
    xg_avg:     float = 1.3
    xga_avg:    float = 1.1
    shots_avg:    float = 12.0
    shots_ot_avg: float = 4.5
    corners_avg:  float = 5.0
    cards_avg:    float = 2.0
    # Casa / Trasferta separati
    gf_home:    float = 0.0
    ga_home:    float = 0.0
    gf_away:    float = 0.0
    ga_away:    float = 0.0
    xg_home:    float = 0.0
    xg_away:    float = 0.0
    xga_home:   float = 0.0
    xga_away:   float = 0.0
    # Forma
    form:       str   = ''
    matches_n:  int   = 0
    source:     str   = ''
    records:    List[MatchRecord] = field(default_factory=list)

@dataclass
class H2HRecord:
    date:     str
    home:     str
    away:     str
    score_h:  int
    score_a:  int
    year_weight: float = 1.0

@dataclass
class InjuryImpact:
    player:   str
    team:     str
    role:     str   = 'unknown'    # striker, midfielder, defender, goalkeeper
    impact:   float = 0.0          # % di riduzione lambda attacco

@dataclass
class EngineResult:
    # Lambda finali
    lam_h:    float
    lam_a:    float
    # Lambda base (senza correzioni)
    lam_h_base: float
    lam_a_base: float
    # Correzioni applicate
    dc_rho:   float   = 0.0        # Dixon-Coles rho
    motiv_h:  float   = 0.0        # aggiustamento motivazione casa
    motiv_a:  float   = 0.0        # aggiustamento motivazione trasferta
    inj_h:    float   = 0.0        # impatto infortuni casa
    inj_a:    float   = 0.0        # impatto infortuni trasferta
    h2h_adj:  float   = 0.0        # aggiustamento H2H
    diff_pct: float   = 0.0        # differenza % base vs avanzato
    notes:    List[str] = field(default_factory=list)


# ==============================================================================
# PESI TEMPORALI
# ==============================================================================
def compute_weights(records: List[MatchRecord]) -> List[MatchRecord]:
    """
    Ultime 5 partite: peso 2.0
    Partite precedenti: peso 1.0
    """
    n = len(records)
    for i, r in enumerate(records):
        # i=0 e' la piu vecchia, i=n-1 la piu recente
        if i >= n - 5:
            r.weight = 2.0
        else:
            r.weight = 1.0
    return records


# ==============================================================================
# STATS PONDERATE
# ==============================================================================
def weighted_stats(records: List[MatchRecord], is_home_filter: Optional[bool] = None) -> Dict:
    filtered = [r for r in records if (is_home_filter is None or r.is_home == is_home_filter)]
    if not filtered:
        return {'gf': 1.2, 'ga': 1.1, 'xg': 1.2, 'xga': 1.1, 'shots': 12.0, 'shots_ot': 4.5, 'n': 0}

    total_w = sum(r.weight for r in filtered)
    gf  = sum(r.gf  * r.weight for r in filtered) / total_w
    ga  = sum(r.ga  * r.weight for r in filtered) / total_w
    xg  = sum(r.xg  * r.weight for r in filtered) / total_w
    xga = sum(r.xga * r.weight for r in filtered) / total_w
    shots    = sum(r.shots    * r.weight for r in filtered) / total_w
    shots_ot = sum(r.shots_ot * r.weight for r in filtered) / total_w

    return {'gf': gf, 'ga': ga, 'xg': xg, 'xga': xga,
            'shots': shots, 'shots_ot': shots_ot, 'n': len(filtered)}


# ==============================================================================
# DIXON-COLES CORRECTION
# ==============================================================================
def dc_tau(x: int, y: int, lam_h: float, lam_a: float, rho: float) -> float:
    """
    Fattore di correzione Dixon-Coles per basso punteggio.
    Corregge la sovra/sottostima di 0-0, 1-0, 0-1, 1-1.
    """
    if x == 0 and y == 0:
        return 1 - lam_h * lam_a * rho
    elif x == 0 and y == 1:
        return 1 + lam_h * rho
    elif x == 1 and y == 0:
        return 1 + lam_a * rho
    elif x == 1 and y == 1:
        return 1 - rho
    else:
        return 1.0

def dc_matrix(lam_h: float, lam_a: float, rho: float = -0.13, N: int = 11) -> np.ndarray:
    """
    Matrice di probabilita con correzione Dixon-Coles.
    rho tipicamente negativo (-0.1 / -0.2): riduce prob di 0-0 e aumenta 1-1.
    """
    m = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            base = poisson.pmf(i, lam_h) * poisson.pmf(j, lam_a)
            m[i, j] = base * dc_tau(i, j, lam_h, lam_a, rho)
    # Normalizza
    total = m.sum()
    if total > 0:
        m /= total
    return m

def estimate_rho(records_h: List[MatchRecord], records_a: List[MatchRecord]) -> float:
    """
    Stima rho empiricamente dai risultati storici.
    Se pochi dati, usa valore di default -0.13.
    """
    all_rec = records_h + records_a
    if len(all_rec) < 10:
        return -0.13

    counts = {(0,0):0, (0,1):0, (1,0):0, (1,1):0}
    total = 0
    for r in all_rec:
        key = (min(r.gf,1), min(r.ga,1))
        if key in counts:
            counts[key] += 1
        total += 1

    if total == 0:
        return -0.13

    # Proporzione 0-0 osservata vs attesa
    obs_00 = counts[(0,0)] / total
    exp_00 = 0.08  # atteso medio campionati europei
    rho = (obs_00 - exp_00) / max(exp_00, 0.01) * (-0.2)
    return max(-0.25, min(0.0, rho))


# ==============================================================================
# STIMA IMPATTO INFORTUNI
# ==============================================================================
# Ruoli stimati da cognomi noti — espandibile
KNOWN_STRIKERS = {
    'immobile','osimhen','lukaku','vlahovic','zapata','lautaro','thuram',
    'giroud','morata','benzema','mbappe','lewandowski','kane','haaland',
    'firmino','salah','nunez','gabriel jesus','marcus thuram','retegui',
    'castellanos','dia','pinamontes','lapadula','pavoletti','caputo',
}
KNOWN_MIDFIELDERS = {
    'verratti','tonali','jorginho','barella','frattesi','pellegrini',
    'zielinski','calhanoglu','milinkovic','rabiot','cambiaso','chiesa',
    'leao','kvara','kvaratskhelia','politano','orsolini','sottil',
}
KNOWN_DEFENDERS = {
    'bonucci','chiellini','bastoni','skriniar','acerbi','smalling',
    'mancini','koulibaly','bremer','danilo','alex sandro','theo',
    'dimarco','spinazzola','florenzi','darmian','dumfries',
}
KNOWN_GK = {
    'donnarumma','szczesny','maignan','meret','sportiello','provedel',
    'vicario','terracciano','carnesecchi','rui patricio',
}

IMPACT_MAP = {
    'striker':    0.18,   # capocannoniere out = -18% lambda attacco
    'midfielder': 0.09,
    'defender':   0.05,   # impatto su ga (difesa)
    'goalkeeper': 0.06,
    'unknown':    0.07,
}

def estimate_injury_impact(injuries: List[Dict], team_name: str) -> InjuryImpact:
    """
    Stima impatto totale degli infortuni sulla squadra.
    Ritorna l'impatto percentuale sul lambda di attacco.
    """
    total_impact = 0.0
    for inj in injuries:
        name = inj.get('name', '').lower()
        status = inj.get('status', 'doubt')
        multiplier = 1.0 if status == 'out' else 0.5

        role = 'unknown'
        if any(s in name for s in KNOWN_STRIKERS):
            role = 'striker'
        elif any(s in name for s in KNOWN_MIDFIELDERS):
            role = 'midfielder'
        elif any(s in name for s in KNOWN_DEFENDERS):
            role = 'defender'
        elif any(s in name for s in KNOWN_GK):
            role = 'goalkeeper'

        impact = IMPACT_MAP[role] * multiplier
        total_impact += impact

    # Cap a 35% (non si puo perdere troppo da soli)
    return min(total_impact, 0.35)


# ==============================================================================
# H2H FETCH DA FOOTBALL-DATA.ORG
# ==============================================================================
def fetch_h2h(fd_key: str, home: str, away: str,
               years: int = 3) -> Tuple[List[H2HRecord], str]:
    """
    Recupera storico H2H da football-data.org.
    Applica decadimento annuale: anno corrente 1.0, -1 anno 0.7, -2 anni 0.4.
    """
    if not fd_key:
        return [], 'Nessuna FD key'

    year_weights = {0: 1.0, 1: 0.7, 2: 0.4}
    records = []
    now = datetime.now()

    try:
        h_headers = {**REQ_H, 'X-Auth-Token': fd_key}

        # Cerca team ID per entrambe le squadre
        def get_team_id(name):
            r = requests.get('https://api.football-data.org/v4/teams',
                             headers=h_headers, params={'name': name}, timeout=10)
            if r.status_code == 200:
                teams = r.json().get('teams', [])
                if teams:
                    return teams[0]['id']
                # Fallback partial
                r2 = requests.get('https://api.football-data.org/v4/teams',
                                  headers=h_headers, params={'name': name[:5]}, timeout=10)
                if r2.status_code == 200:
                    nl = name.lower()
                    for t in r2.json().get('teams', []):
                        if nl in t.get('name', '').lower():
                            return t['id']
            return None

        h_id = get_team_id(home)
        a_id = get_team_id(away)
        if not h_id or not a_id:
            return [], f'Team ID non trovato per {home} o {away}'

        # Partite squadra casa degli ultimi 3 anni
        date_from = (now - timedelta(days=365*years)).strftime('%Y-%m-%d')
        r = requests.get(
            f'https://api.football-data.org/v4/teams/{h_id}/matches',
            headers=h_headers,
            params={'status': 'FINISHED', 'limit': 60},
            timeout=12
        )
        if r.status_code != 200:
            return [], f'H2H HTTP {r.status_code}'

        hl = home.lower()
        al = away.lower()

        for m in r.json().get('matches', []):
            ht = m.get('homeTeam', {}).get('name', '').lower()
            at = m.get('awayTeam', {}).get('name', '').lower()

            is_h2h = ((hl in ht or ht in hl) and (al in at or at in al)) or \
                     ((al in ht or ht in al) and (hl in at or at in hl))

            if not is_h2h:
                continue

            sc = m.get('score', {}).get('fullTime', {})
            hg, ag = sc.get('home'), sc.get('away')
            if hg is None or ag is None:
                continue

            date_str = m.get('utcDate', '')[:10]
            try:
                match_date = datetime.strptime(date_str, '%Y-%m-%d')
                years_ago = (now - match_date).days // 365
                yw = year_weights.get(min(years_ago, 2), 0.3)
            except:
                yw = 0.5

            records.append(H2HRecord(
                date=date_str,
                home=m.get('homeTeam', {}).get('name', ''),
                away=m.get('awayTeam', {}).get('name', ''),
                score_h=int(hg), score_a=int(ag),
                year_weight=yw
            ))

        records.sort(key=lambda x: x.date, reverse=True)
        return records[:15], 'ok'

    except Exception as e:
        return [], str(e)


def h2h_lambda_adjustment(records: List[H2HRecord], home: str) -> float:
    """
    Calcola aggiustamento lambda basato su H2H.
    Se casa vince molto => +5% lambda h, se perde => -5%.
    """
    if not records:
        return 0.0

    hl = home.lower()
    w, d, l = 0, 0, 0
    total_w = 0.0

    for rec in records:
        ht = rec.home.lower()
        is_home = hl in ht or ht in hl
        gf = rec.score_h if is_home else rec.score_a
        ga = rec.score_a if is_home else rec.score_h
        w_factor = rec.year_weight

        if gf > ga:   w += w_factor
        elif gf == ga: d += w_factor
        else:          l += w_factor
        total_w += w_factor

    if total_w == 0:
        return 0.0

    win_rate = w / total_w
    adj = (win_rate - 0.5) * 0.10   # max +/-5%
    return round(max(-0.08, min(0.08, adj)), 4)


# ==============================================================================
# FETCH DATI AVANZATI DA FOOTBALL-DATA.ORG
# ==============================================================================
def fetch_advanced_stats(fd_key: str, team_name: str,
                          is_home_context: bool = True) -> Tuple[Optional[TeamStats], str]:
    """
    Recupera stats avanzate:
    - xG per partita (se disponibile, altrimenti stima da gol)
    - Tiri e tiri in porta
    - Stats separate casa/trasferta
    - Pesi decrescenti (ultime 5 doppio)
    """
    if not fd_key:
        return None, 'Nessuna FD key'

    try:
        h = {**REQ_H, 'X-Auth-Token': fd_key}

        # Trova squadra
        r = requests.get('https://api.football-data.org/v4/teams',
                         headers=h, params={'name': team_name}, timeout=10)
        teams = []
        if r.status_code == 200:
            teams = r.json().get('teams', [])
        if not teams:
            r2 = requests.get('https://api.football-data.org/v4/teams',
                              headers=h, params={'name': team_name[:5]}, timeout=10)
            if r2.status_code == 200:
                tl = team_name.lower()
                teams = [t for t in r2.json().get('teams', [])
                         if tl in t.get('name', '').lower()]
        if not teams:
            return None, f"Squadra '{team_name}' non trovata"

        tid = teams[0]['id']

        # Partite (ultime 20 per avere abbastanza dati)
        r2 = requests.get(
            f'https://api.football-data.org/v4/teams/{tid}/matches',
            headers=h, params={'status': 'FINISHED', 'limit': 20}, timeout=12
        )
        if r2.status_code != 200:
            return None, f'Matches HTTP {r2.status_code}'

        matches = r2.json().get('matches', [])
        if not matches:
            return None, 'Nessuna partita trovata'

        records = []
        form_list = []
        tn = team_name.lower()

        for m in matches:
            ht = m.get('homeTeam', {}).get('name', '').lower()
            at = m.get('awayTeam', {}).get('name', '').lower()
            sc = m.get('score', {}).get('fullTime', {})
            hg, ag = sc.get('home'), sc.get('away')
            if hg is None or ag is None:
                continue

            is_home = tn in ht or ht in tn
            gf = int(hg) if is_home else int(ag)
            ga = int(ag) if is_home else int(hg)
            date_str = m.get('utcDate', '')[:10]

            # xG: football-data free tier non fornisce xG
            # Stima da gol con regressione verso media
            # xG ~ 0.85*gol + 0.15*media_lega (1.3)
            xg_est  = round(gf  * 0.85 + 1.3 * 0.15, 2)
            xga_est = round(ga  * 0.85 + 1.3 * 0.15, 2)

            # Tiri stimati da xG (media: ~10 tiri per 1.3 xG)
            shots_est    = max(3, round(xg_est / 0.13))
            shots_ot_est = max(1, round(xg_est / 0.33))

            rec = MatchRecord(
                date=date_str, gf=gf, ga=ga,
                xg=xg_est, xga=xga_est,
                shots=shots_est, shots_ot=shots_ot_est,
                is_home=is_home, weight=1.0
            )
            records.append(rec)
            form_list.append('W' if gf > ga else ('D' if gf == ga else 'L'))

        if not records:
            return None, 'Nessun record valido'

        # Ordina per data (piu vecchio prima) e applica pesi
        records.sort(key=lambda x: x.date)
        records = compute_weights(records)

        # Stats globali ponderate
        s_all  = weighted_stats(records)
        s_home = weighted_stats(records, is_home_filter=True)
        s_away = weighted_stats(records, is_home_filter=False)

        stats = TeamStats(
            name=team_name,
            gf_avg=round(s_all['gf'], 3),
            ga_avg=round(s_all['ga'], 3),
            xg_avg=round(s_all['xg'], 3),
            xga_avg=round(s_all['xga'], 3),
            shots_avg=round(s_all['shots'], 1),
            shots_ot_avg=round(s_all['shots_ot'], 1),
            gf_home=round(s_home['gf'], 3) if s_home['n'] > 0 else s_all['gf'],
            ga_home=round(s_home['ga'], 3) if s_home['n'] > 0 else s_all['ga'],
            gf_away=round(s_away['gf'], 3) if s_away['n'] > 0 else s_all['gf'],
            ga_away=round(s_away['ga'], 3) if s_away['n'] > 0 else s_all['ga'],
            xg_home=round(s_home['xg'], 3) if s_home['n'] > 0 else s_all['xg'],
            xg_away=round(s_away['xg'], 3) if s_away['n'] > 0 else s_all['xg'],
            xga_home=round(s_home['xga'], 3) if s_home['n'] > 0 else s_all['xga'],
            xga_away=round(s_away['xga'], 3) if s_away['n'] > 0 else s_all['xga'],

            form=''.join(form_list[-5:]),
            matches_n=len(records),
            source='football-data.org (avanzato)',
            records=records,
        )
        return stats, 'ok'

    except Exception as e:
        return None, str(e)


# ==============================================================================
# ADVANCED ENGINE
# ==============================================================================
class AdvancedEngine:
    N = 11

    def __init__(self,
                 h_stats: TeamStats,
                 a_stats: TeamStats,
                 motiv_h: float = 0.0,
                 motiv_a: float = 0.0,
                 inj_h: List[Dict] = None,
                 inj_a: List[Dict] = None,
                 h2h_records: List[H2HRecord] = None,
                 use_home_away_split: bool = True,
                 days_rest_h: int = 7,
                 days_rest_a: int = 7,
                 pressure_h: float = 0.0,
                 pressure_a: float = 0.0,
                 league_name: str = 'default',
                 referee_cards_mult: float = 1.0):

        self.h = h_stats
        self.a = a_stats
        self.h2h = h2h_records or []

        # === LAMBDA BASE (modello semplice) ===
        lh_base = max(0.1, h_stats.gf_avg * 0.55 + h_stats.xg_avg * 0.35 +
                      a_stats.ga_avg * 0.05 + a_stats.xga_avg * 0.05)
        la_base = max(0.1, a_stats.gf_avg * 0.50 + a_stats.xg_avg * 0.35 +
                      h_stats.ga_avg * 0.08 + h_stats.xga_avg * 0.07)

        # === LAMBDA AVANZATO ===
        # 1. Usa stats casa/trasferta separate
        if use_home_away_split and h_stats.gf_home > 0 and a_stats.gf_away > 0:
            lh_adv = max(0.1,
                h_stats.gf_home  * 0.40 + h_stats.xg_home  * 0.30 +
                a_stats.ga_away  * 0.15 + a_stats.xga_away * 0.10 +
                h_stats.gf_avg   * 0.05
            )
            la_adv = max(0.1,
                a_stats.gf_away  * 0.40 + a_stats.xg_away  * 0.30 +
                h_stats.ga_home  * 0.15 + h_stats.xga_home * 0.10 +
                a_stats.gf_avg   * 0.05
            )
        else:
            lh_adv = lh_base
            la_adv = la_base

        notes = []

        # 2. Aggiustamento motivazione
        lh_adv *= (1 + motiv_h / 100)
        la_adv *= (1 + motiv_a / 100)
        if motiv_h != 0:
            notes.append(f'Motivazione casa: {motiv_h:+.0f}% → λ={lh_adv:.2f}')
        if motiv_a != 0:
            notes.append(f'Motivazione trasferta: {motiv_a:+.0f}% → λ={la_adv:.2f}')

        # 3. Aggiustamento infortuni
        inj_impact_h = estimate_injury_impact(inj_h or [], h_stats.name)
        inj_impact_a = estimate_injury_impact(inj_a or [], a_stats.name)
        lh_adv *= (1 - inj_impact_h)
        la_adv *= (1 - inj_impact_a)
        if inj_impact_h > 0:
            notes.append(f'Infortuni casa: -{inj_impact_h*100:.1f}% attacco → λ={lh_adv:.2f}')
        if inj_impact_a > 0:
            notes.append(f'Infortuni trasf: -{inj_impact_a*100:.1f}% attacco → λ={la_adv:.2f}')

        # 4. Aggiustamento H2H
        h2h_adj = h2h_lambda_adjustment(self.h2h, h_stats.name)
        lh_adv *= (1 + h2h_adj)
        la_adv *= (1 - h2h_adj)
        if abs(h2h_adj) > 0.01:
            notes.append(f'H2H storico: casa {h2h_adj*100:+.1f}% → λh={lh_adv:.2f}, λa={la_adv:.2f}')

        # 5. Regressione verso la media di lega
        league_avg = LEAGUE_AVGS.get(league_name, LEAGUE_AVGS['default'])
        lh_adv = regression_to_mean(lh_adv, league_avg, h_stats.matches_n or 0)
        la_adv = regression_to_mean(la_adv, league_avg, a_stats.matches_n or 0)
        notes.append(f'Regressione media lega ({league_name}): avg={league_avg:.2f} → λh={lh_adv:.2f}, λa={la_adv:.2f}')

        # 6. Stanchezza
        fat_h = fatigue_factor(days_rest_h)
        fat_a = fatigue_factor(days_rest_a)
        lh_adv *= fat_h
        la_adv *= fat_a
        if fat_h < 1.0: notes.append(f'Stanchezza casa: {days_rest_h}g → -{(1-fat_h)*100:.0f}% λ')
        if fat_a < 1.0: notes.append(f'Stanchezza trasf: {days_rest_a}g → -{(1-fat_a)*100:.0f}% λ')

        # 7. Pressione psicologica
        lh_adv *= pressure_factor(pressure_h)
        la_adv *= pressure_factor(pressure_a)
        if pressure_h != 0: notes.append(f'Pressione casa: {pressure_h:+.0f}% → λ={lh_adv:.2f}')
        if pressure_a != 0: notes.append(f'Pressione trasf: {pressure_a:+.0f}% → λ={la_adv:.2f}')

        # 8. Fattore arbitro (moltiplicatore cartellini — non tocca lambda gol)
        self.referee_cards_mult = referee_cards_mult
        if referee_cards_mult != 1.0:
            notes.append(f'Arbitro: cartellini x{referee_cards_mult:.1f}')

        # 9. Dixon-Coles rho stimato
        all_records = (h_stats.records or []) + (a_stats.records or [])
        self.rho = estimate_rho(h_stats.records or [], a_stats.records or [])
        notes.append(f'Dixon-Coles rho: {self.rho:.3f}')

        self.lh = round(max(0.2, lh_adv), 3)
        self.la = round(max(0.2, la_adv), 3)
        self.lh_base = round(lh_base, 3)
        self.la_base = round(la_base, 3)

        diff_h = abs(self.lh - self.lh_base) / max(self.lh_base, 0.1) * 100
        diff_a = abs(self.la - self.la_base) / max(self.la_base, 0.1) * 100
        diff_pct = (diff_h + diff_a) / 2

        self.result = EngineResult(
            lam_h=self.lh, lam_a=self.la,
            lam_h_base=self.lh_base, lam_a_base=self.la_base,
            dc_rho=self.rho,
            motiv_h=motiv_h, motiv_a=motiv_a,
            inj_h=inj_impact_h, inj_a=inj_impact_a,
            h2h_adj=h2h_adj, diff_pct=round(diff_pct, 2),
            notes=notes,
        )
        self._mat = None

    def mat(self):
        if self._mat is None:
            self._mat = dc_matrix(self.lh, self.la, self.rho, self.N)
        return self._mat

    def mat_base(self):
        """Matrice base senza correzioni."""
        m = np.array([[poisson.pmf(i, self.lh_base) * poisson.pmf(j, self.la_base)
                       for j in range(self.N)] for i in range(self.N)])
        return m / m.sum()

    def p1x2(self):
        m = self.mat()
        return (float(np.tril(m,-1).sum()),
                float(np.diag(m).sum()),
                float(np.triu(m,1).sum()))

    def p1x2_base(self):
        m = self.mat_base()
        return (float(np.tril(m,-1).sum()),
                float(np.diag(m).sum()),
                float(np.triu(m,1).sum()))

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
                         if lo <= i+j <= hi))

    def pdoppia(self):
        ph,pd,pa = self.p1x2()
        return ph+pd, ph+pa, pd+pa

    def pdnb(self):
        ph,pd,pa = self.p1x2()
        tot = ph+pa
        return (ph/tot if tot>0 else 0), (pa/tot if tot>0 else 0)

    def pht(self):
        lh2,la2 = self.lh/2, self.la/2
        N2=7
        m2 = np.array([[poisson.pmf(i,lh2)*poisson.pmf(j,la2)
                         for j in range(N2)] for i in range(N2)])
        m2 /= m2.sum()
        return (float(np.tril(m2,-1).sum()),
                float(np.diag(m2).sum()),
                float(np.triu(m2,1).sum()))

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
        return self.pbtts_ht()

    def p_team_goals(self, n, is_home):
        lam = self.lh if is_home else self.la
        return float(poisson.pmf(n, lam))

    def p_team_goals_range(self, lo, hi, is_home):
        lam = self.lh if is_home else self.la
        return float(sum(poisson.pmf(k,lam) for k in range(lo, min(hi+1,self.N))))

    def p_team_scores_both_halves(self, is_home):
        lam = self.lh if is_home else self.la
        lh2 = lam/2
        return float((1-poisson.pmf(0,lh2))**2)

    def p_exact_gol(self, n):
        m = self.mat()
        return float(sum(m[i,j] for i in range(self.N) for j in range(self.N) if i+j==n))

    def phandicap_eu(self, handicap, is_home):
        m = self.mat()
        p = 0.0
        for i in range(self.N):
            for j in range(self.N):
                diff = (i-j) if is_home else (j-i)
                if diff + handicap > 0: p += m[i,j]
        return float(p)

    def p_winning_margin(self, margin, is_home):
        m = self.mat()
        p = 0.0
        for i in range(self.N):
            for j in range(self.N):
                diff = (i-j) if is_home else (j-i)
                if diff == margin: p += m[i,j]
        return float(p)

    def p_corners(self, h_avg, a_avg, line=9.5):
        lam = h_avg + a_avg
        ov = 1-sum(poisson.pmf(k,lam) for k in range(int(line)+1))
        return float(ov), float(1-ov)

    def p_cards(self, h_avg, a_avg, line=3.5):
        mult = getattr(self, 'referee_cards_mult', 1.0)
        lam = (h_avg + a_avg) * mult
        ov = 1-sum(poisson.pmf(k,lam) for k in range(int(line)+1))
        return float(ov), float(1-ov)

    def top_scores(self, n=6):
        m = self.mat()
        sc = [{'score':f'{i}-{j}','prob':float(m[i,j]),
               'prob_pct':round(float(m[i,j])*100,2),
               'fair':round(1/max(float(m[i,j]),1e-5),1),
               'cat':'Casa' if i>j else ('Pari' if i==j else 'Trasf')}
              for i in range(self.N) for j in range(self.N) if float(m[i,j])>5e-5]
        sc.sort(key=lambda x:-x['prob'])
        return sc[:n]

    def htft_probs(self):
        ph_ht,pd_ht,pa_ht = self.pht()
        ph,pd,pa = self.p1x2()
        return {
            'C/C':ph_ht*ph,'C/X':ph_ht*pd,'C/T':ph_ht*pa,
            'X/C':pd_ht*ph,'X/X':pd_ht*pd,'X/T':pd_ht*pa,
            'T/C':pa_ht*ph,'T/X':pa_ht*pd,'T/T':pa_ht*pa,
        }

    def comparison_report(self) -> Dict:
        """
        Confronto modello base vs avanzato.
        Mostra solo se differenza > 5%.
        """
        ph_b,pd_b,pa_b = self.p1x2_base()
        ph_a,pd_a,pa_a = self.p1x2()
        ov25_b,_ = (float(sum(
            poisson.pmf(i,self.lh_base)*poisson.pmf(j,self.la_base)
            for i in range(self.N) for j in range(self.N) if i+j>2.5
        )), 0)
        ov25_a,_ = self.pou(2.5)

        significant = self.result.diff_pct >= 5.0

        return {
            'significant': significant,
            'diff_pct':    self.result.diff_pct,
            'base': {
                'lh': self.lh_base, 'la': self.la_base,
                'ph': round(ph_b*100,1), 'pd': round(pd_b*100,1), 'pa': round(pa_b*100,1),
                'ov25': round(ov25_b*100,1),
            },
            'advanced': {
                'lh': self.lh, 'la': self.la,
                'ph': round(ph_a*100,1), 'pd': round(pd_a*100,1), 'pa': round(pa_a*100,1),
                'ov25': round(ov25_a*100,1),
            },
            'notes': self.result.notes,
            'rho':   self.rho,
        }


# ==============================================================================
# H2H SUMMARY
# ==============================================================================
def h2h_summary(records: List[H2HRecord], home: str) -> Dict:
    if not records:
        return {}
    hl = home.lower()
    w,d,l = 0,0,0
    gf_tot,ga_tot = 0,0
    for rec in records:
        ht = rec.home.lower()
        is_h = hl in ht or ht in hl
        gf = rec.score_h if is_h else rec.score_a
        ga = rec.score_a if is_h else rec.score_h
        gf_tot += gf; ga_tot += ga
        if gf > ga: w+=1
        elif gf == ga: d+=1
        else: l+=1
    n = len(records)
    return {
        'n': n, 'w': w, 'd': d, 'l': l,
        'gf_avg': round(gf_tot/n,2) if n else 0,
        'ga_avg': round(ga_tot/n,2) if n else 0,
    }


# ==============================================================================
# v6.2 — Regressione media, Forza lega, Stanchezza, Monte Carlo, Controlli incrociati
# ==============================================================================

LEAGUE_AVGS = {
    'Serie A':1.28,'Serie B':1.22,'Premier League':1.38,'EFL Championship':1.25,
    'Bundesliga':1.45,'2. Bundesliga':1.30,'Ligue 1':1.20,'Ligue 2':1.18,
    'La Liga':1.22,'LaLiga Hypermotion':1.15,'Eredivisie':1.55,'Pro League':1.35,
    'Liga Portugal':1.25,'Champions League':1.42,'Europa League':1.30,
    'Conference League':1.20,'default':1.28,
}

# Arbitri noti per stile (espandibile)
REFEREE_PROFILES = {
    # 'cognome_arbitro': {'cards': 1.2, 'pens': 1.1}  # moltiplicatori
}

def regression_to_mean(lam: float, league_avg: float, n_matches: int,
                        weight: float = 0.25) -> float:
    """
    Regressione verso la media di lega.
    Squadre con pochi dati o in forma estrema vengono riportate parzialmente
    verso la media. Meno partite = più regressione.
    """
    if n_matches <= 0:
        return league_avg
    # Peso regressione: diminuisce con più dati (10+ partite = quasi nessuna regressione)
    reg_weight = max(0.0, weight * (1 - n_matches / 15))
    return lam * (1 - reg_weight) + league_avg * reg_weight


def fatigue_factor(days_since_last: int) -> float:
    """
    Riduzione lambda per stanchezza.
    < 3 giorni: -8%, 3-5 giorni: -4%, 5+ giorni: nessuna riduzione
    """
    if days_since_last < 3:
        return 0.92
    elif days_since_last < 5:
        return 0.96
    return 1.0


def pressure_factor(pressure_pct: float) -> float:
    """
    Pressione psicologica (partite decisive).
    pressure_pct: -20 a +20 (da slider utente)
    """
    return 1.0 + pressure_pct / 100.0


# ==============================================================================
# MONTE CARLO
# ==============================================================================
def monte_carlo(lam_h: float, lam_a: float, rho: float,
                n_sim: int = 50000, seed: int = 42) -> Dict:
    """
    Simula n_sim partite e calcola intervalli di confidenza (90% CI).
    Usa distribuzione di Poisson bivariata con correzione Dixon-Coles.
    """
    rng = np.random.default_rng(seed)
    N = 10

    # Costruisce CDF della matrice DC per il campionamento
    mat = dc_matrix(lam_h, lam_a, rho, N)
    flat = mat.flatten()
    flat = flat / flat.sum()
    indices = rng.choice(len(flat), size=n_sim, p=flat)
    goals_h = indices // N
    goals_a = indices % N

    total = goals_h + goals_a

    results = {
        'home_win': float((goals_h > goals_a).mean()),
        'draw':     float((goals_h == goals_a).mean()),
        'away_win': float((goals_a > goals_h).mean()),
        'over15':   float((total > 1.5).mean()),
        'over25':   float((total > 2.5).mean()),
        'over35':   float((total > 3.5).mean()),
        'btts':     float(((goals_h > 0) & (goals_a > 0)).mean()),
        'avg_goals_h': float(goals_h.mean()),
        'avg_goals_a': float(goals_a.mean()),
        'avg_total':   float(total.mean()),
    }

    # Intervallo di confidenza 90% con bootstrap (rapido)
    ci = {}
    block = n_sim // 20   # 20 blocchi da 2500
    for key in ['home_win','draw','away_win','over25','btts']:
        samples = []
        for i in range(20):
            sl = slice(i*block, (i+1)*block)
            gh, ga = goals_h[sl], goals_a[sl]
            tot = gh + ga
            if key == 'home_win':   v = float((gh > ga).mean())
            elif key == 'draw':     v = float((gh == ga).mean())
            elif key == 'away_win': v = float((ga > gh).mean())
            elif key == 'over25':   v = float((tot > 2.5).mean())
            elif key == 'btts':     v = float(((gh > 0) & (ga > 0)).mean())
            samples.append(v)
        samples = sorted(samples)
        ci[key] = (round(samples[1], 4), round(samples[-2], 4))  # 90% CI

    results['ci'] = ci
    results['n_sim'] = n_sim
    return results


# ==============================================================================
# CONTROLLI INCROCIATI
# ==============================================================================
def check_internal_consistency(markets: list, lam_h: float, lam_a: float) -> List[Dict]:
    """
    Verifica coerenza interna tra mercati.
    Ritorna lista di warnings con spiegazione.
    """
    warnings_out = []
    mkt_map = {m.key: m for m in markets if hasattr(m, 'key')}

    def prob(key): return mkt_map[key].prob if key in mkt_map else None

    # 1. BTTS Si vs Under 1.5 — incompatibili
    p_btts = prob('btts_y')
    p_un15 = prob('under15')
    if p_btts and p_un15 and p_btts > 0.5 and p_un15 > 0.25:
        warnings_out.append({
            'level': 'warn',
            'msg': f'⚠️ BTTS Si ({p_btts*100:.0f}%) + Under 1.5 ({p_un15*100:.0f}%) sono quasi incompatibili. Se entrambe segnano ci sono almeno 2 gol.',
            'markets': ['BTTS Si', 'Under 1.5']
        })

    # 2. Over 3.5 alto ma BTTS No alto
    p_ov35 = prob('over35')
    p_bttsn = prob('btts_n')
    if p_ov35 and p_bttsn and p_ov35 > 0.4 and p_bttsn > 0.35:
        warnings_out.append({
            'level': 'warn',
            'msg': f'⚠️ Over 3.5 ({p_ov35*100:.0f}%) + BTTS No ({p_bttsn*100:.0f}%) si contraddicono parzialmente.',
            'markets': ['Over 3.5', 'BTTS No']
        })

    # 3. Casa vince prob bassa ma Doppia Chance 1X alta
    p_home = prob('home')
    p_1x = prob('dc_1x')
    if p_home and p_1x and p_home < 0.25 and p_1x > 0.65:
        warnings_out.append({
            'level': 'info',
            'msg': f'ℹ️ Casa ha poca probabilità di vittoria ({p_home*100:.0f}%) ma 1X è alta ({p_1x*100:.0f}%). Pareggio molto probabile.',
            'markets': ['1 Casa', '1X']
        })

    # 4. Lambda molto sbilanciato — Under potenzialmente trappola
    if lam_h > 2.0 and lam_a > 1.8:
        p_un25 = prob('under25')
        if p_un25 and p_un25 < 0.25:
            warnings_out.append({
                'level': 'warn',
                'msg': f'⚠️ Entrambe le squadre attaccano molto (λ {lam_h:.1f} vs {lam_a:.1f}). Under 2.5 è rischioso.',
                'markets': ['Under 2.5']
            })

    # 5. Squadra nettamente favorita ma DNB non conveniente
    p_away = prob('away')
    if p_home and p_away and max(p_home, p_away) > 0.65:
        winner = 'home' if p_home > p_away else 'away'
        dnb_key = 'dnb_home' if winner == 'home' else 'dnb_away'
        p_dnb = prob(dnb_key)
        if p_dnb and p_dnb < 0.70:
            warnings_out.append({
                'level': 'info',
                'msg': f'ℹ️ Squadra nettamente favorita ma DNB bassa ({p_dnb*100:.0f}%). Considera la doppia chance invece del 1X2 secco.',
                'markets': ['DNB']
            })

    return warnings_out


def detect_traps(markets: list, lam_h: float, lam_a: float) -> List[Dict]:
    """
    Segnala trappole classiche dei bookmaker.
    """
    traps = []
    mkt_map = {m.key: m for m in markets if hasattr(m, 'key')}
    def mkt(key): return mkt_map.get(key)

    # Trappola 1: risultato esatto — quota attraente ma rarissimo
    for key in [k for k in mkt_map if k.startswith('exact') and k != 'exact0']:
        m = mkt(key)
        if m and m.bk > 0 and m.bk < 8.0 and m.prob < 0.08:
            traps.append({
                'level': 'danger',
                'msg': f'🚨 TRAPPOLA: {m.name} ha quota {m.bk:.2f} ma prob solo {m.prob*100:.1f}%. I bookmaker tengono margini altissimi sui risultati esatti.',
                'market': m.name
            })

    # Trappola 2: BTTS su squadre difensive
    m_btts = mkt('btts_y')
    if m_btts and lam_h < 0.9 and lam_a < 0.9:
        traps.append({
            'level': 'danger',
            'msg': f'🚨 TRAPPOLA: BTTS Si su due squadre molto difensive (λ {lam_h:.1f} vs {lam_a:.1f}). Prob reale più bassa di quanto sembri.',
            'market': 'BTTS Si'
        })

    # Trappola 3: Over 4.5 con lambda bassi
    m_ov45 = mkt('over45')
    if m_ov45 and m_ov45.bk > 0 and lam_h + lam_a < 2.5 and m_ov45.prob < 0.10:
        traps.append({
            'level': 'danger',
            'msg': f'🚨 TRAPPOLA: Over 4.5 con lambda totale {lam_h+lam_a:.1f}. Estremamente improbabile.',
            'market': 'Over 4.5'
        })

    # Trappola 4: quota 1X2 troppo bassa (< 1.25) — margine bookmaker altissimo
    for key in ['home','draw','away']:
        m = mkt(key)
        if m and 1.01 < m.bk < 1.25:
            traps.append({
                'level': 'warn',
                'msg': f'⚠️ ATTENZIONE: quota {m.name} = {m.bk:.2f} troppo bassa. Il margine del bookmaker erode quasi tutto il valore potenziale.',
                'market': m.name
            })

    # Trappola 5: Long shot con edge apparente ma prob < 15%
    for m in markets:
        if hasattr(m,'bk') and m.bk > 5.0 and m.prob < 0.15 and m.edge > 0:
            traps.append({
                'level': 'warn',
                'msg': f'⚠️ {m.name}: edge apparente +{m.edge*100:.1f}% ma prob solo {m.prob*100:.1f}%. Alta varianza — servono molte scommesse per realizzare il valore.',
                'market': m.name
            })

    return traps


def confidence_score(h_stats: 'TeamStats', a_stats: 'TeamStats',
                     h2h_records: list, inj_h: list, inj_a: list,
                     odds: dict) -> Dict:
    """
    Calcola punteggio di confidenza 0-100 del modello per questa partita.
    """
    score = 100
    details = []

    # Dati squadra casa
    n_h = h_stats.matches_n if h_stats.matches_n else 0
    if n_h < 5:
        score -= 25; details.append(f'❌ Pochi dati {h_stats.name}: solo {n_h} partite (-25)')
    elif n_h < 10:
        score -= 10; details.append(f'⚠️ Dati limitati {h_stats.name}: {n_h} partite (-10)')
    else:
        details.append(f'✅ Buoni dati {h_stats.name}: {n_h} partite')

    # Dati squadra trasferta
    n_a = a_stats.matches_n if a_stats.matches_n else 0
    if n_a < 5:
        score -= 25; details.append(f'❌ Pochi dati {a_stats.name}: solo {n_a} partite (-25)')
    elif n_a < 10:
        score -= 10; details.append(f'⚠️ Dati limitati {a_stats.name}: {n_a} partite (-10)')
    else:
        details.append(f'✅ Buoni dati {a_stats.name}: {n_a} partite')

    # H2H
    if len(h2h_records) >= 4:
        details.append(f'✅ H2H storico: {len(h2h_records)} partite')
    elif len(h2h_records) > 0:
        score -= 5; details.append(f'⚠️ H2H limitato: {len(h2h_records)} partite (-5)')
    else:
        score -= 10; details.append('❌ Nessuno storico H2H (-10)')

    # Infortuni
    n_inj = len(inj_h) + len(inj_a)
    if n_inj > 4:
        score -= 15; details.append(f'❌ Molti infortuni ({n_inj} totali): alta incertezza (-15)')
    elif n_inj > 0:
        score -= 5; details.append(f'⚠️ Infortuni presenti ({n_inj}) (-5)')
    else:
        details.append('✅ Nessun infortunio rilevato')

    # Quote disponibili
    n_odds = sum(1 for k,v in odds.items() if v and v > 1.01 and not k.startswith('_'))
    if n_odds >= 6:
        details.append(f'✅ Quote complete: {n_odds} mercati')
    elif n_odds >= 3:
        score -= 5; details.append(f'⚠️ Quote parziali: {n_odds} mercati (-5)')
    else:
        score -= 15; details.append(f'❌ Poche quote disponibili: {n_odds} mercati (-15)')

    # Stats casa/trasferta separate
    if h_stats.gf_home > 0 and a_stats.gf_away > 0:
        details.append('✅ Stats casa/trasferta separate disponibili')
    else:
        score -= 5; details.append('⚠️ Stats casa/trasferta non differenziate (-5)')

    score = max(0, min(100, score))

    if score >= 75:
        level = 'alto'
        color = 'verde'
        verdict = '✅ Dati affidabili — analisi solida'
    elif score >= 50:
        level = 'medio'
        color = 'giallo'
        verdict = '⚠️ Dati parziali — usa con cautela'
    else:
        level = 'basso'
        color = 'rosso'
        verdict = '❌ Dati insufficienti — evita scommesse rischiose'

    return {
        'score': score, 'level': level, 'color': color,
        'verdict': verdict, 'details': details
    }


def traffic_light(market: 'MarketResult', edge_threshold: float,
                  mc_result: dict, conf_score: int,
                  traps: list, consistency_warnings: list) -> str:
    """
    Semaforo finale per ogni scommessa: SCOMMETTI / ASPETTA / EVITA.
    """
    if not market or market.bk <= 1.01:
        return 'EVITA'

    # Controlla trappole
    trap_markets = [t['market'] for t in traps]
    if market.name in trap_markets:
        return 'EVITA'

    # Edge sotto soglia
    if market.edge < edge_threshold:
        return 'EVITA'

    # Confidenza bassa
    if conf_score < 40:
        return 'ASPETTA'

    # Quota troppo bassa
    if market.bk < 1.40:
        return 'ASPETTA'

    # Edge positivo ma modello poco sicuro
    if conf_score < 60 and market.edge < edge_threshold * 1.5:
        return 'ASPETTA'

    # Controlla coerenza con altri mercati
    warn_markets = []
    for w in consistency_warnings:
        warn_markets.extend(w.get('markets', []))
    if market.name in warn_markets and market.edge < edge_threshold * 2:
        return 'ASPETTA'

    # Monte Carlo CI conferma
    mc_key = None
    if market.key == 'home':    mc_key = 'home_win'
    elif market.key == 'draw':  mc_key = 'draw'
    elif market.key == 'away':  mc_key = 'away_win'
    elif market.key == 'over25': mc_key = 'over25'
    elif market.key == 'btts_y': mc_key = 'btts'

    if mc_key and mc_key in mc_result.get('ci', {}):
        ci_lo, ci_hi = mc_result['ci'][mc_key]
        implied_bk = 1 / market.bk
        if ci_lo > implied_bk:
            return 'SCOMMETTI'
        elif ci_hi < implied_bk:
            return 'EVITA'

    if market.edge >= edge_threshold and conf_score >= 60:
        return 'SCOMMETTI'
    elif market.edge >= edge_threshold:
        return 'ASPETTA'

    return 'EVITA'


def bookmaker_implied_comparison(markets: list) -> List[Dict]:
    """
    Confronta probabilità modello vs probabilità implicita bookmaker.
    Mostra divergenze significative.
    """
    comparisons = []
    for m in markets:
        if not hasattr(m, 'bk') or m.bk <= 1.01:
            continue
        implied = round(1 / m.bk, 4)
        diff = m.prob - implied
        diff_pct = round(diff * 100, 1)

        if abs(diff_pct) >= 5:
            if diff_pct > 0:
                interpretation = f'Il modello vede +{diff_pct:.1f}% di probabilità rispetto al bookmaker → potenziale value'
                signal = 'value'
            else:
                interpretation = f'Il bookmaker sovrastima di {abs(diff_pct):.1f}% → il modello è più pessimista'
                signal = 'overpriced'
            comparisons.append({
                'name': m.name,
                'model_prob': round(m.prob * 100, 1),
                'implied_prob': round(implied * 100, 1),
                'diff_pct': diff_pct,
                'interpretation': interpretation,
                'signal': signal,
                'bk': m.bk,
            })

    comparisons.sort(key=lambda x: -abs(x['diff_pct']))
    return comparisons[:8]

# ==============================================================================
# API-FOOTBALL — statistiche partita reali
# ==============================================================================
AF_KEY = '13777514d0dcbde1d9e6b32141341610'
AF_BASE = 'https://v3.football.api-sports.io'
AF_HEADERS = {'x-apisports-key': AF_KEY}

# Mapping league names to API-Football league IDs
AF_LEAGUE_IDS = {
    'Serie A': 135, 'Serie B': 136,
    'Premier League': 39, 'EFL Championship': 40,
    'Bundesliga': 78, '2. Bundesliga': 79,
    'La Liga': 140, 'La Liga 2': 141,
    'Ligue 1': 61, 'Ligue 2': 62,
    'Eredivisie': 88, 'Primeira Liga': 94,
    'Champions League': 2, 'Europa League': 3,
}

def fetch_af_stats(home: str, away: str, league: str) -> Dict:
    """Fetch real match stats from API-Football for last 5 home/away matches each."""
    try:
        league_id = AF_LEAGUE_IDS.get(league)
        if not league_id:
            return {}
        # Search for team IDs
        rh = requests.get(f'{AF_BASE}/teams', headers=AF_HEADERS,
                          params={'name': home, 'league': league_id, 'season': 2025}, timeout=8)
        ra = requests.get(f'{AF_BASE}/teams', headers=AF_HEADERS,
                          params={'name': away, 'league': league_id, 'season': 2025}, timeout=8)
        if rh.status_code != 200 or ra.status_code != 200:
            return {}
        th = rh.json().get('response', [])
        ta = ra.json().get('response', [])
        if not th or not ta:
            return {}
        hid = th[0]['team']['id']
        aid = ta[0]['team']['id']
        # Fetch team season stats
        sh = requests.get(f'{AF_BASE}/teams/statistics', headers=AF_HEADERS,
                          params={'team': hid, 'league': league_id, 'season': 2025}, timeout=8)
        sa = requests.get(f'{AF_BASE}/teams/statistics', headers=AF_HEADERS,
                          params={'team': aid, 'league': league_id, 'season': 2025}, timeout=8)
        if sh.status_code != 200 or sa.status_code != 200:
            return {}
        dh = sh.json().get('response', {})
        da = sa.json().get('response', {})
        def safe_avg(d, *keys):
            v = d
            for k in keys:
                if isinstance(v, dict): v = v.get(k, {})
                else: return 0.0
            try: return float(v or 0)
            except: return 0.0
        return {
            'h_shots_avg':   safe_avg(dh, 'shots', 'on', 'average'),
            'h_poss_avg':    safe_avg(dh, 'fixtures', 'played', 'home'),
            'h_corners_avg': safe_avg(dh, 'corners', 'total', 'average'),
            'h_cards_avg':   (safe_avg(dh, 'cards', 'yellow', 'average') +
                              safe_avg(dh, 'cards', 'red', 'average')),
            'a_shots_avg':   safe_avg(da, 'shots', 'on', 'average'),
            'a_poss_avg':    safe_avg(da, 'fixtures', 'played', 'away'),
            'a_corners_avg': safe_avg(da, 'corners', 'total', 'average'),
            'a_cards_avg':   (safe_avg(da, 'cards', 'yellow', 'average') +
                              safe_avg(da, 'cards', 'red', 'average')),
        }
    except: return {}


# ==============================================================================
# UNDERSTAT — xG reale per partita
# ==============================================================================
UNDERSTAT_LEAGUE_MAP = {
    'Serie A': 'Serie_A', 'Premier League': 'EPL',
    'Bundesliga': 'Bundesliga', 'La Liga': 'La_liga',
    'Ligue 1': 'Ligue_1', 'Eredivisie': 'RFPL',  # Eredivisie non supportata, fallback
    'Scottish Premiership': None,  # Non supportata
}

def fetch_understat_xg(home: str, away: str, league: str) -> Dict:
    """Fetch real xG from Understat for both teams' last matches."""
    try:
        league_key = UNDERSTAT_LEAGUE_MAP.get(league)
        if not league_key:
            return {}
        import json as _json, re as _re
        url = f'https://understat.com/league/{league_key}/2025'
        r = requests.get(url, headers={**REQ_H, 'Accept-Language': 'en-US,en;q=0.9'}, timeout=12)
        if r.status_code != 200:
            return {}
        # Extract teamsData JSON from script tag
        match = _re.search(r"teamsData\s*=\s*JSON\.parse\('(.+?)'\)", r.text)
        if not match:
            return {}
        raw = match.group(1).encode('utf-8').decode('unicode_escape')
        teams_data = _json.loads(raw)
        # Find home and away team
        hn, an = home.lower(), away.lower()
        h_data, a_data = None, None
        for tname, tdata in teams_data.items():
            tl = tname.lower()
            if hn in tl or tl in hn: h_data = tdata
            if an in tl or tl in an: a_data = tdata
        if not h_data or not a_data:
            return {}
        def team_xg(tdata, last_n=10):
            history = tdata.get('history', [])[-last_n:]
            if not history: return 0.0, 0.0
            xgf = sum(float(m.get('xG', 0)) for m in history) / len(history)
            xga = sum(float(m.get('xGA', 0)) for m in history) / len(history)
            return round(xgf, 3), round(xga, 3)
        h_xgf, h_xga = team_xg(h_data)
        a_xgf, a_xga = team_xg(a_data)
        return {'h_xg': h_xgf, 'h_xga': h_xga, 'a_xg': a_xgf, 'a_xga': a_xga, 'source': 'Understat'}
    except: return {}


# ==============================================================================
# CLUBELO — forza relativa squadre (Elo rating)
# ==============================================================================
def fetch_clubelo(team: str) -> float:
    """Fetch current Elo rating for a team from ClubElo.com API."""
    try:
        # ClubElo uses slugified names (spaces to nothing, accents removed)
        import unicodedata
        slug = ''.join(c for c in unicodedata.normalize('NFD', team)
                       if unicodedata.category(c) != 'Mn')
        slug = slug.replace(' ', '').replace('-', '')
        r = requests.get(f'http://api.clubelo.com/{slug}', timeout=8)
        if r.status_code != 200:
            return 0.0
        lines = r.text.strip().split('\n')
        if len(lines) < 2:
            return 0.0
        # Last entry = most recent rating
        last = lines[-1].split(',')
        return float(last[4]) if len(last) > 4 else 0.0
    except: return 0.0

def elo_lambda_adjustment(elo_h: float, elo_a: float) -> tuple:
    """Convert Elo difference into lambda multipliers."""
    if elo_h <= 0 or elo_a <= 0:
        return 1.0, 1.0
    diff = elo_h - elo_a
    # Each 100 Elo ≈ 1.5x stronger → multiplicative adjustment capped at ±20%
    adj = max(-0.20, min(0.20, diff / 500))
    return round(1 + adj, 3), round(1 - adj, 3)
