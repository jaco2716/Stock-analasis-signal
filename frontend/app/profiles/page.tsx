import Link from "next/link";
import { Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { ProfileForm } from "@/components/profile-form";
import { deleteProfile } from "@/app/_actions/profiles";
import { listProfiles } from "@/lib/api/profiles";

const ProfilesPage = async () => {
  const profiles = await listProfiles();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Profiles</h1>
        <p className="text-sm text-muted-foreground">
          Each profile holds its own portfolio, watchlist, and signal history.
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Existing profiles</h2>
        {profiles.length === 0 ? (
          <div className="rounded-md border p-6 text-sm text-muted-foreground">
            No profiles yet. Create one below.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Slug</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Discord</TableHead>
                <TableHead className="w-[200px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {profiles.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">
                    <Link
                      href={`/p/${p.slug}`}
                      className="hover:underline"
                    >
                      {p.name}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono">{p.slug}</TableCell>
                  <TableCell>
                    {p.is_active ? (
                      <Badge variant="secondary">Active</Badge>
                    ) : (
                      <Badge variant="outline">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {p.discord_webhook_url ? "Configured" : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button asChild variant="outline" size="sm">
                        <Link href={`/profiles/${p.id}/edit`}>Edit</Link>
                      </Button>
                      <ConfirmDialog
                        trigger={
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Delete ${p.name}`}
                          >
                            <Trash2 />
                          </Button>
                        }
                        title={`Delete ${p.name}?`}
                        description="This permanently removes the profile, its holdings, and its signal history."
                        confirmLabel="Delete"
                        destructive
                        successMessage="Profile deleted"
                        onConfirm={() => deleteProfile(p.id)}
                      />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Create a profile</CardTitle>
        </CardHeader>
        <CardContent>
          <ProfileForm />
        </CardContent>
      </Card>
    </div>
  );
};

export default ProfilesPage;
