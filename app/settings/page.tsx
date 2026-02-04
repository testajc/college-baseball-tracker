"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/login");
  }, [status, router]);

  // Fetch current settings
  useEffect(() => {
    if (status !== "authenticated") return;
    fetch("/api/settings")
      .then((r) => r.json())
      .then((data) => {
        if (data.emailAlerts !== undefined) setEmailAlerts(data.emailAlerts);
        if (data.name) setName(data.name);
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, [status]);

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    try {
      const res = await fetch("/api/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ emailAlerts, name: name || undefined }),
      });
      if (res.ok) setMessage("Settings saved");
      else setMessage("Failed to save");
    } catch {
      setMessage("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (status === "loading" || !loaded) {
    return <div className="py-12 text-center text-muted-foreground">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-md py-8">
      <h1 className="mb-6 text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Account</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Signed in as {session?.user?.email}
          </p>

          <div>
            <label htmlFor="display-name" className="mb-1 block text-sm font-medium text-muted-foreground">
              Display Name
            </label>
            <input
              id="display-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
            />
          </div>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={emailAlerts}
              onChange={(e) => setEmailAlerts(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">
              Email me when a favorited player enters the transfer portal
            </span>
          </label>

          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save Settings"}
          </Button>

          {message && (
            <p className={`text-sm ${message === "Settings saved" ? "text-muted-foreground" : "text-destructive"}`}>
              {message}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
