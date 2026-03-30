import { Activity } from "lucide-react";
import useWebSocket from "./hooks/useWebSocket";
import MatchTable from "./components/MatchTable";
import StatusBadge from "./components/StatusBadge";

const WS_URL =
  (window.location.protocol === "https:" ? "wss://" : "ws://") +
  window.location.host +
  "/ws";

export default function App() {
  const { data, status } = useWebSocket(WS_URL);

  const matches = data?.matches ?? data?.matches_from_db ?? [];
  const updatedAt = data?.updated_at
    ? new Date(data.updated_at).toLocaleTimeString("tr-TR")
    : "—";

  return (
    <div className="min-h-screen bg-surface text-text-primary">
      {/* Header */}
      <header className="border-b border-border bg-surface-alt/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent/15">
              <Activity size={22} className="text-accent" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">
                Anomali Dashboard
              </h1>
              <p className="text-xs text-text-secondary">
                Basketbol Karar Destek Sistemi
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-xs text-text-secondary">
              Son güncelleme: {updatedAt}
            </span>
            <StatusBadge status={status} />
          </div>
        </div>
      </header>

      {/* Stats Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatCard label="Canlı Maç" value={matches.length} />
          <StatCard
            label="Aktif Sinyal"
            value={matches.filter((m) => m.signal && m.signal !== "NONE").length}
            highlight
          />
          <StatCard
            label="Ort. PPM"
            value={
              matches.length
                ? (
                    matches.reduce((s, m) => s + (m.ppm ?? m.current_ppm ?? 0), 0) /
                    matches.length
                  ).toFixed(2)
                : "—"
            }
          />
          <StatCard label="Bağlantı" value={status === "connected" ? "Aktif" : "Kapalı"} />
        </div>

        {/* Table */}
        <MatchTable matches={matches} />
      </div>
    </div>
  );
}

function StatCard({ label, value, highlight = false }) {
  return (
    <div className="bg-surface-alt border border-border rounded-lg px-4 py-3">
      <div className="text-xs text-text-secondary">{label}</div>
      <div
        className={`text-xl font-bold mt-1 ${
          highlight ? "text-accent" : "text-text-primary"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
