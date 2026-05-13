"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { BacktestFilters } from "@/lib/types";

interface BacktestFormProps {
  profileSlug: string;
  filters: BacktestFilters;
}

export const BacktestForm = ({ profileSlug, filters }: BacktestFormProps) => {
  const types = new Set(filters.signalTypes);
  const tickersValue = filters.tickers?.join(", ") ?? "";

  return (
    <form
      method="get"
      className="space-y-6 rounded-md border p-4"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-2">
          <Label htmlFor="minConfidence">Min. confidence (0–1)</Label>
          <Input
            id="minConfidence"
            name="minConfidence"
            type="number"
            min="0"
            max="1"
            step="0.05"
            defaultValue={filters.minConfidence}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="from">Fra dato</Label>
          <Input
            id="from"
            name="from"
            type="date"
            defaultValue={filters.fromDate ?? ""}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="to">Til dato</Label>
          <Input
            id="to"
            name="to"
            type="date"
            defaultValue={filters.toDate ?? ""}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="tickers">Tickers (komma-separeret)</Label>
          <Input
            id="tickers"
            name="tickers"
            placeholder="NOVO-B.CO, AAPL"
            defaultValue={tickersValue}
            className="font-mono uppercase"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-2">
          <Label htmlFor="window">Holdeperiode</Label>
          <select
            id="window"
            name="window"
            defaultValue={String(filters.window)}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
          >
            <option value="5">T+5</option>
            <option value="30">T+30</option>
          </select>
        </div>

        <div className="space-y-2">
          <Label>Signal-typer</Label>
          <div className="flex h-9 items-center gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                name="types"
                value="BUY"
                defaultChecked={types.has("BUY")}
                className="h-4 w-4"
              />
              BUY
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                name="types"
                value="SELL"
                defaultChecked={types.has("SELL")}
                className="h-4 w-4"
              />
              SELL
            </label>
          </div>
        </div>

        <div className="space-y-2">
          <Label>Dedupér ugentligt</Label>
          <label className="flex h-9 items-center gap-2 text-sm">
            <input
              type="checkbox"
              name="dedup"
              value="1"
              defaultChecked={filters.dedupWeekly}
              className="h-4 w-4"
            />
            Tæl kun første signal pr. ISO-uge
          </label>
        </div>

        <div className="space-y-2">
          <Label>SELL som shorts</Label>
          <label className="flex h-9 items-center gap-2 text-sm">
            <input
              type="checkbox"
              name="shorts"
              value="1"
              defaultChecked={filters.treatSellsAsShorts}
              className="h-4 w-4"
            />
            Inkludér SELL-trades med inverteret P&L
          </label>
        </div>
      </div>

      <fieldset className="space-y-3 rounded-md border p-3">
        <legend className="px-1 text-xs font-medium uppercase text-muted-foreground">
          Notional pr. valuta
        </legend>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="notionalDKK">DKK</Label>
            <Input
              id="notionalDKK"
              name="notionalDKK"
              type="number"
              min="0"
              step="any"
              defaultValue={filters.notionalByCurrency.DKK}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="notionalUSD">USD</Label>
            <Input
              id="notionalUSD"
              name="notionalUSD"
              type="number"
              min="0"
              step="any"
              defaultValue={filters.notionalByCurrency.USD}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="notionalEUR">EUR</Label>
            <Input
              id="notionalEUR"
              name="notionalEUR"
              type="number"
              min="0"
              step="any"
              defaultValue={filters.notionalByCurrency.EUR}
            />
          </div>
        </div>
      </fieldset>

      <fieldset className="space-y-3 rounded-md border p-3">
        <legend className="px-1 text-xs font-medium uppercase text-muted-foreground">
          Kurtage pr. side (køb + salg = 2x)
        </legend>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="kurtageDKK">DKK</Label>
            <Input
              id="kurtageDKK"
              name="kurtageDKK"
              type="number"
              min="0"
              step="any"
              defaultValue={filters.kurtageByCurrency.DKK}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="kurtageUSD">USD</Label>
            <Input
              id="kurtageUSD"
              name="kurtageUSD"
              type="number"
              min="0"
              step="any"
              defaultValue={filters.kurtageByCurrency.USD}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="kurtageEUR">EUR</Label>
            <Input
              id="kurtageEUR"
              name="kurtageEUR"
              type="number"
              min="0"
              step="any"
              defaultValue={filters.kurtageByCurrency.EUR}
            />
          </div>
        </div>
      </fieldset>

      <div className="flex gap-2">
        <Button type="submit">Kør backtest</Button>
        <Button asChild variant="outline">
          <Link href={`/p/${profileSlug}/backtest`}>Nulstil</Link>
        </Button>
      </div>
    </form>
  );
};
