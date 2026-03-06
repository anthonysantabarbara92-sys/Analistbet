"""
QUANTUM FOOTBALL ANALYTICS v9.0
engine.py — Core matematico, fetch dati, modello predittivo
Autore: QF Team | Fix: cache per-team, fallback trasparente, logging
"""

from __future__ import annotations
import math
import random
import logging
import time
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("QF_ENGINE")

# ─────────────────────────────────────────────
# COSTANTI GLOBALI
# ─────────────────────────────────────────────

LEAGUE_AVGS: dict[str, float] = {
    "Serie A":           2.67,
    "Serie B":           2.48,
    "Premier League":    2.82,
    "EFL Championship":  2.55,
    "Bundesliga":        3.17,
    "2. Bundesliga":     2.90,
    "Ligue 1":           2.61,
    "Ligue 2":           2.40,
    "La Liga":           2.55,
    "LaLiga Hypermotion":2.42,
    "Eredivisie":        3.10,
    "Pro League":        2.75,
    "Liga Portugal":     2.58,
    "Champions League":  2.84,
    "Europa League":     2.66,
    "Conference League": 2.52,
    "default":           2.65,
}

# Mapping competizione → codice football-data.org
COMP_FD: dict[str, str] = {
    "Serie A":           "SA",
    "Serie B":           "SB",
    "Premier League":    "PL",
    "EFL Championship":  "ELC",
    "Bundesliga":        "BL1",
    "2. Bundesliga":     "BL2",
    "Ligue 1":           "FL1",
    "Ligue 2":           "FL2",
    "La Liga":           "PD",
    "LaLiga Hypermotion":"SD",
    "Eredivisie":        "DED",
    "Pro League":        "BSA",
    "Liga Portugal":     "PPL",
    "Champions League":  "CL",
    "Europa League":     "EL",
    "Conference League": "UECL",
}

# Mapping competizione → sport key per The Odds API
COMP_ODDS: dict[str, str] = {
    "Serie A":           "soccer_italy_serie_a",
    "Serie B":           "soccer_italy_serie_b",
    "Premier League":    "soccer_england_league1",
    "EFL Championship":  "soccer_england_league2",
    "Bundesliga":        "soccer_germany_bundesliga",
    "2. Bundesliga":     "soccer_germany_bundesliga2",
    "Ligue 1":           "soccer_france_ligue_one",
    "Ligue 2":           "soccer_france_ligue_deux",
    "La Liga":           "soccer_spain_la_liga",
    "LaLiga Hypermotion":"soccer_spain_segunda_division",
    "Eredivisie":        "soccer_netherlands_eredivisie",
    "Pro League":        "soccer_belgium_first_div",
    "Liga Portugal":     "soccer_portugal_primeira_liga",
    "Champions League":  "soccer_uefa_champs_league",
    "Europa League":     "soccer_uefa_europa_league",
    "Conference League": "soccer_uefa_europa_conference_league",
}

COMPETITIONS: dict[str, list[str]] = {
    "🇮🇹 Italia":        ["Serie A", "Serie B"],
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inghilterra":  ["Premier League", "EFL Championship"],
    "🇩🇪 Germania":       ["Bundesliga", "2. Bundesliga"],
    "🇫🇷 Francia":        ["Ligue 1", "Ligue 2"],
    "🇪🇸 Spagna":         ["La Liga", "LaLiga Hypermotion"],
    "🇳🇱 Olanda":         ["Eredivisie"],
    "🇧🇪 Belgio":         ["Pro League"],
    "🇵🇹 Portogallo":     ["Liga Portugal"],
    "🇪🇺 Champions":      ["Champions League"],
    "🇪🇺 Europa League":  ["Europa League"],
    "🇪🇺 Conference":     ["Conference League"],
}

BK_PRIORITY = ["Sportium", "bet365", "unibet", "bwin", "betway",
                "williamhill", "marathonbet", "pinnacle"]

# Understat: solo top-5 leghe
UNDERSTAT_LEAGUES = {
    "Serie A":        "Serie_A",
    "Premier League": "EPL",
    "Bundesliga":     "Bundesliga",
    "La Liga":        "La_liga",
    "Ligue 1":        "Ligue_1",
}

UNDERSTAT_TEAMS_CURRENT_SEASON = 2024  # stagione understat corrente

# ─────────────────────────────────────────────
# DATACLASSES
# ─────────────────────────────────────────────

@dataclass
class MatchRecord:
    gf: float
    ga: float
    xg: float
    xga: float
    home: bool
    weight: float = 1.0

@dataclass
class TeamStats:
    name: str
    league: str
    matches: list[MatchRecord] = field(default_factory=list)
    corners_avg: float = 5.0
    cards_avg: float = 1.8
    shots_avg: float = 12.0
    elo: float = 1500.0
    injuries: list[dict] = field(default_factory=list)
    # fonte dei dati per trasparenza
    data_source: str = "N/D"
    api_warnings: list[str] = field(default_factory=list)

    @property
    def n_matches(self) -> int:
        return len(self.matches)

    def avg_gf(self, home_only: bool = False, away_only: bool = False) -> float:
        pool = self._filter(home_only, away_only)
        if not pool: return LEAGUE_AVGS.get(self.league, LEAGUE_AVGS["default"]) / 2
        return np.average([m.gf for m in pool], weights=[m.weight for m in pool])

    def avg_ga(self, home_only: bool = False, away_only: bool = False) -> float:
        pool = self._filter(home_only, away_only)
        if not pool: return LEAGUE_AVGS.get(self.league, LEAGUE_AVGS["default"]) / 2
        return np.average([m.ga for m in pool], weights=[m.weight for m in pool])

    def avg_xg(self) -> float:
        if not self.matches: return LEAGUE_AVGS.get(self.league, LEAGUE_AVGS["default"]) / 2
        return np.average([m.xg for m in self.matches], weights=[m.weight for m in self.matches])

    def avg_xga(self) -> float:
        if not self.matches: return LEAGUE_AVGS.get(self.league, LEAGUE_AVGS["default"]) / 2
        return np.average([m.xga for m in self.matches], weights=[m.weight for m in self.matches])

    def form_str(self) -> str:
        """Stringa WDL ultimi 5"""
        results = []
        for m in self.matches[-5:]:
            if m.gf > m.ga: results.append("W")
            elif m.gf == m.ga: results.append("D")
            else: results.append("L")
        return " ".join(results) if results else "—"

    def _filter(self, home_only, away_only):
        if home_only: return [m for m in self.matches if m.home]
        if away_only: return [m for m in self.matches if not m.home]
        return self.matches

