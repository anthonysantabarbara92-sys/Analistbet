import { useForm } from "react-hook-form";
import { Send, Clock, ChevronRight, AlertCircle, Trophy } from "lucide-react";

const LEAGUES = [
  "Serie A",
  "Serie B",
  "Premier League",
  "LaLiga",
  "Bundesliga",
  "Ligue 1",
  "Eredivisie",
  "Primeira Liga",
  "Champions League",
  "Europa League",
  "Conference League",
  "Altro",
];

function InputField({ label, placeholder, registration, error, hint }) {
  return (
    <div className="space-y-1">
      <label className="block text-[10px] font-mono uppercase tracking-widest text-zinc-500">
        {label}
      </label>
      <input
        {...registration}
        placeholder={placeholder}
        autoComplete="off"
        data-testid={`${registration.name}-input`}
        className={`w-full bg-black border rounded-sm p-3 font-mono text-sm text-white placeholder:text-zinc-700 outline-none transition-colors focus:border-green-500 ${
          error ? "border-red-500" : "border-zinc-800"
        }`}
      />
      {error && (
        <p className="text-[10px] text-red-400 font-mono flex items-center gap-1">
          <AlertCircle className="w-3 h-3" /> {error}
        </p>
      )}
      {hint && !error && (
        <p className="text-[10px] text-zinc-600 font-mono">{hint}</p>
      )}
    </div>
  );
}

function HistoryItem({ item, onClick }) {
  const { home, away } = item.match_info || {};
  const ts = item.timestamp ? new Date(item.timestamp) : null;
  const dq = item.result?.data_quality || "—";
  const conf = item.result?.confidence || "—";

  return (
    <button
      onClick={onClick}
      data-testid={`history-item-${(home || "").toLowerCase().replace(/\s/g, "-")}`}
      className="w-full text-left group border border-zinc-800 hover:border-zinc-700 rounded-sm p-3 transition-colors bg-zinc-950 hover:bg-zinc-900"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-mono text-white truncate">
            {home} <span className="text-zinc-600">vs</span> {away}
          </p>
          <p className="text-[10px] text-zinc-600 font-mono mt-0.5">
            {item.match_info?.league} · {item.match_info?.matchday}
          </p>
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-zinc-700 group-hover:text-green-500 flex-shrink-0 mt-0.5 transition-colors" />
      </div>
      <div className="flex items-center gap-3 mt-2">
        <span
          className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-sm ${
            dq === "alta"
              ? "bg-green-500/10 text-green-500"
              : dq === "media"
              ? "bg-yellow-500/10 text-yellow-500"
              : "bg-red-500/10 text-red-400"
          }`}
        >
          {dq}
        </span>
        <span className="text-[10px] font-mono text-zinc-500">
          Conf: {conf}%
        </span>
        {ts && (
          <span className="text-[10px] font-mono text-zinc-700 ml-auto">
            {ts.toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit" })}
          </span>
        )}
      </div>
    </button>
  );
}

export default function MatchForm({ onAnalyze, error, history, onLoadHistory }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in-up">
      {/* Main form — 2 columns */}
      <div className="lg:col-span-2 space-y-4">
        {/* Header card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-5">
          <div className="flex items-center gap-2 mb-1">
            <Trophy className="w-4 h-4 text-green-500" />
            <h2 className="text-xs font-mono uppercase tracking-widest text-zinc-300 font-semibold">
              Inserisci Partita
            </h2>
          </div>
          <p className="text-[11px] text-zinc-600 font-mono">
            Compila i campi per avviare l'analisi AI con calcolo Poisson completo
          </p>
        </div>

        {/* Form card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-5">
          <form
            onSubmit={handleSubmit(onAnalyze)}
            data-testid="match-analysis-form"
            className="space-y-4"
          >
            {/* Teams row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <InputField
                label="Squadra Casa"
                placeholder="es. Juventus"
                registration={register("home", {
                  required: "Campo obbligatorio",
                  minLength: { value: 2, message: "Minimo 2 caratteri" },
                })}
                error={errors.home?.message}
              />
              <InputField
                label="Squadra Trasferta"
                placeholder="es. Milan"
                registration={register("away", {
                  required: "Campo obbligatorio",
                  minLength: { value: 2, message: "Minimo 2 caratteri" },
                })}
                error={errors.away?.message}
              />
            </div>

            {/* League + Matchday row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="block text-[10px] font-mono uppercase tracking-widest text-zinc-500">
                  Campionato
                </label>
                <select
                  {...register("league", { required: "Campo obbligatorio" })}
                  data-testid="league-select"
                  className={`w-full bg-black border rounded-sm p-3 font-mono text-sm text-white outline-none transition-colors focus:border-green-500 cursor-pointer ${
                    errors.league ? "border-red-500" : "border-zinc-800"
                  }`}
                >
                  <option value="" className="bg-zinc-900">
                    Seleziona campionato...
                  </option>
                  {LEAGUES.map((l) => (
                    <option key={l} value={l} className="bg-zinc-900">
                      {l}
                    </option>
                  ))}
                </select>
                {errors.league && (
                  <p className="text-[10px] text-red-400 font-mono flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> {errors.league.message}
                  </p>
                )}
              </div>

              <InputField
                label="Giornata / Data"
                placeholder="es. Giornata 29 / 15 Mar 2025"
                registration={register("matchday", {
                  required: "Campo obbligatorio",
                })}
                error={errors.matchday?.message}
                hint="Giornata o data prevista della partita"
              />
            </div>

            {/* Error */}
            {error && (
              <div
                data-testid="analysis-error"
                className="flex items-start gap-2 bg-red-500/10 border border-red-500/20 rounded-sm p-3"
              >
                <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs font-mono text-red-400">{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              data-testid="analyze-submit-btn"
              className="w-full bg-green-500 hover:bg-green-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-black font-mono font-bold text-sm uppercase tracking-widest rounded-sm py-3.5 transition-colors flex items-center justify-center gap-2 active:scale-[0.98]"
            >
              {isSubmitting ? (
                <>
                  <span className="animate-spin">⟳</span>
                  Elaborazione...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Avvia Analisi AI
                </>
              )}
            </button>
          </form>
        </div>

        {/* Info card */}
        <div className="border border-zinc-800/50 rounded-sm p-4 bg-zinc-900/30">
          <p className="text-[10px] font-mono text-zinc-600 leading-relaxed">
            <span className="text-zinc-500">NOTA:</span> Il modello AI analizza usando la sua
            base di conoscenza aggiornata su campionati europei e mondiali. Per partite con dati
            scarsi, il campo <span className="text-yellow-500">data_quality</span> rifletterà la
            confidenza dell'analisi.
          </p>
        </div>
      </div>

      {/* History sidebar */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-4 h-fit">
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-zinc-800">
          <Clock className="w-3.5 h-3.5 text-zinc-500" />
          <h3 className="text-[10px] font-mono uppercase tracking-widest text-zinc-500 font-semibold">
            Analisi Recenti
          </h3>
          {history.length > 0 && (
            <span className="ml-auto text-[10px] font-mono text-zinc-700">
              {history.length}
            </span>
          )}
        </div>

        {history.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-[11px] font-mono text-zinc-700">
              Nessuna analisi ancora
            </p>
            <p className="text-[10px] font-mono text-zinc-800 mt-1">
              Le analisi salvate appariranno qui
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {history.slice(0, 10).map((item, idx) => (
              <HistoryItem
                key={item.id || idx}
                item={item}
                onClick={() => onLoadHistory(item)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
