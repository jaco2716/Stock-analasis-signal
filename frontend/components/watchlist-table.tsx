"use client";

import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { removeHolding } from "@/app/_actions/holdings";
import { formatRelativeTime } from "@/lib/format";
import type { Holding } from "@/lib/types";

interface WatchlistTableProps {
  holdings: Holding[];
  profileSlug: string;
}

export const WatchlistTable = ({
  holdings,
  profileSlug,
}: WatchlistTableProps) => {
  if (holdings.length === 0) {
    return (
      <div className="rounded-md border p-6 text-sm text-muted-foreground">
        Watchlist is empty. Add tickers to track without committing capital.
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead>Name</TableHead>
          <TableHead>Added</TableHead>
          <TableHead className="w-[80px] text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {holdings.map((h) => (
          <TableRow key={h.id}>
            <TableCell className="font-mono font-medium">{h.ticker}</TableCell>
            <TableCell>{h.name}</TableCell>
            <TableCell className="text-muted-foreground">
              {formatRelativeTime(h.added_at)}
            </TableCell>
            <TableCell className="text-right">
              <ConfirmDialog
                trigger={
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove ${h.ticker}`}
                  >
                    <Trash2 />
                  </Button>
                }
                title={`Remove ${h.ticker}?`}
                description="This will remove the ticker from your watchlist."
                confirmLabel="Remove"
                destructive
                successMessage={`Removed ${h.ticker}`}
                onConfirm={() => removeHolding({ id: h.id, profileSlug })}
              />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
