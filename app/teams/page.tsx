"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SearchBar } from "@/components/SearchBar";
import type { Division, TeamWithCount } from "@/lib/types";

const DIVISIONS: (Division | undefined)[] = [undefined, "D1", "D2", "D3"];

export default function TeamsPage() {
  const [teams, setTeams] = useState<TeamWithCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [division, setDivision] = useState<Division | undefined>();

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (division) params.set("division", division);

    fetch(`/api/teams?${params}`)
      .then((r) => r.json())
      .then((data) => setTeams(data.teams ?? []))
      .catch(() => setTeams([]))
      .finally(() => setLoading(false));
  }, [search, division]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">Teams</h1>

      <div className="flex flex-wrap items-center gap-4">
        <SearchBar
          onSearch={(q) => setSearch(q)}
          placeholder="Search teams..."
        />
        <div className="flex gap-1">
          {DIVISIONS.map((d) => (
            <Button
              key={d ?? "all"}
              variant={division === d ? "default" : "outline"}
              size="sm"
              onClick={() => setDivision(d)}
            >
              {d ?? "All"}
            </Button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="py-12 text-center text-muted-foreground">Loading...</div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((team) => (
            <Link key={team.id} href={`/teams/${team.id}`}>
              <Card className="transition-colors hover:bg-muted/50">
                <CardContent className="pt-0">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold">{team.name}</div>
                      {team.mascot && (
                        <div className="text-sm text-muted-foreground">{team.mascot}</div>
                      )}
                    </div>
                    <Badge variant="secondary">{team.division}</Badge>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {team.conference} &middot; {team._count.players} players
                    {team.state && <> &middot; {team.state}</>}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
          {teams.length === 0 && (
            <div className="col-span-full py-8 text-center text-muted-foreground">
              No teams found
            </div>
          )}
        </div>
      )}
    </div>
  );
}
