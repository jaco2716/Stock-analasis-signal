import Link from "next/link";
import { notFound } from "next/navigation";

import { AddTickerForm } from "@/components/add-ticker-form";
import { PortfolioTable } from "@/components/portfolio-table";
import { SignalsFeed } from "@/components/signals-feed";
import { WatchlistTable } from "@/components/watchlist-table";
import { Button } from "@/components/ui/button";
import { listHoldings } from "@/lib/api/portfolio";
import { getProfileBySlug } from "@/lib/api/profiles";
import { listRecentSignals } from "@/lib/api/signals";

interface DashboardPageProps {
  params: Promise<{ slug: string }>;
}

const DashboardPage = async ({ params }: DashboardPageProps) => {
  const { slug } = await params;
  const profile = await getProfileBySlug(slug);
  if (!profile) notFound();

  const [owned, watchlist, signals] = await Promise.all([
    listHoldings(profile.id, "owned"),
    listHoldings(profile.id, "watchlist"),
    listRecentSignals(profile.id, 10),
  ]);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{profile.name}</h1>
          <p className="text-sm text-muted-foreground">
            Slug: <span className="font-mono">{profile.slug}</span>
            {!profile.is_active ? " · inactive" : null}
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href={`/profiles/${profile.id}/edit`}>Edit profile</Link>
        </Button>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Portfolio</h2>
        <PortfolioTable holdings={owned} profileSlug={profile.slug} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Watchlist</h2>
        <WatchlistTable holdings={watchlist} profileSlug={profile.slug} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Add ticker</h2>
        <AddTickerForm profileId={profile.id} profileSlug={profile.slug} />
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Recent signals</h2>
          <div className="flex items-center gap-4">
            <Link
              href={`/p/${profile.slug}/backtest`}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Backtest
            </Link>
            <Link
              href={`/p/${profile.slug}/signals`}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              View all
            </Link>
          </div>
        </div>
        <SignalsFeed signals={signals} />
      </section>
    </div>
  );
};

export default DashboardPage;
