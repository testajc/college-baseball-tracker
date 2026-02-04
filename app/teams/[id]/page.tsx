"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Division, HittingStatsData, PitchingStatsData } from "@/lib/types";

interface TeamPlayer {
  id: number;
  firstName: string;
  lastName: string;
  position: string | null;
  classYear: string | null;
  heightInches: number | null;
  weightLbs: number | null;
  bats: string | null;
  throws: string | null;
  hometown: string | null;
  inPortal: boolean;
  hittingStats: HittingStatsData | null;
  pitchingStats: PitchingStatsData | null;
}

interface TeamDetail {
  id: number;
  name: string;
  mascot: string | null;
  division: Division;
  conference: string;
  state: string | null;
  logoUrl: string | null;
  players: TeamPlayer[];
  _count: { players: number };
}

export default function TeamDetailPage() {
  const params = useParams();
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [statView, setStatView] = useState<"hitting" | "pitching">("hitting");

  useEffect(() => {
    fetch(`/api/teams/${params.id}`)
      .then((r) => {
        if (!r.ok) throw new Error("Not found");
        return r.json();
      })
      .then(setTeam)
      .catch(() => setTeam(null))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return <div className="py-12 text-center text-muted-foreground">Loading...</div>;
  }

  if (!team) {
    return <div className="py-12 text-center text-muted-foreground">Team not found</div>;
  }

  const formatHeight = (inches: number | null) => {
    if (!inches) return "-";
    const ft = Math.floor(inches / 12);
    const rem = inches % 12;
    return `${ft}'${rem}"`;
  };

  return (
    <div className="flex flex-col gap-6">
      <Link href="/teams" className="text-sm text-primary hover:underline">
        &larr; Back to teams
      </Link>

      {/* Team header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{team.name}</h1>
          {team.mascot && (
            <p className="text-lg text-muted-foreground">{team.mascot}</p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{team.division}</Badge>
            <span className="text-sm text-muted-foreground">{team.conference}</span>
            {team.state && (
              <span className="text-sm text-muted-foreground">&middot; {team.state}</span>
            )}
            <span className="text-sm text-muted-foreground">
              &middot; {team._count.players} players
            </span>
          </div>
        </div>
      </div>

      {/* Stat summary cards */}
      <div className="grid gap-3 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Roster Size</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{team._count.players}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Division</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{team.division}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Conference</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{team.conference || "-"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Portal Entries</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {team.players.filter((p) => p.inPortal).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Roster */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Roster</h2>
          <div className="flex gap-1">
            {(["hitting", "pitching"] as const).map((type) => (
              <Button
                key={type}
                variant={statView === type ? "default" : "outline"}
                size="sm"
                className="capitalize"
                onClick={() => setStatView(type)}
              >
                {type}
              </Button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Pos</th>
                <th className="px-3 py-2">Yr</th>
                <th className="px-3 py-2">Ht</th>
                <th className="px-3 py-2">Wt</th>
                <th className="px-3 py-2">B/T</th>
                {statView === "hitting" ? (
                  <>
                    <th className="px-3 py-2">AVG</th>
                    <th className="px-3 py-2">OBP</th>
                    <th className="px-3 py-2">SLG</th>
                    <th className="px-3 py-2">HR</th>
                    <th className="px-3 py-2">RBI</th>
                    <th className="px-3 py-2">H</th>
                    <th className="px-3 py-2">BB</th>
                    <th className="px-3 py-2">K</th>
                    <th className="px-3 py-2">SB</th>
                  </>
                ) : (
                  <>
                    <th className="px-3 py-2">ERA</th>
                    <th className="px-3 py-2">W-L</th>
                    <th className="px-3 py-2">SV</th>
                    <th className="px-3 py-2">IP</th>
                    <th className="px-3 py-2">K</th>
                    <th className="px-3 py-2">BB</th>
                    <th className="px-3 py-2">WHIP</th>
                    <th className="px-3 py-2">K/9</th>
                    <th className="px-3 py-2">H/9</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {team.players.map((player) => {
                const h = player.hittingStats;
                const p = player.pitchingStats;

                return (
                  <tr key={player.id} className="border-t border-border hover:bg-muted/50">
                    <td className="px-3 py-2">
                      <Link
                        href={`/players/${player.id}`}
                        className="font-medium hover:text-primary"
                      >
                        {player.lastName}, {player.firstName}
                      </Link>
                      {player.inPortal && (
                        <Badge variant="destructive" className="ml-1.5 text-[10px]">
                          PORTAL
                        </Badge>
                      )}
                    </td>
                    <td className="px-3 py-2">{player.position ?? "-"}</td>
                    <td className="px-3 py-2">{player.classYear ?? "-"}</td>
                    <td className="px-3 py-2">{formatHeight(player.heightInches)}</td>
                    <td className="px-3 py-2">{player.weightLbs ?? "-"}</td>
                    <td className="px-3 py-2">
                      {player.bats ?? "-"}/{player.throws ?? "-"}
                    </td>
                    {statView === "hitting" ? (
                      <>
                        <td className="px-3 py-2">{h?.avg?.toFixed(3) ?? "-"}</td>
                        <td className="px-3 py-2">{h?.obp?.toFixed(3) ?? "-"}</td>
                        <td className="px-3 py-2">{h?.slg?.toFixed(3) ?? "-"}</td>
                        <td className="px-3 py-2">{h?.hr ?? "-"}</td>
                        <td className="px-3 py-2">{h?.rbi ?? "-"}</td>
                        <td className="px-3 py-2">{h?.h ?? "-"}</td>
                        <td className="px-3 py-2">{h?.bb ?? "-"}</td>
                        <td className="px-3 py-2">{h?.k ?? "-"}</td>
                        <td className="px-3 py-2">{h?.sb ?? "-"}</td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-2">{p?.era?.toFixed(2) ?? "-"}</td>
                        <td className="px-3 py-2">
                          {p ? `${p.w}-${p.l}` : "-"}
                        </td>
                        <td className="px-3 py-2">{p?.sv ?? "-"}</td>
                        <td className="px-3 py-2">{p?.ip?.toFixed(1) ?? "-"}</td>
                        <td className="px-3 py-2">{p?.k ?? "-"}</td>
                        <td className="px-3 py-2">{p?.bb ?? "-"}</td>
                        <td className="px-3 py-2">{p?.whip?.toFixed(2) ?? "-"}</td>
                        <td className="px-3 py-2">{p?.kPer9?.toFixed(1) ?? "-"}</td>
                        <td className="px-3 py-2">{p?.hPer9?.toFixed(1) ?? "-"}</td>
                      </>
                    )}
                  </tr>
                );
              })}
              {team.players.length === 0 && (
                <tr>
                  <td
                    colSpan={statView === "hitting" ? 15 : 15}
                    className="px-3 py-8 text-center text-muted-foreground"
                  >
                    No players on roster
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
