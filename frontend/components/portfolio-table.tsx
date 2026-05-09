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
import { EditHoldingDialog } from "@/components/edit-holding-dialog";
import { removeHolding } from "@/app/_actions/holdings";
import { formatDKK, formatQuantity } from "@/lib/format";
import type { Holding } from "@/lib/types";

interface PortfolioTableProps {
  holdings: Holding[];
  profileSlug: string;
}

const costBasis = (h: Holding): number | null =>
  h.quantity != null && h.avg_buy_price_dkk != null
    ? h.quantity * h.avg_buy_price_dkk
    : null;

export const PortfolioTable = ({
  holdings,
  profileSlug,
}: PortfolioTableProps) => {
  if (holdings.length === 0) {
    return (
      <div className="rounded-md border p-6 text-sm text-muted-foreground">
        No owned holdings yet. Add one below.
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead>Name</TableHead>
          <TableHead className="text-right">Qty</TableHead>
          <TableHead className="text-right">Avg buy (DKK)</TableHead>
          <TableHead className="text-right">Cost basis</TableHead>
          <TableHead className="w-[120px] text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {holdings.map((h) => (
          <TableRow key={h.id}>
            <TableCell className="font-mono font-medium">{h.ticker}</TableCell>
            <TableCell>{h.name}</TableCell>
            <TableCell className="text-right">{formatQuantity(h.quantity)}</TableCell>
            <TableCell className="text-right">{formatDKK(h.avg_buy_price_dkk)}</TableCell>
            <TableCell className="text-right">{formatDKK(costBasis(h))}</TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                <EditHoldingDialog
                  holdingId={h.id}
                  ticker={h.ticker}
                  profileSlug={profileSlug}
                  currentQuantity={h.quantity}
                  currentAvgBuyPriceDkk={h.avg_buy_price_dkk}
                />
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
                  description="This will remove the holding from your portfolio."
                  confirmLabel="Remove"
                  destructive
                  successMessage={`Removed ${h.ticker}`}
                  onConfirm={() =>
                    removeHolding({ id: h.id, profileSlug })
                  }
                />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
