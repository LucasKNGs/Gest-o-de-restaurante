import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { verifyPassword } from "@/backend/lib/security";
import { createSession } from "@/backend/lib/session";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

export async function POST(request: Request) {
  const body = schema.safeParse(await request.json().catch(() => null));
  if (!body.success) return NextResponse.json({ error: "Dados inválidos" }, { status: 400 });

  const user = await prisma.user.findUnique({ where: { email: body.data.email.toLowerCase().trim() } });
  if (!user || !(await verifyPassword(body.data.password, user.passwordHash))) {
    return NextResponse.json({ error: "E-mail ou senha inválidos" }, { status: 401 });
  }

  await createSession(user.id);
  return NextResponse.json({ ok: true });
}
