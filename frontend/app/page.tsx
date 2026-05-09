import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getProfileBySlug, listActiveProfiles } from "@/lib/api/profiles";
import { ACTIVE_PROFILE_COOKIE } from "@/lib/constants";

const RootPage = async () => {
  const cookieStore = await cookies();
  const cookieSlug = cookieStore.get(ACTIVE_PROFILE_COOKIE)?.value ?? null;

  if (cookieSlug) {
    const cookieProfile = await getProfileBySlug(cookieSlug);
    if (cookieProfile && cookieProfile.is_active) {
      redirect(`/p/${cookieProfile.slug}`);
    }
  }

  const active = await listActiveProfiles();
  if (active.length > 0) {
    redirect(`/p/${active[0].slug}`);
  }

  redirect("/profiles");
};

export default RootPage;
