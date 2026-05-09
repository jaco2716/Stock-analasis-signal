export const formatDKK = (n: number | null | undefined): string =>
  n == null
    ? "—"
    : new Intl.NumberFormat("da-DK", {
        style: "currency",
        currency: "DKK",
        maximumFractionDigits: 0,
      }).format(n);

export const formatPercent = (n: number): string =>
  new Intl.NumberFormat("da-DK", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(n);

export const formatQuantity = (n: number | null | undefined): string => {
  if (n == null) return "—";
  return new Intl.NumberFormat("da-DK", { maximumFractionDigits: 4 }).format(n);
};

export const formatPnL = (
  pct: number | null | undefined,
): { label: string; tone: "pos" | "neg" | "neutral" } => {
  if (pct == null) return { label: "—", tone: "neutral" };
  const sign = pct > 0 ? "+" : "";
  return {
    label: `${sign}${pct.toFixed(1)}%`,
    tone: pct > 0 ? "pos" : pct < 0 ? "neg" : "neutral",
  };
};

export const formatRelativeTime = (d: Date | string): string => {
  const date = typeof d === "string" ? new Date(d) : d;
  const diffMs = Date.now() - date.getTime();
  const future = diffMs < 0;
  const abs = Math.abs(diffMs);
  const sec = Math.floor(abs / 1000);
  const min = Math.floor(sec / 60);
  const hr = Math.floor(min / 60);
  const day = Math.floor(hr / 24);

  if (sec < 45) return future ? "in a moment" : "just now";
  if (min < 60) return future ? `in ${min}m` : `${min}m ago`;
  if (hr < 24) return future ? `in ${hr}h` : `${hr}h ago`;
  if (day < 7) return future ? `in ${day}d` : `${day}d ago`;
  return new Intl.DateTimeFormat("da-DK", { dateStyle: "medium" }).format(date);
};
