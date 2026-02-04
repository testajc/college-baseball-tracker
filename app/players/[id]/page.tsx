"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { PlayerWithStats } from "@/lib/types";

export default function PlayerDetailPage() {
  const params = useParams();
  const [player, setPlayer] = useState<PlayerWithStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/players/${params.id}`)
      .then((r) => {
        if (!r.ok) throw new Error("Not found");
        return r.json();
      })
      .then(setPlayer)
      .catch(() => setPlayer(null))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return <div className="py-12 text-center text-muted-foreground">Loading...</div>;
  }

  if (!player) {
    return <div className="py-12 text-center text-muted-foreground">Player not found</div>;
  }

  const h = player.hittingStats;
  const p = player.pitchingStats;

  const formatHeight = (inches: number | null) => {
    if (!inches) return null;
    const ft = Math.floor(inches / 12);
    const rem = inches % 12;
    return `${ft}'${rem}"`;
  };

  return (
    <div className="flex flex-col gap-6">
      <Link href="/players" className="text-sm text-primary hover:underline">
        &larr; Back to players
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            {player.firstName} {player.lastName}
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-muted-foreground">
            {player.position && <span>{player.position}</span>}
            {player.classYear && (
              <>
                <span>&middot;</span>
                <span>{player.classYear}</span>
              </>
            )}
            <span>&middot;</span>
            <Link href={`/teams/${player.team.id}`} className="hover:text-primary hover:underline">
              {player.team.name}
            </Link>
            <span>&middot;</span>
            <Badge variant="secondary">{player.team.division}</Badge>
            <span className="text-sm">{player.team.conference}</span>
          </div>

          {/* Physical info */}
          <div className="mt-2 flex flex-wrap gap-3 text-sm text-muted-foreground">
            {player.heightInches && <span>{formatHeight(player.heightInches)}</span>}
            {player.weightLbs && <span>{player.weightLbs} lbs</span>}
            {player.bats && <span>Bats: {player.bats}</span>}
            {player.throws && <span>Throws: {player.throws}</span>}
            {player.hometown && <span>From: {player.hometown}</span>}
            {player.highSchool && <span>HS: {player.highSchool}</span>}
          </div>

          {player.inPortal && (
            <Badge variant="destructive" className="mt-3">
              IN TRANSFER PORTAL
              {player.portalDate && ` (${new Date(player.portalDate).toLocaleDateString()})`}
            </Badge>
          )}
          {player.committedTo && (
            <div className="mt-1 text-sm text-muted-foreground">
              Committed to: <span className="font-medium text-foreground">{player.committedTo}</span>
            </div>
          )}
        </div>
      </div>

      {/* Hitting Stats */}
      {h && (
        <section>
          <h2 className="mb-3 text-xl font-semibold">Hitting Stats</h2>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-5 md:grid-cols-7 lg:grid-cols-9">
            {([
              ["G", h.g],
              ["AB", h.ab],
              ["AVG", h.avg?.toFixed(3)],
              ["OBP", h.obp?.toFixed(3)],
              ["SLG", h.slg?.toFixed(3)],
              ["OPS", h.ops?.toFixed(3)],
              ["H", h.h],
              ["2B", h.doubles],
              ["3B", h.triples],
              ["HR", h.hr],
              ["RBI", h.rbi],
              ["R", h.r],
              ["BB", h.bb],
              ["K", h.k],
              ["SB", h.sb],
              ["CS", h.cs],
              ["HBP", h.hbp],
              ["SF", h.sf],
              ["SH", h.sh],
              ["GIDP", h.gidp],
              ["TB", h.tb],
              ["XBH", h.xbh],
              ["XBH:K", h.xbhToK?.toFixed(2)],
            ] as [string, string | number | null | undefined][]).map(([label, value]) => (
              <Card key={label} className="py-3">
                <CardContent className="p-0 text-center">
                  <div className="text-xs text-muted-foreground">{label}</div>
                  <div className="mt-1 text-lg font-semibold">{value ?? "-"}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Pitching Stats */}
      {p && (
        <section>
          <h2 className="mb-3 text-xl font-semibold">Pitching Stats</h2>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-5 md:grid-cols-7 lg:grid-cols-9">
            {([
              ["ERA", p.era?.toFixed(2)],
              ["W", p.w],
              ["L", p.l],
              ["SV", p.sv],
              ["APP", p.app],
              ["GS", p.gs],
              ["CG", p.cg],
              ["SHO", p.sho],
              ["IP", p.ip?.toFixed(1)],
              ["H", p.h],
              ["R", p.r],
              ["ER", p.er],
              ["BB", p.bb],
              ["K", p.k],
              ["HR", p.hrAllowed],
              ["HB", p.hb],
              ["WP", p.wp],
              ["BK", p.bk],
              ["WHIP", p.whip?.toFixed(2)],
              ["K/9", p.kPer9?.toFixed(1)],
              ["BB/9", p.bbPer9?.toFixed(1)],
              ["K:BB", p.kToBb?.toFixed(2)],
              ["H/9", p.hPer9?.toFixed(1)],
            ] as [string, string | number | null | undefined][]).map(([label, value]) => (
              <Card key={label} className="py-3">
                <CardContent className="p-0 text-center">
                  <div className="text-xs text-muted-foreground">{label}</div>
                  <div className="mt-1 text-lg font-semibold">{value ?? "-"}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
