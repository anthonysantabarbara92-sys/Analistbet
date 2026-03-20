import { useState } from "react";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  Zap,
  Target,
  AlertTriangle,
  BarChart2,
  FileText,
  ChevronDown,
  ChevronUp,
  Shield,
  Crosshair,
  Activity,
} from "lucide-react";

// ── Utility helpers ──────────────────────────────────────────────────────────
const pct = (v) => (typeof v === "number" ? (v * 100).toFixed(1) + "%" : "—");
const toFixed2 = (v) => (typeof v === "number" ? v.toFixed(2) : "—");

function getFormColor(char) {
  const c = char?.toUpperCase();
  if (c === "V" || c === "W") return "#22c55e";
  if (c === "P" || c === "D") return "#f59e0b";
  if (c === "S" || c === "L") return "#ef4444";
  return "#52525b";
}

function FormDisplay({ formStr }) {
  if (!formStr || formStr === "dato non disponibile") {
    return <span className="text-zinc-600 text-xs font-mono">N/D</span>;
  }
  const tokens = formStr
    .toUpperCase()
    .split(/[-\s,]+/)
    .filter(Boolean)
    .slice(0, 6);
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {tokens.map((t, i) => (
        <span
          key={i}
          className="w-6 h-6 rounded-sm flex items-center justify-center text-[10px] font-mono font-bold text-black"
          style={{ backgroundColor: getFormColor(t[0]) }}
        >
          {t[0]}
        </span>
      ))}
    </div>
  );
}

