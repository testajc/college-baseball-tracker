import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const userId = parseInt((session.user as { id: string }).id);

  try {
    const favorites = await prisma.favorite.findMany({
      where: { userId },
      include: {
        player: {
          include: {
            team: { select: { id: true, name: true, division: true, conference: true } },
            hittingStats: true,
            pitchingStats: true,
          },
        },
      },
      orderBy: { createdAt: "desc" },
    });

    return NextResponse.json({ favorites });
  } catch (error) {
    console.error("Error fetching favorites:", error);
    return NextResponse.json(
      { error: "Failed to fetch favorites" },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const userId = parseInt((session.user as { id: string }).id);
  const { playerId } = await req.json();

  if (!playerId || typeof playerId !== "number") {
    return NextResponse.json({ error: "playerId required" }, { status: 400 });
  }

  try {
    const favorite = await prisma.favorite.create({
      data: { userId, playerId },
    });
    return NextResponse.json(favorite, { status: 201 });
  } catch (error: unknown) {
    // Unique constraint = already favorited
    if (
      error &&
      typeof error === "object" &&
      "code" in error &&
      (error as { code: string }).code === "P2002"
    ) {
      return NextResponse.json(
        { error: "Already favorited" },
        { status: 409 }
      );
    }
    console.error("Error creating favorite:", error);
    return NextResponse.json(
      { error: "Failed to add favorite" },
      { status: 500 }
    );
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const userId = parseInt((session.user as { id: string }).id);
  const { playerId } = await req.json();

  try {
    await prisma.favorite.delete({
      where: { userId_playerId: { userId, playerId } },
    });
    return NextResponse.json({ success: true });
  } catch {
    return NextResponse.json(
      { error: "Favorite not found" },
      { status: 404 }
    );
  }
}
