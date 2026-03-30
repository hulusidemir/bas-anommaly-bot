import SignalBadge from "./SignalBadge";
import { ExternalLink } from "lucide-react";

function fmt(v, decimals = 1) {
  if (v == null) return "—";
  return Number(v).toFixed(decimals);
}

export default function MatchTable({ matches }) {
  if (!matches || matches.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-text-secondary text-sm">
        Canlı maç verisi bekleniyor…
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="bg-surface-alt text-text-secondary text-xs uppercase tracking-wider">
            <th className="px-4 py-3 font-semibold">Maç / Dakika</th>
            <th className="px-4 py-3 font-semibold text-center">Anlık Skor</th>
            <th className="px-4 py-3 font-semibold text-center">PPM (Mevcut / Hedef)</th>
            <th className="px-4 py-3 font-semibold text-center">Barem (Açılış / Canlı)</th>
            <th className="px-4 py-3 font-semibold text-center">Adil Barem</th>
            <th className="px-4 py-3 font-semibold text-center">Δ</th>
            <th className="px-4 py-3 font-semibold text-center">Sinyal</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {matches.map((m) => {
            const liveLine = m.live_line ?? m.live_total_odds ?? 0;
            const opening = m.opening_line ?? m.opening_total ?? 0;
            const score = m.total_score ?? m.current_score ?? 0;
            const ppm = m.ppm ?? m.current_ppm ?? 0;
            const target = m.target_ppm ?? null;
            const fairVal = m.fair_value ?? 0;
            const deltaAbs = Math.abs(fairVal - liveLine);
            const matchName = m.match_name ?? `${m.home_team ?? "?"} vs ${m.away_team ?? "?"}`;
            const timeDisplay = m.quarter_display ?? `${fmt(m.elapsed_minutes ?? m.played_minutes, 0)} dk`;
            const sofascoreUrl = m.sofascore_url || null;

            return (
              <tr
                key={m.match_id}
                className={`hover:bg-surface-hover transition-colors ${sofascoreUrl ? "cursor-pointer" : ""}`}
                onClick={() => sofascoreUrl && window.open(sofascoreUrl, "_blank", "noopener")}
              >
                {/* Maç / Dakika */}
                <td className="px-4 py-3">
                  <div className="font-medium text-text-primary flex items-center gap-1.5">
                    {matchName}
                    {sofascoreUrl && (
                      <ExternalLink size={12} className="text-text-secondary shrink-0" />
                    )}
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">{timeDisplay}</div>
                </td>

                {/* Skor */}
                <td className="px-4 py-3 text-center font-mono font-semibold text-lg text-text-primary">
                  {m.home_score != null
                    ? `${m.home_score} - ${m.away_score}`
                    : score}
                </td>

                {/* PPM */}
                <td className="px-4 py-3 text-center font-mono">
                  <span className="text-text-primary">{fmt(ppm, 2)}</span>
                  <span className="text-text-secondary"> / </span>
                  <span className={target != null && target > ppm * 1.4 ? "text-red font-semibold" : "text-text-secondary"}>
                    {fmt(target, 2)}
                  </span>
                </td>

                {/* Barem */}
                <td className="px-4 py-3 text-center font-mono">
                  <span className="text-text-secondary">{fmt(opening)}</span>
                  <span className="text-text-secondary"> / </span>
                  <span className="text-text-primary">{fmt(liveLine)}</span>
                </td>

                {/* Adil Barem */}
                <td className="px-4 py-3 text-center">
                  <span className="text-xl font-bold text-accent">
                    {fmt(fairVal)}
                  </span>
                </td>

                {/* Delta */}
                <td className="px-4 py-3 text-center font-mono">
                  <span className={deltaAbs > 8.5 ? "text-amber font-semibold" : "text-text-secondary"}>
                    {(fairVal - liveLine) >= 0 ? "+" : ""}{fmt(fairVal - liveLine)}
                  </span>
                </td>

                {/* Sinyal */}
                <td className="px-4 py-3 text-center">
                  <SignalBadge match={{ ...m, live_line: liveLine }} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
