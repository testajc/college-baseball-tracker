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
  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: { email: true, name: true, emailAlerts: true },
  });

  return NextResponse.json(user);
}

export async function PATCH(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const userId = parseInt((session.user as { id: string }).id);
  const body = await req.json();

  const data: { emailAlerts?: boolean; name?: string } = {};
  if (typeof body.emailAlerts === "boolean") data.emailAlerts = body.emailAlerts;
  if (typeof body.name === "string") data.name = body.name;

  const user = await prisma.user.update({
    where: { id: userId },
    data,
    select: { email: true, name: true, emailAlerts: true },
  });

  return NextResponse.json(user);
}
