import { TrendingDown, TrendingUp, AlertTriangle, CheckCircle, MinusCircle } from "lucide-react";

const DELTA_THRESHOLD = 8.5;

function getSignalInfo(match) {
  const { signal, delta, fair_value, live_line, live_total_odds } = match;

  const liveLine = live_line ?? live_total_odds ?? 0;
  const gap = liveLine > 0 ? Math.abs((fair_value ?? 0) - liveLine) : 0;

  if (signal === "PACE_DROP") {
    return { icon: TrendingDown, color: "text-red", bg: "bg-red/10", label: "Aşırı Hız" };
  }
  if (signal === "VALUE_GAP") {
    return { icon: AlertTriangle, color: "text-amber", bg: "bg-amber/10", label: "Barem Sapması" };
  }
  if (signal === "SCORING_DROUGHT") {
    return { icon: MinusCircle, color: "text-red", bg: "bg-red/10", label: "Kilitlenme" };
  }
  if (gap > DELTA_THRESHOLD) {
    return { icon: AlertTriangle, color: "text-amber", bg: "bg-amber/10", label: "Fark Yüksek" };
  }
  return { icon: CheckCircle, color: "text-green", bg: "bg-green/10", label: "Normal" };
}

export default function SignalBadge({ match }) {
  const { icon: Icon, color, bg, label } = getSignalInfo(match);

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${color} ${bg}`}>
      <Icon size={14} />
      {label}
    </span>
  );
}
