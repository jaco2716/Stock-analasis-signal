import Link from "next/link";
import { notFound } from "next/navigation";

import { BacktestForm } from "@/components/backtest-form";
import { BacktestResults } from "@/components/backtest-results";
import { Button } from "@/components/ui/button";
import { runBacktest } from "@/lib/api/backtest";
import { getProfileBySlug } from "@/lib/api/profiles";
import type {
  BacktestFilters,
  SignalType,
  SupportedCurrency,
} from "@/lib/types";

interface BacktestPageProps {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{
    minConfidence?: string;
    from?: string;
    to?: string;
    tickers?: string;
    window?: string;
    types?: string;
    dedup?: string;
    shorts?: string;
    notionalDKK?: string;
    notionalUSD?: string;
    notionalEUR?: string;
    kurtageDKK?: string;
    kurtageUSD?: string;
    kurtageEUR?: string;
  }>;
}

const DEFAULT_NOTIONAL: Record<SupportedCurrency, number> = {
  DKK: 10000,
  USD: 1500,
  EUR: 1500,
};

const DEFAULT_KURTAGE: Record<SupportedCurrency, number> = {
  DKK: 29,
  USD: 3,
  EUR: 3,
};

const isoDateNDaysAgo = (n: number): string => {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
};

const parseNumber = (raw: string | undefined, fallback: number): number => {
  if (raw == null || raw === "") return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
};

const parseSignalTypes = (raw: string | undefined): SignalType[] => {
  if (raw == null || raw === "") return ["BUY"];
  const parts = raw
    .split(",")
    .map((s) => s.trim().toUpperCase())
    .filter((s): s is SignalType => s === "BUY" || s === "SELL");
  return parts.length > 0 ? parts : ["BUY"];
};

const parseTickers = (raw: string | undefined): string[] | undefined => {
  if (raw == null || raw === "") return undefined;
  const parts = raw
    .split(",")
    .map((s) => s.trim().toUpperCase())
    .filter((s) => s.length > 0);
  return parts.length > 0 ? parts : undefined;
};

const parseBool = (
  raw: string | undefined,
  fallback: boolean,
): boolean => {
  if (raw == null) return fallback;
  if (raw === "1" || raw === "true" || raw === "on") return true;
  if (raw === "0" || raw === "false" || raw === "off") return false;
  return fallback;
};

const BacktestPage = async ({ params, searchParams }: BacktestPageProps) => {
  const { slug } = await params;
  const sp = await searchParams;
  const profile = await getProfileBySlug(slug);
  if (!profile) notFound();

  // Distinguish "first visit, no params" from "user submitted with all
  // toggles off" — Next.js sends an empty object on first visit.
  const hasParams = Object.keys(sp).length > 0;

  const filters: BacktestFilters = {
    minConfidence: parseNumber(sp.minConfidence, 0.6),
    signalTypes: parseSignalTypes(sp.types),
    fromDate: sp.from || isoDateNDaysAgo(90),
    toDate: sp.to || undefined,
    tickers: parseTickers(sp.tickers),
    window: sp.window === "5" ? 5 : 30,
    dedupWeekly: parseBool(sp.dedup, !hasParams ? true : false),
    treatSellsAsShorts: parseBool(sp.shorts, false),
    notionalByCurrency: {
      DKK: parseNumber(sp.notionalDKK, DEFAULT_NOTIONAL.DKK),
      USD: parseNumber(sp.notionalUSD, DEFAULT_NOTIONAL.USD),
      EUR: parseNumber(sp.notionalEUR, DEFAULT_NOTIONAL.EUR),
    },
    kurtageByCurrency: {
      DKK: parseNumber(sp.kurtageDKK, DEFAULT_KURTAGE.DKK),
      USD: parseNumber(sp.kurtageUSD, DEFAULT_KURTAGE.USD),
      EUR: parseNumber(sp.kurtageEUR, DEFAULT_KURTAGE.EUR),
    },
  };

  const result = await runBacktest(profile.id, filters);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Backtest — {profile.name}
          </h1>
          <p className="text-sm text-muted-foreground">
            Simuler P&L for historiske signaler ud fra valgte filtre.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href={`/p/${profile.slug}`}>Tilbage til dashboard</Link>
        </Button>
      </div>

      <BacktestForm profileSlug={profile.slug} filters={filters} />

      <BacktestResults result={result} />
    </div>
  );
};

export default BacktestPage;
