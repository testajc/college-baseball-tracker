import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export async function GET() {
  const [d1, d2, d3, totalPlayers, recentTeams] = await Promise.all([
    prisma.team.count({ where: { division: "D1" } }),
    prisma.team.count({ where: { division: "D2" } }),
    prisma.team.count({ where: { division: "D3" } }),
    prisma.player.count(),
    prisma.team.findMany({
      orderBy: { updatedAt: "desc" },
      take: 10,
      select: { name: true, division: true, updatedAt: true, _count: { select: { players: true } } },
    }),
  ]);

  return NextResponse.json({
    teams: { D1: d1, D2: d2, D3: d3, total: d1 + d2 + d3 },
    totalPlayers,
    recentTeams: recentTeams.map((t) => ({
      name: t.name,
      division: t.division,
      players: t._count.players,
      updatedAt: t.updatedAt,
    })),
  });
}
