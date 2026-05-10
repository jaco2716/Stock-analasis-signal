import type { Route } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { SignalsFeed } from "@/components/signals-feed";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getProfileBySlug } from "@/lib/api/profiles";
import { listSignals, type SignalFilters } from "@/lib/api/signals";
import type { SignalType } from "@/lib/types";

const PAGE_SIZE = 25;

interface SignalsHistoryPageProps {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{
    type?: string;
    ticker?: string;
    from?: string;
    to?: string;
    page?: string;
  }>;
}

const isSignalType = (v: string | undefined): v is SignalType =>
  v === "BUY" || v === "SELL" || v === "HOLD";

const SignalsHistoryPage = async ({
  params,
  searchParams,
}: SignalsHistoryPageProps) => {
  const { slug } = await params;
  const sp = await searchParams;
  const profile = await getProfileBySlug(slug);
  if (!profile) notFound();

  const typeParam = sp.type === "ALL" ? undefined : sp.type;
  const filters: SignalFilters = {
    signalType: isSignalType(typeParam) ? typeParam : undefined,
    ticker: sp.ticker?.trim() || undefined,
    fromDate: sp.from || undefined,
    toDate: sp.to || undefined,
  };
  const page = Math.max(1, Number(sp.page) || 1);
  const { rows, total } = await listSignals(profile.id, filters, page, PAGE_SIZE);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const baseQuery = (overrides: Record<string, string | number | undefined>) => {
    const params = new URLSearchParams();
    if (filters.signalType) params.set("type", filters.signalType);
    if (filters.ticker) params.set("ticker", filters.ticker);
    if (filters.fromDate) params.set("from", filters.fromDate);
    if (filters.toDate) params.set("to", filters.toDate);
    if (page > 1) params.set("page", String(page));
    for (const [k, v] of Object.entries(overrides)) {
      if (v === undefined || v === "") params.delete(k);
      else params.set(k, String(v));
    }
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Signals — {profile.name}
          </h1>
          <p className="text-sm text-muted-foreground">{total} total</p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href={`/p/${profile.slug}`}>Back to dashboard</Link>
        </Button>
      </div>

      <form className="grid grid-cols-1 gap-3 rounded-md border p-4 sm:grid-cols-5">
        <div className="space-y-2">
          <Label htmlFor="type">Signal</Label>
          <Select name="type" defaultValue={filters.signalType ?? "ALL"}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All</SelectItem>
              <SelectItem value="BUY">BUY</SelectItem>
              <SelectItem value="SELL">SELL</SelectItem>
              <SelectItem value="HOLD">HOLD</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="ticker">Ticker</Label>
          <Input
            id="ticker"
            name="ticker"
            placeholder="NOVO-B"
            defaultValue={filters.ticker ?? ""}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="from">From</Label>
          <Input
            id="from"
            name="from"
            type="date"
            defaultValue={filters.fromDate ?? ""}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="to">To</Label>
          <Input
            id="to"
            name="to"
            type="date"
            defaultValue={filters.toDate ?? ""}
          />
        </div>
        <div className="flex items-end gap-2">
          <Button type="submit" className="flex-1">
            Filter
          </Button>
          <Button asChild variant="outline">
            <Link href={`/p/${profile.slug}/signals`}>Reset</Link>
          </Button>
        </div>
      </form>

      <SignalsFeed
        signals={rows}
        emptyMessage="No signals match the current filters."
      />

      {totalPages > 1 ? (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            {page > 1 ? (
              <Button asChild variant="outline" size="sm">
                <Link
                  href={`/p/${profile.slug}/signals${baseQuery({ page: page - 1 || undefined })}` as Route}
                >
                  Previous
                </Link>
              </Button>
            ) : (
              <Button variant="outline" size="sm" disabled>
                Previous
              </Button>
            )}
            {page < totalPages ? (
              <Button asChild variant="outline" size="sm">
                <Link
                  href={`/p/${profile.slug}/signals${baseQuery({ page: page + 1 })}` as Route}
                >
                  Next
                </Link>
              </Button>
            ) : (
              <Button variant="outline" size="sm" disabled>
                Next
              </Button>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default SignalsHistoryPage;
