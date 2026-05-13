"use client";

import { useState, useTransition } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { addHolding, lookupTicker } from "@/app/_actions/holdings";
import type { HoldingKind } from "@/lib/types";

const positiveOptionalNumber = z
  .string()
  .optional()
  .transform((v) => (v == null || v === "" ? undefined : Number(v)));

const formSchema = z
  .object({
    ticker: z
      .string()
      .trim()
      .min(1, "Ticker is required")
      .max(16)
      .transform((s) => s.toUpperCase()),
    kind: z.enum(["owned", "watchlist"]),
    quantity: positiveOptionalNumber,
    avg_buy_price: positiveOptionalNumber,
  })
  .superRefine((v, ctx) => {
    if (v.kind !== "owned") return;
    if (!Number.isFinite(v.quantity) || (v.quantity ?? 0) <= 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["quantity"],
        message: "Quantity is required for owned holdings",
      });
    }
    if (!Number.isFinite(v.avg_buy_price) || (v.avg_buy_price ?? 0) <= 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["avg_buy_price"],
        message: "Avg buy price is required for owned holdings",
      });
    }
  });

type FormValues = z.input<typeof formSchema>;

type LookupState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "found"; currency: string; name: string }
  | { status: "not_found" };

interface AddTickerFormProps {
  profileId: string;
  profileSlug: string;
}

export const AddTickerForm = ({
  profileId,
  profileSlug,
}: AddTickerFormProps) => {
  const [pending, startTransition] = useTransition();
  const [kind, setKind] = useState<HoldingKind>("owned");
  const [lookup, setLookup] = useState<LookupState>({ status: "idle" });

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      ticker: "",
      kind: "owned",
      quantity: "",
      avg_buy_price: "",
    },
  });

  const runLookup = async (rawTicker: string): Promise<LookupState> => {
    const ticker = rawTicker.trim().toUpperCase();
    if (!ticker) {
      const next: LookupState = { status: "idle" };
      setLookup(next);
      return next;
    }
    setLookup({ status: "loading" });
    const result = await lookupTicker({ ticker });
    const next: LookupState = result
      ? { status: "found", currency: result.currency, name: result.name }
      : { status: "not_found" };
    setLookup(next);
    return next;
  };

  const onSubmit = (values: FormValues) => {
    startTransition(async () => {
      // Re-run the lookup so a click-without-blur can't race ahead with stale state.
      let state = lookup;
      if (state.status !== "found") {
        state = await runLookup(values.ticker);
      }
      if (state.status !== "found") {
        toast.error(
          "Ticker not found. Try an exchange suffix (e.g. RHM.DE, NOVO-B.CO).",
        );
        return;
      }
      const isOwned = values.kind === "owned";
      const qty = Number(values.quantity);
      const avg = Number(values.avg_buy_price);
      const result = await addHolding({
        profileId,
        profileSlug,
        ticker: values.ticker,
        name: state.name,
        kind: values.kind,
        quantity: isOwned && Number.isFinite(qty) ? qty : undefined,
        avg_buy_price: isOwned && Number.isFinite(avg) ? avg : undefined,
        currency: state.currency,
      });
      if (result.ok) {
        toast.success(`Added ${values.ticker.toUpperCase()} — ${state.name}`);
        setLookup({ status: "idle" });
        form.reset({
          ticker: "",
          kind: values.kind,
          quantity: "",
          avg_buy_price: "",
        });
      } else {
        toast.error(result.error);
      }
    });
  };

  const handleTickerBlur = async (rawTicker: string) => {
    await runLookup(rawTicker);
  };

  const ownedDisabled = kind !== "owned";
  const displayName = lookup.status === "found" ? lookup.name : "";
  const displayCurrency = lookup.status === "found" ? lookup.currency : "";
  const canSubmit = !pending && lookup.status === "found";

  const tickerHint =
    lookup.status === "loading"
      ? "Looking up…"
      : lookup.status === "found"
        ? `Found: ${lookup.name} (${lookup.currency})`
        : lookup.status === "not_found"
          ? "Not found. Try an exchange suffix (e.g. RHM.DE, NOVO-B.CO)."
          : "Include exchange suffix for non-US tickers.";

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="grid grid-cols-1 gap-4 sm:grid-cols-7"
      >
        <FormField
          control={form.control}
          name="kind"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Type</FormLabel>
              <Select
                value={field.value}
                onValueChange={(v) => {
                  field.onChange(v);
                  setKind(v as HoldingKind);
                }}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="owned">Owned</SelectItem>
                  <SelectItem value="watchlist">Watchlist</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="ticker"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Ticker</FormLabel>
              <FormControl>
                <Input
                  placeholder="NOVO-B.CO"
                  {...field}
                  onChange={(e) => {
                    field.onChange(e.target.value.toUpperCase());
                    // Invalidate prior lookup as soon as the ticker changes.
                    if (lookup.status !== "idle") setLookup({ status: "idle" });
                  }}
                  onBlur={(e) => {
                    field.onBlur();
                    void handleTickerBlur(e.target.value);
                  }}
                  className="font-mono uppercase"
                />
              </FormControl>
              <FormDescription
                className={
                  lookup.status === "not_found" ? "text-destructive" : undefined
                }
              >
                {tickerHint}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormItem>
          <FormLabel>Name</FormLabel>
          <FormControl>
            <Input
              value={displayName}
              readOnly
              tabIndex={-1}
              placeholder="Auto"
              aria-label="Name (auto-filled)"
            />
          </FormControl>
          <FormDescription>Auto-filled.</FormDescription>
        </FormItem>
        <FormField
          control={form.control}
          name="quantity"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Quantity</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="any"
                  placeholder={ownedDisabled ? "Not used" : "Shares"}
                  disabled={ownedDisabled}
                  {...field}
                />
              </FormControl>
              <FormDescription>Owned only.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="avg_buy_price"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Avg buy ({displayCurrency || "—"})</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="any"
                  placeholder={ownedDisabled ? "Not used" : "Per share"}
                  disabled={ownedDisabled}
                  {...field}
                />
              </FormControl>
              <FormDescription>Per share.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormItem>
          <FormLabel>Currency</FormLabel>
          <FormControl>
            <Input
              value={displayCurrency}
              readOnly
              tabIndex={-1}
              placeholder="Auto"
              className="font-mono"
              aria-label="Currency (auto-detected)"
            />
          </FormControl>
          <FormDescription>Auto-detected.</FormDescription>
        </FormItem>
        <div className="flex items-end">
          <Button type="submit" disabled={!canSubmit} className="w-full">
            {pending ? "Adding..." : "Add"}
          </Button>
        </div>
      </form>
    </Form>
  );
};
