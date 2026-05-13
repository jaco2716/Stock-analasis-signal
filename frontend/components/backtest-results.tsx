"use client";

import { useMemo, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BacktestResult, BacktestTickerRow } from "@/lib/types";

interface BacktestResultsProps {
  result: BacktestResult;
}

type SortKey =
  | "ticker"
  | "currency"
  | "trades"
  | "wins"
  | "winRate"
  | "avgOutcomePct"
  | "totalPnl";

const formatPct1 = (n: number): string => `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;

const formatWinRate = (n: number): string => `${(n * 100).toFixed(0)}%`;

const pnlTone = (n: number): string =>
  n > 0
    ? "text-green-700 dark:text-green-400"
    : n < 0
      ? "text-red-700 dark:text-red-400"
      : "text-muted-foreground";

export const BacktestResults = ({ result }: BacktestResultsProps) => {
  const [sortKey, setSortKey] = useState<SortKey>("totalPnl");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sortedTickers = useMemo(() => {
    const dir = sortDir === "asc" ? 1 : -1;
    const cmp = (a: BacktestTickerRow, b: BacktestTickerRow): number => {
      let av: number | string;
      let bv: number | string;
      switch (sortKey) {
        case "ticker":
        case "currency":
          av = a[sortKey];
          bv = b[sortKey];
          return av < bv ? -dir : av > bv ? dir : 0;
        case "winRate":
          av = a.trades > 0 ? a.wins / a.trades : 0;
          bv = b.trades > 0 ? b.wins / b.trades : 0;
          break;
        default:
          av = a[sortKey];
          bv = b[sortKey];
      }
      return (av as number) < (bv as number)
        ? -dir
        : (av as number) > (bv as number)
          ? dir
          : 0;
    };
    return [...result.byTicker].sort(cmp);
  }, [result.byTicker, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(
        key === "ticker" || key === "currency" ? "asc" : "desc",
      );
    }
  };

  if (result.totals.length === 0) {
    return (
      <div className="space-y-3">
        <div className="rounded-md border p-6 text-sm text-muted-foreground">
          Ingen trades matchede de valgte filtre. Prøv at sænke min. confidence,
          udvide dato-intervallet, eller skifte mellem T+5 og T+30. Husk at nye
          signaler først får et outcome efter 5–30 handelsdage.
        </div>
        {(result.excludedNoOutcome > 0 || result.dedupRemoved > 0) && (
          <p className="text-xs text-muted-foreground">
            {result.excludedNoOutcome} signaler udeladt (manglende outcome eller
            valuta-konfiguration). {result.dedupRemoved} signaler fjernet via
            ugentlig dedup.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {result.totals.map((t) => (
          <Card key={t.currency}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{t.currency}</span>
                <span className={cn("font-mono text-base", pnlTone(t.totalPnl))}>
                  {formatCurrency(t.totalPnl, t.currency)}
                </span>
              </CardTitle>
              <CardDescription>
                {t.trades} trades · win rate {formatWinRate(t.winRate)}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Avg return</span>
                <span className="font-mono">{formatPct1(t.avgOutcomePct)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Bedste trade</span>
                <span className={cn("font-mono", pnlTone(t.bestTradePnl))}>
                  {formatCurrency(t.bestTradePnl, t.currency)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Værste trade</span>
                <span className={cn("font-mono", pnlTone(t.worstTradePnl))}>
                  {formatCurrency(t.worstTradePnl, t.currency)}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <SortHeader
                k="ticker"
                label="Ticker"
                current={sortKey}
                dir={sortDir}
                onClick={toggleSort}
              />
              <SortHeader
                k="currency"
                label="Valuta"
                current={sortKey}
                dir={sortDir}
                onClick={toggleSort}
              />
              <SortHeader
                k="trades"
                label="Trades"
                current={sortKey}
                dir={sortDir}
                onClick={toggleSort}
                align="right"
              />
              <SortHeader
                k="wins"
                label="Wins"
                current={sortKey}
                dir={sortDir}
                onClick={toggleSort}
                align="right"
              />
              <SortHeader
                k="winRate"
                label="Win rate"
                current={sortKey}
                dir={sortDir}
                onClick={toggleSort}
                align="right"
              />
              <SortHeader
                k="avgOutcomePct"
                label="Avg outcome"
                current={sortKey}
                dir={sortDir}
                onClick={toggleSort}
                align="right"
              />
              <SortHeader
                k="totalPnl"
                label="Total P&L"
                current={sortKey}
                dir={sortDir}
                onClick={toggleSort}
                align="right"
              />
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedTickers.map((row) => {
              const wr = row.trades > 0 ? row.wins / row.trades : 0;
              return (
                <TableRow key={row.ticker}>
                  <TableCell className="font-mono font-medium">
                    {row.ticker}
                  </TableCell>
                  <TableCell>{row.currency}</TableCell>
                  <TableCell className="text-right">{row.trades}</TableCell>
                  <TableCell className="text-right">{row.wins}</TableCell>
                  <TableCell className="text-right">
                    {formatWinRate(wr)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatPct1(row.avgOutcomePct)}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-mono",
                      pnlTone(row.totalPnl),
                    )}
                  >
                    {formatCurrency(row.totalPnl, row.currency)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-muted-foreground">
        {result.excludedNoOutcome} signaler udeladt (manglende outcome eller
        valuta-konfiguration). {result.dedupRemoved} signaler fjernet via
        ugentlig dedup.
      </p>
    </div>
  );
};

interface SortHeaderProps {
  k: SortKey;
  label: string;
  current: SortKey;
  dir: "asc" | "desc";
  onClick: (key: SortKey) => void;
  align?: "left" | "right";
}

const SortHeader = ({
  k,
  label,
  current,
  dir,
  onClick,
  align = "left",
}: SortHeaderProps) => {
  const active = current === k;
  const arrow = active ? (dir === "asc" ? " ↑" : " ↓") : "";
  return (
    <TableHead className={align === "right" ? "text-right" : undefined}>
      <button
        type="button"
        onClick={() => onClick(k)}
        className={cn(
          "inline-flex items-center gap-1 hover:text-foreground",
          active && "text-foreground",
        )}
      >
        {label}
        {arrow}
      </button>
    </TableHead>
  );
};