function ProbBar({ label, value, color = "#22c55e", bgColor = "#1a1a1a" }) {
  const pctVal = typeof value === "number" ? value * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">
          {label}
        </span>
        <span
          className="text-xs font-mono font-bold"
          style={{ color }}
        >
          {pct(value)}
        </span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: bgColor }}>
        <div
          className="h-full rounded-full prob-bar-fill"
          style={{ width: `${pctVal}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function SectionTitle({ icon: Icon, title, subtitle }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-6 h-6 bg-zinc-800 rounded-sm flex items-center justify-center flex-shrink-0">
        <Icon className="w-3.5 h-3.5 text-green-400" />
      </div>
      <div>
        <h3 className="text-[10px] font-mono uppercase tracking-widest text-zinc-400 font-semibold">
          {title}
        </h3>
        {subtitle && (
          <p className="text-[9px] font-mono text-zinc-700">{subtitle}</p>
        )}
      </div>
    </div>
  );
}

function DataQualityBadge({ quality }) {
  const cfg = {
    alta: { label: "Alta", cls: "bg-green-500/10 text-green-500 border-green-500/20" },
    media: { label: "Media", cls: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20" },
    bassa: { label: "Bassa", cls: "bg-red-500/10 text-red-400 border-red-500/20" },
  };
  const q = (quality || "").toLowerCase();
  const { label, cls } = cfg[q] || cfg["bassa"];
  return (
    <span
      className={`text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 rounded-sm border ${cls}`}
    >
      {label}
    </span>
  );
}

// ── SECTION: Match Header ─────────────────────────────────────────────────────
function MatchHeader({ match_info, confidence, data_quality, onNewAnalysis }) {
  return (
    <div
      data-testid="match-header"
      className="bg-zinc-900 border border-zinc-800 rounded-sm p-5 animate-fade-in-up stagger-1"
    >
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-[10px] font-mono uppercase tracking-widest text-zinc-500 border border-zinc-800 px-2 py-0.5 rounded-sm">
              {match_info?.league}
            </span>
            <span className="text-[10px] font-mono text-zinc-600">
              {match_info?.matchday}
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-mono font-bold text-white tracking-tight">
            <span className="text-green-400">{match_info?.home}</span>
            <span className="text-zinc-600 mx-3 text-xl">vs</span>
            <span className="text-blue-400">{match_info?.away}</span>
          </h2>
        </div>

        <div className="flex items-center gap-4 flex-shrink-0">
          {/* Confidence */}
          <div
            data-testid="confidence-score"
            className="text-center border border-zinc-800 rounded-sm px-4 py-2"
          >
            <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 mb-0.5">
              Fiducia
            </p>
            <p
              className="text-2xl font-mono font-bold"
              style={{
                color:
                  confidence >= 70
                    ? "#22c55e"
                    : confidence >= 50
                    ? "#f59e0b"
                    : "#ef4444",
              }}
            >
              {confidence}%
            </p>
          </div>

          {/* Data quality */}
          <div className="text-center">
            <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 mb-1">
              Qualità Dati
            </p>
            <DataQualityBadge quality={data_quality} />
          </div>
        </div>
      </div>

      <button
        onClick={onNewAnalysis}
        data-testid="back-to-form-btn"
        className="mt-4 flex items-center gap-1.5 text-xs font-mono text-zinc-600 hover:text-zinc-300 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Nuova analisi
      </button>
    </div>
  );
}

// ── SECTION: Context ──────────────────────────────────────────────────────────
function ContextSection({ context, home, away }) {
  return (
    <div
      data-testid="context-section"
      className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 animate-fade-in-up stagger-2"
    >
      {/* Form */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-4">
        <SectionTitle icon={Activity} title="Forma Recente" />
        <div className="space-y-3">
          <div>
            <p className="text-[10px] font-mono text-zinc-500 mb-1.5 flex items-center gap-1">
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ backgroundColor: "#22c55e" }}
              />
              {home}
            </p>
            <FormDisplay formStr={context?.form_home} />
          </div>
          <div>
            <p className="text-[10px] font-mono text-zinc-500 mb-1.5 flex items-center gap-1">
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ backgroundColor: "#3b82f6" }}
              />
              {away}
            </p>
            <FormDisplay formStr={context?.form_away} />
          </div>
        </div>
      </div>

      {/* H2H */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-4">
        <SectionTitle icon={Crosshair} title="Testa a Testa" subtitle="Ultimi scontri diretti" />
        <p className="text-xs text-zinc-400 leading-relaxed">
          {context?.h2h || "dato non disponibile"}
        </p>
      </div>

      {/* Key Factor */}
      <div className="bg-zinc-900 border border-green-500/20 rounded-sm p-4 glow-green">
        <SectionTitle icon={Zap} title="Fattore Chiave" />
        <p className="text-sm text-green-300 font-medium leading-relaxed">
          {context?.key_factor || "dato non disponibile"}
        </p>
      </div>

      {/* Infortuni Casa */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-4">
        <SectionTitle
          icon={Shield}
          title="Infortuni / Squalifiche"
          subtitle={home}
        />
        {!context?.injuries_home || context.injuries_home.length === 0 ? (
          <p className="text-xs text-zinc-600 font-mono">Nessun infortunio noto</p>
        ) : (
          <ul className="space-y-1">
            {context.injuries_home.map((inj, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-red-400 mt-0.5 flex-shrink-0">•</span>
                <span className="text-xs text-zinc-400 font-mono">{inj}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Infortuni Trasferta */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-4">
        <SectionTitle
          icon={Shield}
          title="Infortuni / Squalifiche"
          subtitle={away}
        />
        {!context?.injuries_away || context.injuries_away.length === 0 ? (
          <p className="text-xs text-zinc-600 font-mono">Nessun infortunio noto</p>
        ) : (
          <ul className="space-y-1">
            {context.injuries_away.map((inj, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-red-400 mt-0.5 flex-shrink-0">•</span>
                <span className="text-xs text-zinc-400 font-mono">{inj}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Motivazione + Stanchezza + Arbitro */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-4 space-y-3">
        <SectionTitle icon={TrendingUp} title="Contesto" />
        <div>
          <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 mb-0.5">
            Motivazione {home}
          </p>
          <p className="text-xs text-zinc-400">{context?.motivation_home || "N/D"}</p>
        </div>
        <div>
          <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 mb-0.5">
            Motivazione {away}
          </p>
          <p className="text-xs text-zinc-400">{context?.motivation_away || "N/D"}</p>
        </div>
        <div>
          <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 mb-0.5">
            Stanchezza
          </p>
          <p className="text-xs text-zinc-400">{context?.fatigue || "N/D"}</p>
        </div>
        <div>
          <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 mb-0.5">
            Arbitro
          </p>
          <p className="text-xs text-zinc-400">{context?.referee || "N/D"}</p>
        </div>
      </div>
    </div>
  );
}

// ── SECTION: Poisson ──────────────────────────────────────────────────────────
function PoissonSection({ poisson }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      data-testid="poisson-section"
      className="bg-zinc-900 border border-zinc-800 rounded-sm p-5 animate-fade-in-up stagger-3"
    >
      <SectionTitle
        icon={BarChart2}
        title="Parametri Poisson"
        subtitle="Distribuzioni calcolate dal modello AI"
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <div
          data-testid="lambda-home"
          className="text-center border border-zinc-800 rounded-sm p-4"
        >
          <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 mb-1">
            λ Casa
          </p>
          <p className="text-4xl font-mono font-bold text-green-400">
            {toFixed2(poisson?.lambda_home)}
          </p>
          <p className="text-[9px] font-mono text-zinc-700 mt-1">gol attesi</p>
        </div>

        <div
          data-testid="lambda-away"
          className="text-center border border-zinc-800 rounded-sm p-4"
        >
          <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 mb-1">
            λ Trasferta
          </p>
          <p className="text-4xl font-mono font-bold text-blue-400">
            {toFixed2(poisson?.lambda_away)}
          </p>
          <p className="text-[9px] font-mono text-zinc-700 mt-1">gol attesi</p>
        </div>

        <div className="text-center border border-zinc-800 rounded-sm p-4">
          <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 mb-1">
            λ Corner
          </p>
          <p className="text-4xl font-mono font-bold text-amber-400">
            {toFixed2(poisson?.total_corners)}
          </p>
          <p className="text-[9px] font-mono text-zinc-700 mt-1">corner attesi</p>
        </div>
      </div>

      {/* Reasoning expandable */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-zinc-600 hover:text-zinc-400 transition-colors border border-zinc-800 rounded-sm px-3 py-2"
      >
        <span>Ragionamento e rettifiche</span>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </button>

      {expanded && (
        <div className="mt-3 bg-zinc-950 border border-zinc-800 rounded-sm p-4">
          <p className="text-xs font-mono text-zinc-400 leading-relaxed whitespace-pre-wrap">
            {poisson?.reasoning || "dato non disponibile"}
          </p>
        </div>
      )}
    </div>
  );
}

// ── SECTION: 1X2 Result Market ────────────────────────────────────────────────
function ResultMarket({ result, home, away }) {
  const { home_win = 0, draw = 0, away_win = 0 } = result || {};
  const max = Math.max(home_win, draw, away_win);

  const items = [
    { label: `${home} vince`, value: home_win, color: "#22c55e" },
    { label: "Pareggio", value: draw, color: "#f59e0b" },
    { label: `${away} vince`, value: away_win, color: "#3b82f6" },
  ];

  return (
    <div
      data-testid="result-market"
      className="bg-zinc-900 border border-zinc-800 rounded-sm p-5"
    >
      <SectionTitle icon={Target} title="Mercato 1X2" subtitle="Probabilità risultato finale" />
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.label} className={item.value === max ? "ring-1 ring-offset-2 ring-offset-zinc-900 rounded-sm" : ""} style={item.value === max ? { ringColor: item.color } : {}}>
            <ProbBar
              label={item.label}
              value={item.value}
              color={item.color}
              bgColor="#27272a"
            />
          </div>
        ))}
      </div>
      <p className="text-[9px] font-mono text-zinc-700 mt-3 text-right">
        Somma: {((home_win + draw + away_win) * 100).toFixed(1)}%
      </p>
    </div>
  );
}

// ── SECTION: Over/Under Table ─────────────────────────────────────────────────
function OverUnderTable({ over_under }) {
  const rows = [
    {
      label: "1.5",
      over: over_under?.over_1_5,
      under: over_under?.under_1_5,
    },
    {
      label: "2.5",
      over: over_under?.over_2_5,
      under: over_under?.under_2_5,
    },
    {
      label: "3.5",
      over: over_under?.over_3_5,
      under: over_under?.under_3_5,
    },
  ];

  return (
    <div
      data-testid="over-under-market"
      className="bg-zinc-900 border border-zinc-800 rounded-sm p-5"
    >
      <SectionTitle
        icon={TrendingUp}
        title="Over / Under"
        subtitle="Probabilità gol totali"
      />
      <table className="w-full">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 pb-2 text-left">
              Mercato
            </th>
            <th className="text-[9px] font-mono uppercase tracking-widest text-green-600 pb-2 text-right">
              Over
            </th>
            <th className="text-[9px] font-mono uppercase tracking-widest text-red-600 pb-2 text-right">
              Under
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-zinc-800/50">
              <td className="py-2 text-sm font-mono font-bold text-white">
                {r.label}
              </td>
              <td className="py-2 text-right">
                <span
                  className={`text-sm font-mono font-bold ${
                    (r.over || 0) > 0.5 ? "text-green-400" : "text-zinc-400"
                  }`}
                >
                  {pct(r.over)}
                </span>
              </td>
              <td className="py-2 text-right">
                <span
                  className={`text-sm font-mono font-bold ${
                    (r.under || 0) > 0.5 ? "text-red-400" : "text-zinc-400"
                  }`}
                >
                  {pct(r.under)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── SECTION: Multigoal ────────────────────────────────────────────────────────
function MultigoalCard({ data, label }) {
  const items = [
    { k: "0", l: "0 gol" },
    { k: "1", l: "1 gol" },
    { k: "2", l: "2 gol" },
    { k: "3plus", l: "3+ gol" },
  ];
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-4">
      <p className="text-[9px] font-mono uppercase tracking-widest text-zinc-500 mb-3">
        {label}
      </p>
      <div className="space-y-2">
        {items.map((item) => (
          <ProbBar
            key={item.k}
            label={item.l}
            value={data?.[item.k]}
            color="#a78bfa"
            bgColor="#27272a"
          />
        ))}
      </div>
    </div>
  );
}

// ── SECTION: Corners ─────────────────────────────────────────────────────────
function CornersTable({ corners }) {
  const rows = [
    { label: "7.5", over: corners?.over_7_5, under: corners?.under_7_5 },
    { label: "8.5", over: corners?.over_8_5, under: corners?.under_8_5 },
    { label: "9.5", over: corners?.over_9_5, under: corners?.under_9_5 },
    { label: "10.5", over: corners?.over_10_5, under: corners?.under_10_5 },
  ];

  return (
    <div
      data-testid="corners-market"
      className="bg-zinc-900 border border-zinc-800 rounded-sm p-5"
    >
      <SectionTitle
        icon={Activity}
        title="Corner Over / Under"
        subtitle="Distribuzione corner totali"
      />
      <table className="w-full">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 pb-2 text-left">
              Linea
            </th>
            <th className="text-[9px] font-mono uppercase tracking-widest text-amber-600 pb-2 text-right">
              Over
            </th>
            <th className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 pb-2 text-right">
              Under
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-zinc-800/50">
              <td className="py-2 text-sm font-mono font-bold text-white">
                {r.label}
              </td>
              <td className="py-2 text-right">
                <span
                  className={`text-sm font-mono font-bold ${
                    (r.over || 0) > 0.5 ? "text-amber-400" : "text-zinc-400"
                  }`}
                >
                  {pct(r.over)}
                </span>
              </td>
              <td className="py-2 text-right">
                <span className="text-sm font-mono font-bold text-zinc-400">
                  {pct(r.under)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── SECTION: Exact Scores ─────────────────────────────────────────────────────
function ExactScoresSection({ exact_scores }) {
  if (!exact_scores || exact_scores.length === 0) return null;

  const maxProb = Math.max(...exact_scores.map((s) => s.prob || 0));

  return (
    <div
      data-testid="exact-scores-section"
      className="bg-zinc-900 border border-zinc-800 rounded-sm p-5 animate-fade-in-up stagger-6"
    >
      <SectionTitle
        icon={Crosshair}
        title="Risultati Esatti"
        subtitle="Top 8 punteggi per probabilità Poisson"
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {exact_scores.slice(0, 8).map((s, i) => {
          const isTop = s.prob === maxProb;
          const probPct = ((s.prob || 0) * 100).toFixed(1);
          return (
            <div
              key={i}
              data-testid={`exact-score-${s.score}`}
              className={`relative border rounded-sm p-3 text-center transition-colors ${
                isTop
                  ? "border-green-500/40 bg-green-500/5 glow-green"
                  : "border-zinc-800 bg-zinc-950"
              }`}
            >
              {isTop && (
                <span className="absolute -top-2 left-1/2 -translate-x-1/2 text-[8px] font-mono uppercase tracking-widest bg-green-500 text-black px-1.5 rounded-sm">
                  TOP
                </span>
              )}
              <p className="text-xl font-mono font-bold text-white mt-1">
                {s.score}
              </p>
              <p
                className={`text-sm font-mono font-bold mt-0.5 ${
                  isTop ? "text-green-400" : "text-zinc-400"
                }`}
              >
                {probPct}%
              </p>
              {s.note && (
                <p className="text-[9px] text-zinc-600 font-mono mt-1 leading-tight">
                  {s.note}
                </p>
              )}
              <p className="text-[9px] font-mono text-zinc-700 mt-0.5">
                #{i + 1}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── SECTION: Analyst Report ───────────────────────────────────────────────────
function AnalystReport({ report }) {
  return (
    <div
      data-testid="analyst-report"
      className="bg-zinc-900 border border-zinc-800 rounded-sm p-5 animate-fade-in-up stagger-7"
    >
      <SectionTitle
        icon={FileText}
        title="Report Analitico"
        subtitle="Valutazione professionale del trading desk"
      />

      <div className="bg-zinc-950 border border-zinc-800 rounded-sm p-5">
        <p className="text-sm font-mono text-zinc-300 leading-relaxed whitespace-pre-wrap terminal-cursor">
          {report || "Report non disponibile"}
        </p>
      </div>
    </div>
  );
}

// ── SECTION: Data Gaps ────────────────────────────────────────────────────────
function DataGapsSection({ data_gaps }) {
  if (!data_gaps || data_gaps.length === 0) return null;

  return (
    <div
      data-testid="data-gaps-section"
      className="bg-zinc-900/50 border border-yellow-500/10 rounded-sm p-4 animate-fade-in-up stagger-8"
    >
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-3.5 h-3.5 text-yellow-500" />
        <p className="text-[10px] font-mono uppercase tracking-widest text-yellow-600">
          Lacune nei Dati
        </p>
      </div>
      <ul className="space-y-1">
        {data_gaps.map((gap, i) => (
          <li key={i} className="flex items-start gap-1.5">
            <span className="text-yellow-600 mt-0.5">•</span>
            <span className="text-xs font-mono text-zinc-500">{gap}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── MAIN EXPORT ───────────────────────────────────────────────────────────────
export default function AnalysisResults({ analysis, onNewAnalysis }) {
  const {
    match_info,
    context,
    poisson,
    markets,
    exact_scores,
    analyst_report,
    confidence,
    data_quality,
    data_gaps,
  } = analysis || {};

  const home = match_info?.home || "Casa";
  const away = match_info?.away || "Trasferta";

  return (
    <div data-testid="analysis-results" className="space-y-4 pb-12">
      {/* Header */}
      <MatchHeader
        match_info={match_info}
        confidence={confidence}
        data_quality={data_quality}
        onNewAnalysis={onNewAnalysis}
      />

      {/* Context grid */}
      <ContextSection context={context} home={home} away={away} />

      {/* Poisson */}
      <PoissonSection poisson={poisson} />

      {/* Markets row */}
      <div
        data-testid="markets-section"
        className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 animate-fade-in-up stagger-4"
      >
        <ResultMarket result={markets?.result} home={home} away={away} />
        <OverUnderTable over_under={markets?.over_under} />
        <CornersTable corners={markets?.corners} />
      </div>

      {/* Multigoal row */}
      <div
        data-testid="multigoal-section"
        className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-in-up stagger-5"
      >
        <MultigoalCard data={markets?.multigoal_home} label={`Multigoal ${home}`} />
        <MultigoalCard data={markets?.multigoal_away} label={`Multigoal ${away}`} />
      </div>

      {/* Exact scores */}
      <ExactScoresSection exact_scores={exact_scores} />

      {/* Analyst report */}
      <AnalystReport report={analyst_report} />

      {/* Data gaps */}
      <DataGapsSection data_gaps={data_gaps} />

      {/* Footer action */}
      <div className="flex justify-center pt-4">
        <button
          onClick={onNewAnalysis}
          data-testid="new-analysis-bottom-btn"
          className="bg-zinc-800 hover:bg-zinc-700 text-white font-mono font-bold text-sm uppercase tracking-widest rounded-sm px-8 py-3 transition-colors flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Nuova Analisi
        </button>
      </div>
    </div>
  );
}
