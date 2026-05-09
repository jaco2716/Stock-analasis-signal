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
import { updatePosition } from "@/app/_actions/holdings";

interface EditPositionDialogProps {
  holdingId: string;
  ticker: string;
  profileSlug: string;
  currentPositionDkk: number | null;
}

export const EditPositionDialog = ({
  holdingId,
  ticker,
  profileSlug,
  currentPositionDkk,
}: EditPositionDialogProps) => {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(
    currentPositionDkk == null ? "" : String(currentPositionDkk),
  );
  const [pending, startTransition] = useTransition();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      toast.error("Position must be a positive number");
      return;
    }
    startTransition(async () => {
      const result = await updatePosition({
        id: holdingId,
        profileSlug,
        position_dkk: parsed,
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
          <DialogTitle>Edit position — {ticker}</DialogTitle>
          <DialogDescription>
            Update the position size for this holding in DKK.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="position_dkk">Position (DKK)</Label>
            <Input
              id="position_dkk"
              type="number"
              inputMode="decimal"
              min="0"
              step="any"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              autoFocus
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