@dataclass
class H2HRecord:
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    year_weight: float = 1.0

@dataclass
class EngineResult:
    lambda_h: float
    lambda_a: float
    matrix: np.ndarray
    prob_1: float
    prob_x: float
    prob_2: float
    markets: dict
    mc_ci_1: tuple[float, float]
    mc_ci_x: tuple[float, float]
    mc_ci_2: tuple[float, float]
    confidence_score: int
    warnings: list[str]
    traps: list[str]
    rho: float
    adj_log: list[str]

# ─────────────────────────────────────────────
# FETCH: football-data.org
# ─────────────────────────────────────────────

def fetch_fd_stats(
    fd_key: str,
    league: str,
    team_name: str,
    is_home: bool,
    season: int = 2024,
) -> tuple[TeamStats, str]:
    """
    Recupera ultime 20 partite da football-data.org.
    Ritorna (TeamStats, fonte_usata).
    NOTA: team_name è parametro esplicito → cache per squadra corretta.
    """
    stats = TeamStats(name=team_name, league=league)
    comp_code = COMP_FD.get(league)
    if not comp_code:
        stats.api_warnings.append(f"Nessun codice FD per lega '{league}'")
        return stats, "fallback_medio_lega"

    url = f"https://api.football-data.org/v4/competitions/{comp_code}/matches"
    headers = {"X-Auth-Token": fd_key}
    params = {"season": season, "status": "FINISHED"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 429:
            stats.api_warnings.append("football-data.org: rate limit (429)")
            return stats, "rate_limit_FD"
        if r.status_code != 200:
            stats.api_warnings.append(f"football-data.org: HTTP {r.status_code}")
            return stats, f"errore_FD_{r.status_code}"

        data = r.json()
        matches_raw = data.get("matches", [])

        for m in matches_raw:
            ht = m.get("homeTeam", {}).get("name", "")
            at = m.get("awayTeam", {}).get("name", "")
            # Fuzzy match case-insensitive
            team_lower = team_name.lower()
            is_match = (team_lower in ht.lower() or ht.lower() in team_lower or
                        team_lower in at.lower() or at.lower() in team_lower)
            if not is_match:
                continue

            score = m.get("score", {}).get("fullTime", {})
            hg = score.get("home")
            ag = score.get("away")
            if hg is None or ag is None:
                continue

            playing_home = team_lower in ht.lower() or ht.lower() in team_lower
            gf = hg if playing_home else ag
            ga = ag if playing_home else hg

            # xG stimato (Understat verrà sovrascrivere questi valori)
            lg_avg = LEAGUE_AVGS.get(league, LEAGUE_AVGS["default"])
            xg_est = float(gf) * 0.85 + lg_avg * 0.15
            xga_est = float(ga) * 0.85 + lg_avg * 0.15

            # Pesi temporali: ultime 5 pesano 2.0
            idx = len(stats.matches)
            weight = 2.0 if idx >= max(0, len(matches_raw) - 5) else 1.0

            stats.matches.append(MatchRecord(
                gf=float(gf), ga=float(ga),
                xg=xg_est, xga=xga_est,
                home=playing_home, weight=weight
            ))

        stats.data_source = "football-data.org"
        return stats, "football-data.org"

    except requests.exceptions.Timeout:
        stats.api_warnings.append("football-data.org: timeout")
        return stats, "timeout_FD"
    except Exception as e:
        stats.api_warnings.append(f"football-data.org: {e}")
        return stats, f"errore_FD"


# ─────────────────────────────────────────────
# FETCH: API-Football (backup primario)
# ─────────────────────────────────────────────

AF_LEAGUE_IDS: dict[str, int] = {
    "Serie A":           135,
    "Serie B":           136,
    "Premier League":    39,
    "EFL Championship":  40,
    "Bundesliga":        78,
    "2. Bundesliga":     79,
    "Ligue 1":           61,
    "Ligue 2":           62,
    "La Liga":           140,
    "LaLiga Hypermotion":141,
    "Eredivisie":        88,
    "Pro League":        144,
    "Liga Portugal":     94,
    "Champions League":  2,
    "Europa League":     3,
    "Conference League": 848,
}

def fetch_af_stats(
    af_key: str,
    league: str,
    team_name: str,
    season: int = 2024,
) -> tuple[TeamStats, str]:
    """
    Recupera statistiche da API-Football come backup.
    Parametro team_name esplicito per cache corretta.
    """
    stats = TeamStats(name=team_name, league=league)
    league_id = AF_LEAGUE_IDS.get(league)
    if not league_id:
        stats.api_warnings.append(f"Nessun ID AF per lega '{league}'")
        return stats, "fallback_af_no_id"

    # Prima cerca il team_id
    search_url = "https://v3.football.api-sports.io/teams"
    headers = {"x-apisports-key": af_key}
    params = {"search": team_name}

    try:
        rs = requests.get(search_url, headers=headers, params=params, timeout=10)
        if rs.status_code == 429:
            stats.api_warnings.append("API-Football: rate limit")
            return stats, "rate_limit_AF"
        if rs.status_code != 200:
            stats.api_warnings.append(f"API-Football search: HTTP {rs.status_code}")
            return stats, f"errore_AF_{rs.status_code}"

        teams_data = rs.json().get("response", [])
        if not teams_data:
            stats.api_warnings.append(f"API-Football: squadra '{team_name}' non trovata")
            return stats, "squadra_non_trovata_AF"

        team_id = teams_data[0]["team"]["id"]

        # Recupera statistiche stagionali
        stat_url = "https://v3.football.api-sports.io/teams/statistics"
        params2 = {"team": team_id, "league": league_id, "season": season}
        rs2 = requests.get(stat_url, headers=headers, params=params2, timeout=10)
        if rs2.status_code != 200:
            stats.api_warnings.append(f"API-Football stats: HTTP {rs2.status_code}")
            return stats, f"errore_AF_stats"

        resp = rs2.json().get("response", {})
        goals = resp.get("goals", {})
        gf_total = goals.get("for", {}).get("total", {}).get("total", 0) or 0
        ga_total = goals.get("against", {}).get("total", {}).get("total", 0) or 0
        played = resp.get("fixtures", {}).get("played", {}).get("total", 1) or 1

        avg_gf = gf_total / played
        avg_ga = ga_total / played
        lg_avg = LEAGUE_AVGS.get(league, LEAGUE_AVGS["default"])
        xg_est = avg_gf * 0.85 + lg_avg * 0.15
        xga_est = avg_ga * 0.85 + lg_avg * 0.15

        # Costruiamo match sintetici pesati
        for i in range(min(played, 20)):
            stats.matches.append(MatchRecord(
                gf=avg_gf, ga=avg_ga,
                xg=xg_est, xga=xga_est,
                home=(i % 2 == 0),
                weight=1.0
            ))

        # Angoli e cartellini
        shots = resp.get("shots", {})
        stats.shots_avg = (shots.get("on", {}).get("total") or 0) / played
        stats.data_source = "API-Football"
        return stats, "API-Football"

    except requests.exceptions.Timeout:
        stats.api_warnings.append("API-Football: timeout")
        return stats, "timeout_AF"
    except Exception as e:
        stats.api_warnings.append(f"API-Football: {e}")
        return stats, "errore_AF"


# ─────────────────────────────────────────────
# FETCH: Understat xG reale
# ─────────────────────────────────────────────

def fetch_understat_xg(
    league: str,
    team_name: str,
    season: int = UNDERSTAT_TEAMS_CURRENT_SEASON,
) -> tuple[list[tuple[float, float]], str]:
    """
    Recupera xG e xGA reali da Understat (solo top-5 leghe).
    Ritorna lista di (xg, xga) per gli ultimi 10 match.
    """
    us_league = UNDERSTAT_LEAGUES.get(league)
    if not us_league:
        return [], f"understat_non_supporta_{league}"

    url = f"https://understat.com/league/{us_league}/{season}"
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return [], f"understat_HTTP_{r.status_code}"

        soup = BeautifulSoup(r.text, "html.parser")
        scripts = soup.find_all("script")
        json_data = None
        for sc in scripts:
            if "teamsData" in sc.text:
                import re, json
                match = re.search(r"JSON\.parse\('(.+?)'\)", sc.text)
                if match:
                    raw = match.group(1).encode().decode("unicode_escape")
                    json_data = json.loads(raw)
                break

        if not json_data:
            return [], "understat_json_non_trovato"

        # Cerca squadra con fuzzy match
        team_key = None
        team_lower = team_name.lower()
        for k in json_data:
            if team_lower in k.lower() or k.lower() in team_lower:
                team_key = k
                break

        if not team_key:
            return [], f"understat_squadra_{team_name}_non_trovata"

        history = json_data[team_key].get("history", [])[-10:]
        result = []
        for h in history:
            xg = float(h.get("xG", 0))
            xga = float(h.get("xGA", 0))
            result.append((xg, xga))

        return result, "Understat"

    except Exception as e:
        return [], f"understat_errore: {e}"


# ─────────────────────────────────────────────
# FETCH: ClubElo
# ─────────────────────────────────────────────

def fetch_clubelo(team_name: str) -> tuple[float, str]:
    """Recupera rating Elo da ClubElo. Ritorna (elo, fonte)."""
    url = f"http://api.clubelo.com/{team_name.replace(' ', '-')}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return 1500.0, f"clubelo_HTTP_{r.status_code}"
        lines = r.text.strip().split("\n")
        if len(lines) < 2:
            return 1500.0, "clubelo_dati_vuoti"
        last = lines[-1].split(",")
        elo = float(last[4])
        return elo, "ClubElo"
    except Exception as e:
        return 1500.0, f"clubelo_errore: {e}"


# ─────────────────────────────────────────────
# FETCH: Quote reali (The Odds API)
# ─────────────────────────────────────────────

def fetch_odds(
    odds_key: str,
    league: str,
    home_team: str,
    away_team: str,
) -> tuple[dict, str]:
    """
    Recupera quote 1X2, O/U 2.5, BTTS da The Odds API.
    Ritorna (odds_dict, fonte).
    """
    sport_key = COMP_ODDS.get(league)
    if not sport_key:
        return {}, f"odds_no_sport_key_{league}"

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": odds_key,
        "regions": "eu",
        "markets": "h2h,totals,btts",
        "oddsFormat": "decimal",
        "bookmakers": ",".join(BK_PRIORITY[:5]),
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 401:
            return {}, "odds_chiave_non_valida"
        if r.status_code == 422:
            return {}, "odds_sport_non_disponibile"
        if r.status_code != 200:
            return {}, f"odds_HTTP_{r.status_code}"

        events = r.json()
        home_lower = home_team.lower()
        away_lower = away_team.lower()

        for ev in events:
            ht = ev.get("home_team", "").lower()
            at = ev.get("away_team", "").lower()
            # Fuzzy match
            hm = home_lower in ht or ht in home_lower
            am = away_lower in at or at in away_lower
            if not (hm and am):
                continue

            result = {}
            for bk in ev.get("bookmakers", []):
                bk_name = bk.get("key", "").lower()
                priority = next((i for i, b in enumerate(BK_PRIORITY)
                                 if b.lower() in bk_name), 999)
                for mkt in bk.get("markets", []):
                    key = mkt.get("key")
                    if key == "h2h":
                        for outcome in mkt.get("outcomes", []):
                            n = outcome.get("name", "").lower()
                            pr = outcome.get("price", 0)
                            if "draw" in n:
                                if "quota_x" not in result or priority < result.get("_priority_x", 999):
                                    result["quota_x"] = pr
                                    result["_priority_x"] = priority
                            elif ht in n or n in ht:
                                if "quota_1" not in result or priority < result.get("_priority_1", 999):
                                    result["quota_1"] = pr
                                    result["_priority_1"] = priority
                            else:
                                if "quota_2" not in result or priority < result.get("_priority_2", 999):
                                    result["quota_2"] = pr
                                    result["_priority_2"] = priority
                    elif key == "totals":
                        for outcome in mkt.get("outcomes", []):
                            pt = outcome.get("point", 0)
                            nm = outcome.get("name", "").lower()
                            if abs(pt - 2.5) < 0.01:
                                k = "quota_over25" if nm == "over" else "quota_under25"
                                if k not in result or priority < result.get(f"_p_{k}", 999):
                                    result[k] = outcome.get("price", 0)
                                    result[f"_p_{k}"] = priority
                    elif key == "btts":
                        for outcome in mkt.get("outcomes", []):
                            nm = outcome.get("name", "").lower()
                            if "yes" in nm:
                                if "quota_btts_si" not in result or priority < result.get("_p_btts_si", 999):
                                    result["quota_btts_si"] = outcome.get("price", 0)
                                    result["_p_btts_si"] = priority
                            elif "no" in nm:
                                if "quota_btts_no" not in result or priority < result.get("_p_btts_no", 999):
                                    result["quota_btts_no"] = outcome.get("price", 0)
                                    result["_p_btts_no"] = priority

            # Pulisci chiavi interne
            result = {k: v for k, v in result.items() if not k.startswith("_")}
            if result:
                return result, "The Odds API"

        return {}, "odds_evento_non_trovato"

    except Exception as e:
        return {}, f"odds_errore: {e}"


# ─────────────────────────────────────────────
# FETCH: Infortuni Transfermarkt
# ─────────────────────────────────────────────

INJURY_IMPACT = {
    "striker":     -0.18,
    "attaccante":  -0.18,
    "midfielder":  -0.09,
    "centrocampista": -0.09,
    "defender":    -0.05,
    "difensore":   -0.05,
    "goalkeeper":  -0.06,
    "portiere":    -0.06,
}

def fetch_injuries_tm(team_name: str) -> tuple[list[dict], str]:
    """Scraping infortuni da Transfermarkt."""
    slug = team_name.lower().replace(" ", "-")
    url = f"https://www.transfermarkt.com/{slug}/verletzungen/verein/0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "it-IT,it;q=0.9"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return [], f"tm_HTTP_{r.status_code}"

        soup = BeautifulSoup(r.text, "html.parser")
        injuries = []
        rows = soup.select("table.items tbody tr")[:10]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            player_name = cells[0].get_text(strip=True)
            position = cells[1].get_text(strip=True).lower()
            injuries.append({"player": player_name, "position": position})

        return injuries, "Transfermarkt"
    except Exception as e:
        return [], f"tm_errore: {e}"


def injuries_impact(injuries: list[dict]) -> float:
    """Calcola impatto totale infortuni sul lambda (max -35%)."""
    total = 0.0
    for inj in injuries:
        pos = inj.get("position", "").lower()
        for key, val in INJURY_IMPACT.items():
            if key in pos:
                total += val
                break
    return max(total, -0.35)


# ─────────────────────────────────────────────
# FETCH: H2H da football-data.org
# ─────────────────────────────────────────────

def fetch_h2h(
    fd_key: str,
    team1: str,
    team2: str,
    league: str,
    season_range: int = 3,
) -> tuple[list[H2HRecord], str]:
    """Recupera storico H2H degli ultimi N anni."""
    comp_code = COMP_FD.get(league)
    if not comp_code:
        return [], "h2h_no_comp_code"

    records = []
    current_year = 2024
    for i, yr in enumerate(range(current_year, current_year - season_range, -1)):
        weight = [1.0, 0.7, 0.4][i]
        url = f"https://api.football-data.org/v4/competitions/{comp_code}/matches"
        headers = {"X-Auth-Token": fd_key}
        params = {"season": yr, "status": "FINISHED"}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code != 200:
                continue
            for m in r.json().get("matches", []):
                ht = m.get("homeTeam", {}).get("name", "").lower()
                at = m.get("awayTeam", {}).get("name", "").lower()
                t1l = team1.lower()
                t2l = team2.lower()
                is_h2h = (
                    (t1l in ht or ht in t1l) and (t2l in at or at in t2l) or
                    (t2l in ht or ht in t2l) and (t1l in at or at in t1l)
                )
                if is_h2h:
                    sc = m.get("score", {}).get("fullTime", {})
                    hg = sc.get("home")
                    ag = sc.get("away")
                    if hg is not None and ag is not None:
                        records.append(H2HRecord(
                            home_team=m.get("homeTeam", {}).get("name", ""),
                            away_team=m.get("awayTeam", {}).get("name", ""),
                            home_goals=int(hg), away_goals=int(ag),
                            year_weight=weight
                        ))
        except Exception:
            continue

    return records, "football-data.org (H2H)" if records else "h2h_vuoto"


# ─────────────────────────────────────────────
# MOTORE MATEMATICO
# ─────────────────────────────────────────────

def dixon_coles_correction(
    home_goals: int,
    away_goals: int,
    lambda_h: float,
    lambda_a: float,
    rho: float,
) -> float:
    """Fattore correttivo Dixon-Coles per punteggi bassi."""
    if home_goals == 0 and away_goals == 0:
        return 1 - lambda_h * lambda_a * rho
    elif home_goals == 1 and away_goals == 0:
        return 1 + lambda_a * rho
    elif home_goals == 0 and away_goals == 1:
        return 1 + lambda_h * rho
    elif home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


def build_score_matrix(
    lambda_h: float,
    lambda_a: float,
    rho: float = -0.13,
    max_goals: int = 10,
) -> np.ndarray:
    """Costruisce matrice (max_goals+1)×(max_goals+1) di prob punteggio esatto."""
    mat = np.zeros((max_goals + 1, max_goals + 1))
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p_h = math.exp(-lambda_h) * (lambda_h ** h) / math.factorial(h)
            p_a = math.exp(-lambda_a) * (lambda_a ** a) / math.factorial(a)
            dc = dixon_coles_correction(h, a, lambda_h, lambda_a, rho)
            mat[h, a] = p_h * p_a * dc
    # Normalizza
    mat /= mat.sum()
    return mat


def compute_rho(h2h: list[H2HRecord]) -> float:
    """Stima rho da storico H2H se disponibile."""
    if len(h2h) < 10:
        return -0.13
    low_score = sum(
        1 for r in h2h
        if r.home_goals <= 1 and r.away_goals <= 1
    )
    frac = low_score / len(h2h)
    rho = -0.13 + (frac - 0.4) * 0.2
    return max(-0.25, min(0.0, rho))


def regression_to_mean(value: float, n_matches: int, league_avg: float) -> float:
    """Regressione verso media di lega (max 25% con < 5 partite)."""
    if n_matches >= 15:
        return value
    elif n_matches >= 10:
        alpha = 0.05
    elif n_matches >= 5:
        alpha = 0.15
    else:
        alpha = 0.25
    return value * (1 - alpha) + (league_avg / 2) * alpha


def elo_multiplier(elo_self: float, elo_opp: float) -> float:
    """Moltiplicatore lambda da differenza Elo. Cap ±20%."""
    diff = elo_self - elo_opp
    mult = 1 + (diff / 500) * 0.20
    return max(0.80, min(1.20, mult))


class AdvancedEngine:
    """Core matematico principale."""

    def __init__(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats,
        h2h: list[H2HRecord],
        odds: dict,
        league: str,
        # Slider manuale
        motivation_h: float = 0.0,     # -20 → +20 (%)
        motivation_a: float = 0.0,
        pressure_h: float = 0.0,       # -10 → +10
        pressure_a: float = 0.0,
        fatigue_days_h: int = 7,       # giorni dall'ultima partita
        fatigue_days_a: int = 7,
        referee_mult: float = 1.0,     # 0.7 → 1.5
    ):
        self.hs = home_stats
        self.as_ = away_stats
        self.h2h = h2h
        self.odds = odds
        self.league = league
        self.mot_h = motivation_h / 100
        self.mot_a = motivation_a / 100
        self.pres_h = pressure_h / 100
        self.pres_a = pressure_a / 100
        self.fat_h = fatigue_days_h
        self.fat_a = fatigue_days_a
        self.ref_mult = referee_mult
        self.adj_log: list[str] = []

    def _fatigue_mult(self, days: int) -> float:
        if days < 3: return 0.92
        if days < 5: return 0.96
        return 1.0

    def compute(self) -> EngineResult:
        lg_avg = LEAGUE_AVGS.get(self.league, LEAGUE_AVGS["default"])
        adj = self.adj_log

        # ── Base lambda da xG + GF ponderati
        xg_h = self.hs.avg_xg()
        xg_a = self.as_.avg_xg()
        gf_h = self.hs.avg_gf(home_only=True)
        ga_h = self.hs.avg_ga(home_only=True)
        gf_a = self.as_.avg_gf(away_only=True)
        ga_a = self.as_.avg_ga(away_only=True)

        # Lambda base: media pesata xG (70%) e GF (30%)
        lam_h_raw = xg_h * 0.70 + gf_h * 0.30
        lam_a_raw = xg_a * 0.70 + gf_a * 0.30
        adj.append(f"λ base → H:{lam_h_raw:.3f} A:{lam_a_raw:.3f}")

        # ── Difesa avversaria
        def_adj_h = (ga_a / (lg_avg / 2)) if ga_a > 0 else 1.0
        def_adj_a = (ga_h / (lg_avg / 2)) if ga_h > 0 else 1.0
        lam_h = lam_h_raw * def_adj_h
        lam_a = lam_a_raw * def_adj_a
        adj.append(f"Difesa avv → H:{lam_h:.3f} A:{lam_a:.3f}")

        # ── Regressione verso media
        lam_h = regression_to_mean(lam_h, self.hs.n_matches, lg_avg)
        lam_a = regression_to_mean(lam_a, self.as_.n_matches, lg_avg)
        adj.append(f"Regressione media → H:{lam_h:.3f} A:{lam_a:.3f}")

        # ── Aggiustamento H2H
        if self.h2h:
            h2h_delta = self._h2h_adjustment()
            lam_h *= (1 + h2h_delta * 0.08)
            lam_a *= (1 - h2h_delta * 0.08)
            adj.append(f"H2H adj ({h2h_delta:+.2f}) → H:{lam_h:.3f} A:{lam_a:.3f}")

        # ── Infortuni
        inj_mult_h = 1 + injuries_impact(self.hs.injuries)
        inj_mult_a = 1 + injuries_impact(self.as_.injuries)
        lam_h *= inj_mult_h
        lam_a *= inj_mult_a
        adj.append(f"Infortuni → H:{lam_h:.3f} A:{lam_a:.3f}")

        # ── Elo
        elo_h = elo_multiplier(self.hs.elo, self.as_.elo)
        elo_a = elo_multiplier(self.as_.elo, self.hs.elo)
        # Bonus casa Elo
        lam_h *= elo_h * 1.05
        lam_a *= elo_a
        adj.append(f"Elo ({self.hs.elo:.0f} vs {self.as_.elo:.0f}) → H:{lam_h:.3f} A:{lam_a:.3f}")

        # ── Motivazione
        lam_h *= (1 + self.mot_h)
        lam_a *= (1 + self.mot_a)
        adj.append(f"Motivazione → H:{lam_h:.3f} A:{lam_a:.3f}")

        # ── Stanchezza
        lam_h *= self._fatigue_mult(self.fat_h)
        lam_a *= self._fatigue_mult(self.fat_a)
        adj.append(f"Stanchezza → H:{lam_h:.3f} A:{lam_a:.3f}")

        # ── Pressione psicologica
        lam_h *= (1 + self.pres_h)
        lam_a *= (1 + self.pres_a)
        adj.append(f"Pressione → H:{lam_h:.3f} A:{lam_a:.3f}")

        # ── Clamp
        lam_h = max(0.3, min(lam_h, 4.5))
        lam_a = max(0.3, min(lam_a, 4.5))
        adj.append(f"λ finale → H:{lam_h:.3f} A:{lam_a:.3f}")

        # ── Rho
        rho = compute_rho(self.h2h)

        # ── Matrice punteggi
        matrix = build_score_matrix(lam_h, lam_a, rho)

        # ── Probabilità 1X2
        prob_1 = float(np.sum(np.tril(matrix, -1)))
        prob_x = float(np.sum(np.diag(matrix)))
        prob_2 = float(np.sum(np.triu(matrix, 1)))

        # ── Mercati
        markets = self._build_all_markets(matrix, lam_h, lam_a)

        # ── Monte Carlo
        ci_1, ci_x, ci_2 = self._monte_carlo(lam_h, lam_a, rho)

        # ── Confidence Score
        confidence = self._confidence_score()

        # ── Warnings
        warnings = self._build_warnings(lam_h, lam_a, matrix)

        # ── Trap detector
        traps = self._detect_traps(markets, lam_h, lam_a)

        return EngineResult(
            lambda_h=lam_h, lambda_a=lam_a,
            matrix=matrix,
            prob_1=prob_1, prob_x=prob_x, prob_2=prob_2,
            markets=markets,
            mc_ci_1=ci_1, mc_ci_x=ci_x, mc_ci_2=ci_2,
            confidence_score=confidence,
            warnings=warnings, traps=traps,
            rho=rho, adj_log=adj,
        )

    def _h2h_adjustment(self) -> float:
        """Ritorna valore tra -1 e +1: positivo → Casa domina H2H."""
        score = 0.0
        total_w = 0.0
        home_lower = self.hs.name.lower()
        for r in self.h2h:
            w = r.year_weight
            is_home = home_lower in r.home_team.lower() or r.home_team.lower() in home_lower
            if is_home:
                if r.home_goals > r.away_goals: score += w
                elif r.home_goals < r.away_goals: score -= w
            else:
                if r.away_goals > r.home_goals: score += w
                elif r.away_goals < r.home_goals: score -= w
            total_w += w
        return (score / total_w) if total_w > 0 else 0.0

    def _build_all_markets(self, mat: np.ndarray, lh: float, la: float) -> dict:
        m = {}

        # ── 1X2
        m["1X2"] = {
            "1": np.sum(np.tril(mat, -1)),
            "X": np.sum(np.diag(mat)),
            "2": np.sum(np.triu(mat, 1)),
        }

        # ── Doppia chance
        m["DC"] = {
            "1X": m["1X2"]["1"] + m["1X2"]["X"],
            "12": m["1X2"]["1"] + m["1X2"]["2"],
            "X2": m["1X2"]["X"] + m["1X2"]["2"],
        }

        # ── DNB
        sum_goals = m["1X2"]["1"] + m["1X2"]["2"]
        m["DNB"] = {
            "Casa": m["1X2"]["1"] / sum_goals if sum_goals > 0 else 0.5,
            "Trasferta": m["1X2"]["2"] / sum_goals if sum_goals > 0 else 0.5,
        }

        # ── Over/Under
        totals = {}
        for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
            over = float(np.sum([mat[h, a] for h in range(mat.shape[0])
                                 for a in range(mat.shape[1]) if h + a > line]))
            totals[f"over_{line}"] = over
            totals[f"under_{line}"] = 1 - over
        m["OU"] = totals

        # ── BTTS
        btts_no = float(np.sum(mat[0, :]) + np.sum(mat[:, 0]) - mat[0, 0])
        m["BTTS"] = {"Si": 1 - btts_no, "No": btts_no}

        # ── Gol esatti totali
        m["EXACT_GOALS"] = {}
        for n in range(7):
            m["EXACT_GOALS"][n] = float(np.sum([mat[h, a] for h in range(mat.shape[0])
                                                for a in range(mat.shape[1]) if h + a == n]))

        # ── Gol Casa
        m["GOALS_H"] = {}
        for n in range(5):
            m["GOALS_H"][n] = float(np.sum(mat[n, :]))
        m["GOALS_H"]["2+"] = float(np.sum(mat[2:, :]))

        # ── Gol Trasferta
        m["GOALS_A"] = {}
        for n in range(5):
            m["GOALS_A"][n] = float(np.sum(mat[:, n]))
        m["GOALS_A"]["2+"] = float(np.sum(mat[:, 2:]))

        # ── Multigoal
        m["MULTI"] = {
            "0-1": m["EXACT_GOALS"][0] + m["EXACT_GOALS"][1],
            "2-3": m["EXACT_GOALS"][2] + m["EXACT_GOALS"][3],
            "3-4": m["EXACT_GOALS"][3] + m["EXACT_GOALS"][4],
            "4-5": m["EXACT_GOALS"][4] + m["EXACT_GOALS"].get(5, 0),
            "5+":  float(np.sum([mat[h, a] for h in range(mat.shape[0])
                                 for a in range(mat.shape[1]) if h + a >= 5])),
        }

        # ── HT/FT (approssimazione Poisson metà tempo)
        lh2 = lh / 2
        la2 = la / 2
        mat_ht = build_score_matrix(lh2, la2, rho=0.0, max_goals=6)
        ht_res = {
            "H": float(np.sum(np.tril(mat_ht, -1))),
            "D": float(np.sum(np.diag(mat_ht))),
            "A": float(np.sum(np.triu(mat_ht, 1))),
        }
        htft = {}
        for ht_r, ht_p in ht_res.items():
            for ft_r, ft_p in m["1X2"].items():
                htft[f"{ht_r}/{ft_r}"] = float(ht_p * ft_p)
        m["HTFT"] = htft

        # ── Handicap europeo
        m["HANDICAP"] = {
            "Casa -1": float(np.sum([mat[h, a] for h in range(mat.shape[0])
                                     for a in range(mat.shape[1]) if h - 1 > a])),
            "Ospite -1": float(np.sum([mat[h, a] for h in range(mat.shape[0])
                                       for a in range(mat.shape[1]) if a - 1 > h])),
            "Casa -2": float(np.sum([mat[h, a] for h in range(mat.shape[0])
                                     for a in range(mat.shape[1]) if h - 2 > a])),
        }

        # ── Winning margin
        m["MARGIN"] = {}
        for diff in [1, 2, 3]:
            for side, (d_min, d_max) in [("Casa", (diff, diff)), ("Ospite", (-diff, -diff))]:
                m["MARGIN"][f"{side} +{diff}"] = float(
                    np.sum([mat[h, a] for h in range(mat.shape[0])
                            for a in range(mat.shape[1])
                            if h - a == (diff if side == "Casa" else -diff)])
                )
        m["MARGIN"]["Casa 3+"] = float(np.sum([mat[h, a] for h in range(mat.shape[0])
                                                for a in range(mat.shape[1]) if h - a >= 3]))
        m["MARGIN"]["Ospite 3+"] = float(np.sum([mat[h, a] for h in range(mat.shape[0])
                                                  for a in range(mat.shape[1]) if a - h >= 3]))

        # ── Angoli (stima da media squadre)
        avg_corners = self.hs.corners_avg + self.as_.corners_avg
        import math as _math
        lam_c = avg_corners
        p_over95 = sum(
            _math.exp(-lam_c) * lam_c**k / _math.factorial(k)
            for k in range(10)
        )
        p_over95 = 1 - p_over95
        m["CORNERS"] = {"Over 9.5": p_over95, "Under 9.5": 1 - p_over95}

        # ── Cartellini
        avg_cards = (self.hs.cards_avg + self.as_.cards_avg) * self.ref_mult
        lam_k = avg_cards
        p_over35 = sum(
            _math.exp(-lam_k) * lam_k**k / _math.factorial(k)
            for k in range(4)
        )
        p_over35 = 1 - p_over35
        m["CARDS"] = {"Over 3.5": p_over35, "Under 3.5": 1 - p_over35}

        # ── BTTS primo/secondo tempo
        lh1 = lh * 0.48
        la1 = la * 0.48
        mat1 = build_score_matrix(lh1, la1, rho=0.0, max_goals=5)
        btts1_no = float(np.sum(mat1[0, :]) + np.sum(mat1[:, 0]) - mat1[0, 0])
        lh2r = lh * 0.52
        la2r = la * 0.52
        mat2h = build_score_matrix(lh2r, la2r, rho=0.0, max_goals=5)
        btts2_no = float(np.sum(mat2h[0, :]) + np.sum(mat2h[:, 0]) - mat2h[0, 0])
        m["BTTS_HALVES"] = {
            "BTTS 1T Si": 1 - btts1_no, "BTTS 1T No": btts1_no,
            "BTTS 2T Si": 1 - btts2_no, "BTTS 2T No": btts2_no,
        }

        # ── Over primo tempo
        ht_mat = build_score_matrix(lh1, la1, rho=0.0, max_goals=5)
        m["OU_1T"] = {
            "Over 0.5 1T": float(np.sum([ht_mat[h, a] for h in range(6)
                                          for a in range(6) if h + a >= 1])),
            "Over 1.5 1T": float(np.sum([ht_mat[h, a] for h in range(6)
                                          for a in range(6) if h + a >= 2])),
            "No Gol 1T":   float(ht_mat[0, 0]),
        }

        # ── Combo (top 20 automatici)
        m["COMBO"] = self._build_combos(m)

        # ── Punteggi esatti top 10
        flat = [(h, a, mat[h, a]) for h in range(mat.shape[0])
                for a in range(mat.shape[1])]
        flat.sort(key=lambda x: -x[2])
        m["TOP_SCORES"] = [(f"{h}-{a}", float(p)) for h, a, p in flat[:10]]

        return m

    def _build_combos(self, m: dict) -> list[dict]:
        """Crea 20 combinazioni automatiche."""
        combos = []
        picks = [
            ("1", m["1X2"]["1"], "1X2 - Casa"),
            ("X", m["1X2"]["X"], "1X2 - Pareggio"),
            ("2", m["1X2"]["2"], "1X2 - Trasferta"),
            ("1X", m["DC"]["1X"], "DC - 1X"),
            ("12", m["DC"]["12"], "DC - 12"),
            ("X2", m["DC"]["X2"], "DC - X2"),
            ("O2.5", m["OU"]["over_2.5"], "Over 2.5"),
            ("U2.5", m["OU"]["under_2.5"], "Under 2.5"),
            ("BTTS_SI", m["BTTS"]["Si"], "BTTS Sì"),
            ("BTTS_NO", m["BTTS"]["No"], "BTTS No"),
            ("O1.5", m["OU"]["over_1.5"], "Over 1.5"),
            ("O3.5", m["OU"]["over_3.5"], "Over 3.5"),
        ]
        for i, (k1, p1, n1) in enumerate(picks):
            for k2, p2, n2 in picks[i+1:]:
                if len(combos) >= 20:
                    break
                prob = float(p1 * p2)
                combos.append({
                    "label": f"{n1} + {n2}",
                    "prob": prob,
                    "fair_odd": round(1 / prob, 2) if prob > 0 else 999,
                })
            if len(combos) >= 20:
                break
        combos.sort(key=lambda x: -x["prob"])
        return combos[:20]

    def _monte_carlo(
        self,
        lh: float,
        la: float,
        rho: float,
        n_sim: int = 50_000,
    ) -> tuple[tuple, tuple, tuple]:
        """50.000 simulazioni Dixon-Coles. CI 90% bootstrap 20 blocchi."""
        matrix = build_score_matrix(lh, la, rho)
        flat = matrix.flatten()
        indices = np.arange(len(flat))
        block_size = n_sim // 20

        wins_h, draws, wins_a = [], [], []
        for _ in range(20):
            idx = np.random.choice(indices, size=block_size, p=flat)
            rows = idx // matrix.shape[1]
            cols = idx % matrix.shape[1]
            wins_h.append(np.mean(rows > cols))
            draws.append(np.mean(rows == cols))
            wins_a.append(np.mean(cols > rows))

        def ci90(arr):
            arr = np.array(arr)
            return (float(np.percentile(arr, 5)), float(np.percentile(arr, 95)))

        return ci90(wins_h), ci90(draws), ci90(wins_a)

    def _confidence_score(self) -> int:
        score = 100
        if self.hs.n_matches < 5 or self.as_.n_matches < 5:
            score -= 25
        elif self.hs.n_matches < 10 or self.as_.n_matches < 10:
            score -= 10
        if not self.h2h:
            score -= 10
        elif len(self.h2h) < 4:
            score -= 5
        n_inj = len(self.hs.injuries) + len(self.as_.injuries)
        if n_inj > 4:
            score -= 15
        if not self.odds:
            score -= 15
        elif len(self.odds) < 3:
            score -= 8
        # Penalità fonte dati
        if "fallback" in self.hs.data_source or "errore" in self.hs.data_source:
            score -= 10
        if "fallback" in self.as_.data_source or "errore" in self.as_.data_source:
            score -= 10
        return max(0, score)

    def _build_warnings(self, lh: float, la: float, mat: np.ndarray) -> list[str]:
        w = []
        if abs(lh - la) < 0.15:
            w.append("⚠️ Lambda molto simili: risultato incerto")
        if lh < 0.8:
            w.append(f"⚠️ Attacco Casa debole (λ={lh:.2f})")
        if la < 0.8:
            w.append(f"⚠️ Attacco Trasferta debole (λ={la:.2f})")
        if self.hs.n_matches < 5:
            w.append(f"⚠️ Dati insufficienti per {self.hs.name} ({self.hs.n_matches} partite)")
        if self.as_.n_matches < 5:
            w.append(f"⚠️ Dati insufficienti per {self.as_.name} ({self.as_.n_matches} partite)")
        for warn in self.hs.api_warnings + self.as_.api_warnings:
            w.append(f"🔌 {warn}")
        return w

    def _detect_traps(self, markets: dict, lh: float, la: float) -> list[str]:
        traps = []
        # Trappola 1: risultati esatti con prob < 8%
        for score, prob in markets.get("TOP_SCORES", []):
            if prob < 0.08:
                fair_odd = 1 / prob if prob > 0 else 999
                if fair_odd < 8.0:
                    traps.append(f"🪤 Risultato esatto {score}: prob {prob:.1%} ma quota fair {fair_odd:.2f} — margine elevato")

        # Trappola 2: BTTS su due squadre difensive
        if lh < 0.9 and la < 0.9 and markets.get("BTTS", {}).get("Si", 0) > 0.35:
            traps.append("🪤 BTTS Sì: entrambe squadre difensive (λ < 0.9) — alta varianza")

        # Trappola 3: Over 4.5 con lambda basso
        if lh + la < 2.5 and markets.get("OU", {}).get("over_4.5", 0) > 0.10:
            traps.append("🪤 Over 4.5: lambda totale < 2.5 — bet non consigliata")

        # Trappola 4: Long shot con edge apparente ma prob < 15%
        for k, v in markets.get("1X2", {}).items():
            if float(v) < 0.15:
                traps.append(f"🪤 {k}: probabilità {float(v):.1%} < 15% — alta varianza, evita edge apparenti")

        return traps


# ─────────────────────────────────────────────
# HELPER: calcola edge vs bookmaker
# ─────────────────────────────────────────────

def compute_edge(prob: float, bk_odd: float) -> float:
    """Edge = prob_model × quota_BK - 1"""
    if bk_odd <= 0 or prob <= 0:
        return 0.0
    return prob * bk_odd - 1.0


def fair_odd(prob: float) -> float:
    """Quota fair senza margine."""
    return round(1 / prob, 2) if prob > 0.001 else 999.0


def kelly_fraction(prob: float, bk_odd: float, fraction: float = 0.25) -> float:
    """Kelly frazionato (default 25%)."""
    if bk_odd <= 1 or prob <= 0:
        return 0.0
    b = bk_odd - 1
    k = (b * prob - (1 - prob)) / b
    return max(0.0, round(k * fraction, 3))
