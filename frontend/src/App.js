import { useState, useEffect } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster, toast } from "sonner";
import MatchForm from "@/components/MatchForm";
import AnalysisResults from "@/components/AnalysisResults";
import LoadingState from "@/components/LoadingState";
import { Target, Activity } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function Header({ onNewAnalysis, phase }) {
  return (
    <header className="border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-sm sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-green-500 rounded-sm flex items-center justify-center">
            <Target className="w-4 h-4 text-black" />
          </div>
          <div>
            <h1 className="text-sm font-mono font-bold text-white uppercase tracking-widest leading-none">
              Analizzatore Calcistico <span className="text-green-400">Pro</span>
            </h1>
            <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-widest mt-0.5">
              AI Pricing Engine — Powered by Claude
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {phase === "results" && (
            <button
              data-testid="new-analysis-btn-header"
              onClick={onNewAnalysis}
              className="text-xs font-mono uppercase tracking-widest text-zinc-400 hover:text-green-400 transition-colors border border-zinc-800 hover:border-green-500/50 rounded-sm px-3 py-1.5"
            >
              Nuova Analisi
            </button>
          )}
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-600 border border-zinc-800 rounded-sm px-2 py-1">
            <Activity className="w-3 h-3 text-green-500" />
            <span>LIVE</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function App() {
  const [phase, setPhase] = useState("form");
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await axios.get(`${API}/analyses`);
      setHistory(res.data || []);
    } catch {
      // silent fail
    }
  };

  const handleAnalyze = async (formData) => {
    setPhase("loading");
    setError(null);
    try {
      const res = await axios.post(`${API}/analyze`, formData, {
        timeout: 180000,
      });
      setAnalysis(res.data);
      setPhase("results");
      toast.success("Analisi completata con successo!");
      loadHistory();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Errore durante l'analisi";
      setError(msg);
      setPhase("form");
      toast.error("Errore nell'analisi: " + msg);
    }
  };

  const handleNewAnalysis = () => {
    setPhase("form");
    setAnalysis(null);
    setError(null);
  };

  const handleRecalculate = async () => {
    if (!analysis?.match_info) return;
    toast.info("Ricalcolo con dati web aggiornati...");
    await handleAnalyze(analysis.match_info);
  };

  const handleLoadHistory = (item) => {
    setAnalysis(item.result);
    setPhase("results");
  };

  return (
    <div className="dark min-h-screen bg-zinc-950 text-zinc-100">
      <Toaster theme="dark" position="top-right" richColors />
      <Header onNewAnalysis={handleNewAnalysis} phase={phase} />
      <main className="max-w-7xl mx-auto px-4 py-6">
        {phase === "form" && (
          <MatchForm
            onAnalyze={handleAnalyze}
            error={error}
            history={history}
            onLoadHistory={handleLoadHistory}
          />
        )}
        {phase === "loading" && <LoadingState />}
        {phase === "results" && analysis && (
          <AnalysisResults
            analysis={analysis}
            onNewAnalysis={handleNewAnalysis}
            onRecalculate={handleRecalculate}
          />
        )}
      </main>
    </div>
  );
}

export default App;
