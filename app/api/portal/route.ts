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
  const position = params.get("position");

  try {
    const players = await prisma.player.findMany({
      where: {
        inPortal: true,
        ...(division && { team: { division } }),
        ...(position && { position }),
      },
      include: {
        team: { select: { id: true, name: true, division: true, conference: true } },
        hittingStats: true,
        pitchingStats: true,
      },
      orderBy: { portalDate: "desc" },
    });

    return NextResponse.json({ players });
  } catch (error) {
    console.error("Error fetching portal players:", error);
    return NextResponse.json({ error: "Failed to fetch portal players" }, { status: 500 });
  }
}
