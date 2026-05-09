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
import { addHolding } from "@/app/_actions/holdings";
import type { HoldingKind } from "@/lib/types";

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
    position_dkk: z.string().optional(),
  })
  .superRefine((v, ctx) => {
    if (v.kind === "owned") {
      const num = Number(v.position_dkk);
      if (!Number.isFinite(num) || num <= 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["position_dkk"],
          message: "Position (DKK) is required for owned holdings",
        });
      }
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

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      ticker: "",
      name: "",
      kind: "owned",
      position_dkk: "",
    },
  });

  const onSubmit = (values: FormValues) => {
    startTransition(async () => {
      const positionNum = Number(values.position_dkk);
      const result = await addHolding({
        profileId,
        profileSlug,
        ticker: values.ticker,
        name: values.name?.trim() ? values.name : undefined,
        kind: values.kind,
        position_dkk:
          values.kind === "owned" && Number.isFinite(positionNum)
            ? positionNum
            : undefined,
      });
      if (result.ok) {
        toast.success(`Added ${values.ticker.toUpperCase()}`);
        form.reset({ ticker: "", name: "", kind: values.kind, position_dkk: "" });
      } else {
        toast.error(result.error);
      }
    });
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="grid grid-cols-1 gap-4 sm:grid-cols-5"
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
          name="position_dkk"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Position (DKK)</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="any"
                  placeholder={kind === "owned" ? "Required" : "Not used"}
                  disabled={kind !== "owned"}
                  {...field}
                />
              </FormControl>
              <FormDescription>Owned holdings only.</FormDescription>
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
