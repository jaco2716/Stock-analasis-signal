"use client";

import { useRef, useState, useTransition } from "react";
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
import { addHolding, lookupTickerCurrency } from "@/app/_actions/holdings";
import type { HoldingKind } from "@/lib/types";

const COMMON_CURRENCIES = ["DKK", "USD", "EUR", "GBP", "SEK", "NOK"] as const;
const DEFAULT_CURRENCY = "DKK";

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
    name: z.string().trim().max(200).optional(),
    kind: z.enum(["owned", "watchlist"]),
    quantity: positiveOptionalNumber,
    avg_buy_price: positiveOptionalNumber,
    currency: z
      .string()
      .trim()
      .toUpperCase()
      .regex(/^[A-Z]{3}$/, "3-letter ISO code"),
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
  // Track whether the user has manually picked a currency. Only auto-prefill
  // from yfinance when they haven't, so we never overwrite their explicit choice.
  const currencyTouchedRef = useRef(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      ticker: "",
      name: "",
      kind: "owned",
      quantity: "",
      avg_buy_price: "",
      currency: DEFAULT_CURRENCY,
    },
  });

  const onSubmit = (values: FormValues) => {
    startTransition(async () => {
      const isOwned = values.kind === "owned";
      const qty = Number(values.quantity);
      const avg = Number(values.avg_buy_price);
      const result = await addHolding({
        profileId,
        profileSlug,
        ticker: values.ticker,
        name: values.name?.trim() ? values.name : undefined,
        kind: values.kind,
        quantity: isOwned && Number.isFinite(qty) ? qty : undefined,
        avg_buy_price: isOwned && Number.isFinite(avg) ? avg : undefined,
        currency: values.currency,
      });
      if (result.ok) {
        toast.success(`Added ${values.ticker.toUpperCase()}`);
        currencyTouchedRef.current = false;
        form.reset({
          ticker: "",
          name: "",
          kind: values.kind,
          quantity: "",
          avg_buy_price: "",
          currency: DEFAULT_CURRENCY,
        });
      } else {
        toast.error(result.error);
      }
    });
  };

  const handleTickerBlur = async (rawTicker: string) => {
    const ticker = rawTicker.trim().toUpperCase();
    if (!ticker || currencyTouchedRef.current) return;
    const result = await lookupTickerCurrency({ ticker });
    if (result && !currencyTouchedRef.current) {
      form.setValue("currency", result.currency, { shouldValidate: true });
    }
  };

  const ownedDisabled = kind !== "owned";
  const currentCurrency = form.watch("currency") || DEFAULT_CURRENCY;
  const currencyOptions = COMMON_CURRENCIES.includes(
    currentCurrency as (typeof COMMON_CURRENCIES)[number],
  )
    ? [...COMMON_CURRENCIES]
    : [...COMMON_CURRENCIES, currentCurrency];

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
                  placeholder="NOVO-B"
                  {...field}
                  onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                  onBlur={(e) => {
                    field.onBlur();
                    void handleTickerBlur(e.target.value);
                  }}
                  className="font-mono uppercase"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="Optional" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
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
              <FormLabel>Avg buy ({currentCurrency})</FormLabel>
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
        <FormField
          control={form.control}
          name="currency"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Currency</FormLabel>
              <Select
                value={field.value}
                onValueChange={(v) => {
                  currencyTouchedRef.current = true;
                  field.onChange(v);
                }}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {currencyOptions.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>Auto-detected from ticker.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex items-end">
          <Button type="submit" disabled={pending} className="w-full">
            {pending ? "Adding..." : "Add"}
          </Button>
        </div>
      </form>
    </Form>
  );
};
