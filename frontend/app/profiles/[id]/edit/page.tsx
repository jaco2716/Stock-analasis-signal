import { notFound } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProfileForm } from "@/components/profile-form";
import { getProfileById } from "@/lib/api/profiles";

interface EditProfilePageProps {
  params: Promise<{ id: string }>;
}

const EditProfilePage = async ({ params }: EditProfilePageProps) => {
  const { id } = await params;
  const profile = await getProfileById(id);
  if (!profile) notFound();

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Edit profile</h1>
        <p className="text-sm text-muted-foreground">{profile.name}</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Profile details</CardTitle>
        </CardHeader>
        <CardContent>
          <ProfileForm profile={profile} />
        </CardContent>
      </Card>
    </div>
  );
};

export default EditProfilePage;
