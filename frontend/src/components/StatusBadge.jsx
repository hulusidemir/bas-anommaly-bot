import { Wifi, WifiOff, RefreshCw } from "lucide-react";

const labels = {
  connected: "Bağlı",
  disconnected: "Bağlantı Kesildi",
  reconnecting: "Yeniden Bağlanıyor…",
};

const icons = {
  connected: Wifi,
  disconnected: WifiOff,
  reconnecting: RefreshCw,
};

const colors = {
  connected: "text-green",
  disconnected: "text-red",
  reconnecting: "text-amber",
};

export default function StatusBadge({ status }) {
  const Icon = icons[status] || WifiOff;
  const color = colors[status] || "text-red";
  const label = labels[status] || status;

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${color}`}>
      <Icon size={14} className={status === "reconnecting" ? "animate-spin" : ""} />
      {label}
    </span>
  );
}
