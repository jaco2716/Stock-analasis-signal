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
import { EditPositionDialog } from "@/components/edit-position-dialog";
import { removeHolding } from "@/app/_actions/holdings";
import { formatDKK } from "@/lib/format";
import type { Holding } from "@/lib/types";

interface PortfolioTableProps {
  holdings: Holding[];
  profileSlug: string;
}

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
          <TableHead className="text-right">Position</TableHead>
          <TableHead className="w-[120px] text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {holdings.map((h) => (
          <TableRow key={h.id}>
            <TableCell className="font-mono font-medium">{h.ticker}</TableCell>
            <TableCell>{h.name}</TableCell>
            <TableCell className="text-right">{formatDKK(h.position_dkk)}</TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                <EditPositionDialog
                  holdingId={h.id}
                  ticker={h.ticker}
                  profileSlug={profileSlug}
                  currentPositionDkk={h.position_dkk}
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
