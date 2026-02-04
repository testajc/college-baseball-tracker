import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { sendPortalAlert } from "@/lib/email";

export async function POST(req: NextRequest) {
  // Verify internal API secret
  const authHeader = req.headers.get("Authorization");
  if (authHeader !== `Bearer ${process.env.INTERNAL_API_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { playerId } = await req.json();
  if (!playerId) {
    return NextResponse.json({ error: "playerId required" }, { status: 400 });
  }

  try {
    const player = await prisma.player.findUnique({
      where: { id: playerId },
      include: { team: true },
    });

    if (!player) {
      return NextResponse.json({ error: "Player not found" }, { status: 404 });
    }

    // Find all users who favorited this player and have alerts enabled
    const favorites = await prisma.favorite.findMany({
      where: {
        playerId,
        alertSent: false,
        user: { emailAlerts: true },
      },
      include: {
        user: { select: { id: true, email: true } },
      },
    });

    let sent = 0;
    const errors: string[] = [];

    for (const fav of favorites) {
      try {
        await sendPortalAlert({
          userEmail: fav.user.email,
          playerName: `${player.firstName} ${player.lastName}`,
          previousTeam: player.team.name,
          position: player.position || "Unknown",
          playerId: player.id,
        });

        // Mark alert as sent and record notification
        await prisma.$transaction([
          prisma.favorite.update({
            where: { id: fav.id },
            data: { alertSent: true },
          }),
          prisma.portalAlert.create({
            data: { userId: fav.user.id, playerId },
          }),
          prisma.emailNotification.create({
            data: {
              userId: fav.user.id,
              playerId,
              type: "PORTAL_ENTRY",
            },
          }),
        ]);

        sent++;
      } catch (err) {
        errors.push(`Failed to email ${fav.user.email}: ${err}`);
      }
    }

    return NextResponse.json({ sent, total: favorites.length, errors });
  } catch (error) {
    console.error("Error sending portal alerts:", error);
    return NextResponse.json({ error: "Failed to send alerts" }, { status: 500 });
  }
}
