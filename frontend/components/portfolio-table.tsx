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
import { formatMoney, formatQuantity } from "@/lib/format";
import type { Holding } from "@/lib/types";

interface PortfolioTableProps {
  holdings: Holding[];
  profileSlug: string;
}

const costBasis = (h: Holding): number | null =>
  h.quantity != null && h.avg_buy_price != null
    ? h.quantity * h.avg_buy_price
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
          <TableHead className="text-right">Avg buy</TableHead>
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
            <TableCell className="text-right">
              {formatMoney(h.avg_buy_price, h.currency)}
            </TableCell>
            <TableCell className="text-right">
              {formatMoney(costBasis(h), h.currency)}
            </TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                <EditHoldingDialog
                  holdingId={h.id}
                  ticker={h.ticker}
                  profileSlug={profileSlug}
                  currentQuantity={h.quantity}
                  currentAvgBuyPrice={h.avg_buy_price}
                  currentCurrency={h.currency}
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
