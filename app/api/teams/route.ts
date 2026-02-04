import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { Division } from "@prisma/client";

const VALID_DIVISIONS: Division[] = ["D1", "D2", "D3"];

export async function GET(req: NextRequest) {
  const params = req.nextUrl.searchParams;
  const divisionRaw = params.get("division");
  const division = divisionRaw && VALID_DIVISIONS.includes(divisionRaw as Division)
    ? (divisionRaw as Division)
    : undefined;
  const conference = params.get("conference");
  const search = params.get("search")?.trim();

  try {
    const teams = await prisma.team.findMany({
      where: {
        ...(division && { division }),
        ...(conference && { conference }),
        ...(search && { name: { contains: search, mode: "insensitive" as const } }),
      },
      orderBy: { name: "asc" },
      include: {
        _count: { select: { players: true } },
      },
    });

    // Also return unique conferences for filter dropdowns
    const conferences = await prisma.team.findMany({
      where: { conference: { not: "" } },
      select: { conference: true },
      distinct: ["conference"],
      orderBy: { conference: "asc" },
    });

    return NextResponse.json({
      teams,
      conferences: conferences.map((c) => c.conference),
    });
  } catch (error) {
    console.error("Error fetching teams:", error);
    return NextResponse.json({ error: "Failed to fetch teams" }, { status: 500 });
  }
}
