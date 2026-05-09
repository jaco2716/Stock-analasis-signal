import "server-only";
import { createServerClient, createServiceClient } from "@/lib/supabase/server";
import type { Profile, NewProfile, ProfileUpdate } from "@/lib/types";

export const listProfiles = async (): Promise<Profile[]> => {
  const supabase = await createServerClient();
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .order("created_at", { ascending: true });
  if (error) throw error;
  return data ?? [];
};

export const listActiveProfiles = async (): Promise<Profile[]> => {
  const supabase = await createServerClient();
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("is_active", true)
    .order("created_at", { ascending: true });
  if (error) throw error;
  return data ?? [];
};

export const getProfileBySlug = async (slug: string): Promise<Profile | null> => {
  const supabase = await createServerClient();
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("slug", slug)
    .maybeSingle();
  if (error) throw error;
  return data;
};

export const getProfileById = async (id: string): Promise<Profile | null> => {
  const supabase = await createServerClient();
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return data;
};

export const insertProfile = async (input: NewProfile): Promise<Profile> => {
  const supabase = createServiceClient();
  const { data, error } = await supabase
    .from("profiles")
    .insert(input)
    .select()
    .single();
  if (error) throw error;
  return data;
};

export const updateProfileById = async (
  id: string,
  patch: ProfileUpdate,
): Promise<Profile> => {
  const supabase = createServiceClient();
  const { data, error } = await supabase
    .from("profiles")
    .update(patch)
    .eq("id", id)
    .select()
    .single();
  if (error) throw error;
  return data;
};

export const deleteProfileById = async (id: string): Promise<void> => {
  const supabase = createServiceClient();
  const { error } = await supabase.from("profiles").delete().eq("id", id);
  if (error) throw error;
};
