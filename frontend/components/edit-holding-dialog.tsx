"use client";

import { useState, useTransition } from "react";
import { Pencil } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { updateHoldingAction } from "@/app/_actions/holdings";

interface EditHoldingDialogProps {
  holdingId: string;
  ticker: string;
  profileSlug: string;
  currentQuantity: number | null;
  currentAvgBuyPriceDkk: number | null;
}

export const EditHoldingDialog = ({
  holdingId,
  ticker,
  profileSlug,
  currentQuantity,
  currentAvgBuyPriceDkk,
}: EditHoldingDialogProps) => {
  const [open, setOpen] = useState(false);
  const [quantity, setQuantity] = useState(
    currentQuantity == null ? "" : String(currentQuantity),
  );
  const [avgBuy, setAvgBuy] = useState(
    currentAvgBuyPriceDkk == null ? "" : String(currentAvgBuyPriceDkk),
  );
  const [pending, startTransition] = useTransition();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const parsedQty = Number(quantity);
    const parsedAvg = Number(avgBuy);
    if (!Number.isFinite(parsedQty) || parsedQty <= 0) {
      toast.error("Quantity must be a positive number");
      return;
    }
    if (!Number.isFinite(parsedAvg) || parsedAvg <= 0) {
      toast.error("Avg buy price must be a positive number");
      return;
    }
    startTransition(async () => {
      const result = await updateHoldingAction({
        id: holdingId,
        profileSlug,
        quantity: parsedQty,
        avg_buy_price_dkk: parsedAvg,
      });
      if (result.ok) {
        toast.success(`Updated ${ticker}`);
        setOpen(false);
      } else {
        toast.error(result.error);
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Edit ${ticker}`}>
          <Pencil />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit holding — {ticker}</DialogTitle>
          <DialogDescription>
            Update the share quantity and average buy price for this holding.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="quantity">Quantity</Label>
            <Input
              id="quantity"
              type="number"
              inputMode="decimal"
              min="0"
              step="any"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="avg_buy_price_dkk">Avg buy price (DKK)</Label>
            <Input
              id="avg_buy_price_dkk"
              type="number"
              inputMode="decimal"
              min="0"
              step="any"
              value={avgBuy}
              onChange={(e) => setAvgBuy(e.target.value)}
              required
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={pending}>
              {pending ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
