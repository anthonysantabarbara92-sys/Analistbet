import { useState } from "react";
import { Loader2, CheckCircle2, Zap, Globe, Calculator, FileText } from "lucide-react";

const STEPS = [
  { text: "Avviando ricerca web in tempo reale...", type: "search" },
  { text: "Raccogliendo risultati recenti squadra casa...", type: "search" },
  { text: "Raccogliendo risultati recenti squadra trasferta...", type: "search" },
  { text: "Verificando infortuni e squalifiche aggiornati...", type: "search" },
  { text: "Analizzando H2H, classifica e statistiche...", type: "search" },
  { text: "Calcolando distribuzioni Poisson λ...", type: "calc" },
  { text: "Generando probabilità mercati (1X2, O/U, Corner)...", type: "calc" },
  { text: "Completando report analitico...", type: "report" },
];

import { useEffect } from "react";

const StepIcon = ({ type, done, active }) => {
  if (done) return <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 text-green-500" />;
  if (!active) return <div className="w-3.5 h-3.5 flex-shrink-0 rounded-full border border-zinc-700" />;
  return <Loader2 className="w-3.5 h-3.5 flex-shrink-0 animate-spin text-green-400" />;
};

export default function LoadingState() {
  const [currentStep, setCurrentStep] = useState(0);
  const [completed, setCompleted] = useState([]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < STEPS.length - 1) {
          setCompleted((c) => [...c, prev]);
          return prev + 1;
        }
        clearInterval(interval);
        return prev;
      });
    }, 3800);
    return () => clearInterval(interval);
  }, []);

  const progress = Math.round(((currentStep + 1) / STEPS.length) * 100);
  const searchDone = completed.filter((i) => STEPS[i].type === "search").length;

  return (
    <div
      data-testid="loading-state"
      className="flex flex-col items-center justify-center min-h-[70vh] gap-6 px-4"
    >
      {/* Terminal window */}
      <div className="w-full max-w-xl bg-zinc-900 border border-zinc-800 rounded-sm overflow-hidden shadow-2xl">
        {/* Title bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-950">
          <div className="w-3 h-3 rounded-full bg-red-500/70" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
          <div className="w-3 h-3 rounded-full bg-green-500/70" />
          <span className="text-xs text-zinc-500 font-mono ml-2 select-none">
            football-analyzer — ricerca web + analisi Poisson
          </span>
          {searchDone > 0 && (
            <span className="ml-auto flex items-center gap-1 text-[9px] font-mono text-green-600 border border-green-500/20 rounded-sm px-1.5 py-0.5">
              <Globe className="w-2.5 h-2.5" />
              {searchDone}/5 ricerche
            </span>
          )}
        </div>

        {/* Terminal output */}
        <div className="p-5 space-y-2 min-h-[260px]">
          {STEPS.map((step, i) => {
            const isDone = completed.includes(i);
            const isActive = currentStep === i;
            const isPending = i > currentStep;
            return (
              <div
                key={i}
                className={`flex items-center gap-2 text-xs font-mono transition-all duration-300 ${
                  isDone
                    ? "text-green-500"
                    : isActive
                    ? "text-green-300"
                    : "text-zinc-700"
                }`}
              >
                <StepIcon type={step.type} done={isDone} active={isActive} />
                <span>{step.text}</span>
                {isActive && <span className="animate-blink text-green-500 ml-0.5">_</span>}
                {isDone && step.type === "search" && (
                  <span className="ml-auto text-[9px] text-green-700 border border-green-500/10 rounded-sm px-1">
                    web
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Stats bar */}
        <div className="border-t border-zinc-800 bg-zinc-950 px-5 py-3 flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-600">
            <Globe className="w-3 h-3 text-blue-500" />
            <span>Dati web in tempo reale</span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-600">
            <Calculator className="w-3 h-3 text-amber-500" />
            <span>Poisson bivariata</span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-600">
            <FileText className="w-3 h-3 text-purple-500" />
            <span>Report analitico</span>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-xl space-y-2">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
            <Zap className="w-3 h-3 text-green-500" />
            <span>Claude AI + DuckDuckGo Search</span>
          </div>
          <span className="text-xs font-mono text-green-400 font-bold">{progress}%</span>
        </div>
        <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full prob-bar-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <p className="text-xs font-mono text-zinc-600 text-center max-w-sm leading-relaxed">
        Prima raccoglie dati aggiornati dal web (infortuni, risultati recenti, classifica),
        poi calcola la distribuzione Poisson e genera il report. Attendi 60-120 secondi.
      </p>
    </div>
  );
}
