"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
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
import { Label } from "@/components/ui/label";
import { createProfile, updateProfile } from "@/app/_actions/profiles";
import { isValidSlug, slugify } from "@/lib/slug";
import type { Profile } from "@/lib/types";

const formSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(120),
  slug: z
    .string()
    .trim()
    .min(1, "Slug is required")
    .max(64)
    .refine(isValidSlug, "Use lowercase letters, numbers, and dashes"),
  discord_webhook_url: z
    .string()
    .trim()
    .url("Must be a valid URL")
    .optional()
    .or(z.literal("")),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof formSchema>;

interface ProfileFormProps {
  profile?: Profile;
}

export const ProfileForm = ({ profile }: ProfileFormProps) => {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  // Track whether the user has manually edited the slug; once true, stop
  // auto-deriving from name (so renames don't clobber a deliberate slug).
  const [slugDirty, setSlugDirty] = useState(Boolean(profile));
  const lastAutoSlug = useRef<string>(profile?.slug ?? "");

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: profile?.name ?? "",
      slug: profile?.slug ?? "",
      discord_webhook_url: profile?.discord_webhook_url ?? "",
      is_active: profile?.is_active ?? true,
    },
  });

  const nameValue = form.watch("name");

  useEffect(() => {
    if (slugDirty) return;
    const next = slugify(nameValue);
    if (next !== lastAutoSlug.current) {
      lastAutoSlug.current = next;
      form.setValue("slug", next, { shouldValidate: false });
    }
  }, [nameValue, slugDirty, form]);

  const onSubmit = (values: FormValues) => {
    startTransition(async () => {
      const payload = {
        name: values.name,
        slug: values.slug,
        discord_webhook_url: values.discord_webhook_url || undefined,
        is_active: values.is_active,
      };
      const result = profile
        ? await updateProfile(profile.id, payload)
        : await createProfile(payload);
      if (result.ok) {
        toast.success(profile ? "Profile updated" : "Profile created");
        router.push("/profiles");
        router.refresh();
      } else {
        toast.error(result.error);
      }
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="Growth portfolio" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="slug"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Slug</FormLabel>
              <FormControl>
                <Input
                  placeholder="growth-portfolio"
                  {...field}
                  onChange={(e) => {
                    setSlugDirty(true);
                    field.onChange(e.target.value);
                  }}
                  className="font-mono"
                />
              </FormControl>
              <FormDescription>
                Used in URLs. Auto-derived from name until you change it.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="discord_webhook_url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Discord webhook URL</FormLabel>
              <FormControl>
                <Input
                  placeholder="https://discord.com/api/webhooks/..."
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Optional. Signals for this profile are posted here when set.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="is_active"
          render={({ field }) => (
            <FormItem className="flex items-center gap-3 space-y-0">
              <FormControl>
                <input
                  type="checkbox"
                  id="is_active"
                  className="h-4 w-4 rounded border-input"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                />
              </FormControl>
              <Label htmlFor="is_active" className="cursor-pointer">
                Active — include in scheduled analysis runs
              </Label>
            </FormItem>
          )}
        />
        <div className="flex gap-2">
          <Button type="submit" disabled={pending}>
            {pending ? "Saving..." : profile ? "Save changes" : "Create profile"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => router.push("/profiles")}
            disabled={pending}
          >
            Cancel
          </Button>
        </div>
      </form>
    </Form>
  );
};
