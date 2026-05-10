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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { updateHoldingAction } from "@/app/_actions/holdings";

const COMMON_CURRENCIES = ["DKK", "USD", "EUR", "GBP", "SEK", "NOK"] as const;

interface EditHoldingDialogProps {
  holdingId: string;
  ticker: string;
  profileSlug: string;
  currentQuantity: number | null;
  currentAvgBuyPrice: number | null;
  currentCurrency: string;
}

export const EditHoldingDialog = ({
  holdingId,
  ticker,
  profileSlug,
  currentQuantity,
  currentAvgBuyPrice,
  currentCurrency,
}: EditHoldingDialogProps) => {
  const [open, setOpen] = useState(false);
  const [quantity, setQuantity] = useState(
    currentQuantity == null ? "" : String(currentQuantity),
  );
  const [avgBuy, setAvgBuy] = useState(
    currentAvgBuyPrice == null ? "" : String(currentAvgBuyPrice),
  );
  const [currency, setCurrency] = useState(currentCurrency.toUpperCase());
  const [pending, startTransition] = useTransition();

  const currencyOptions = COMMON_CURRENCIES.includes(
    currency as (typeof COMMON_CURRENCIES)[number],
  )
    ? [...COMMON_CURRENCIES]
    : [...COMMON_CURRENCIES, currency];

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
    if (!/^[A-Z]{3}$/.test(currency)) {
      toast.error("Currency must be a 3-letter ISO code");
      return;
    }
    startTransition(async () => {
      const result = await updateHoldingAction({
        id: holdingId,
        profileSlug,
        quantity: parsedQty,
        avg_buy_price: parsedAvg,
        currency,
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
            Update the share quantity, average buy price, and currency for this
            holding.
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
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 space-y-2">
              <Label htmlFor="avg_buy_price">Avg buy price ({currency})</Label>
              <Input
                id="avg_buy_price"
                type="number"
                inputMode="decimal"
                min="0"
                step="any"
                value={avgBuy}
                onChange={(e) => setAvgBuy(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="currency">Currency</Label>
              <Select value={currency} onValueChange={setCurrency}>
                <SelectTrigger id="currency">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {currencyOptions.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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
