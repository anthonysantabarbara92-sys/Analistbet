import { useState, useEffect } from "react";
import { Loader2, CheckCircle2, Zap } from "lucide-react";

const STEPS = [
  "Raccogliendo dati squadra casa...",
  "Raccogliendo dati squadra trasferta...",
  "Analizzando scontri diretti (H2H)...",
  "Verificando infortuni e squalifiche...",
  "Analizzando motivazione e calendario...",
  "Calcolando distribuzioni Poisson...",
  "Generando probabilità mercati...",
  "Completando report analitico...",
];

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
    }, 3500);
    return () => clearInterval(interval);
  }, []);

  const progress = Math.round(((currentStep + 1) / STEPS.length) * 100);

  return (
    <div
      data-testid="loading-state"
      className="flex flex-col items-center justify-center min-h-[70vh] gap-6 px-4"
    >
      {/* Terminal window */}
      <div className="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-sm overflow-hidden shadow-2xl">
        {/* Title bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-950">
          <div className="w-3 h-3 rounded-full bg-red-500/70" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
          <div className="w-3 h-3 rounded-full bg-green-500/70" />
          <span className="text-xs text-zinc-500 font-mono ml-2 select-none">
            football-analyzer — analisi in corso
          </span>
        </div>

        {/* Terminal output */}
        <div className="p-5 space-y-2 min-h-[220px]">
          {completed.map((i) => (
            <div
              key={i}
              className="flex items-center gap-2 text-xs font-mono text-green-500 animate-fade-in-up"
            >
              <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
              <span>{STEPS[i]}</span>
            </div>
          ))}
          {currentStep < STEPS.length && (
            <div className="flex items-center gap-2 text-xs font-mono text-green-300 animate-fade-in-up">
              <Loader2 className="w-3.5 h-3.5 flex-shrink-0 animate-spin" />
              <span>{STEPS[currentStep]}</span>
              <span className="animate-blink text-green-500">_</span>
            </div>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-lg space-y-2">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
            <Zap className="w-3 h-3 text-green-500" />
            <span>Claude AI in elaborazione</span>
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

      <p className="text-xs font-mono text-zinc-600 text-center max-w-sm">
        L'analisi completa richiede 30-90 secondi. Il modello AI sta elaborando
        statistiche, calcoli Poisson e report analitico.
      </p>
    </div>
  );
}
