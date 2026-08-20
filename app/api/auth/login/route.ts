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
  try {
    const parsed = schema.safeParse(await request.json().catch(() => null));

    if (!parsed.success) {
      return NextResponse.json({ error: "Dados inválidos" }, { status: 400 });
    }

    const user = await prisma.user.findUnique({
      where: { email: parsed.data.email.toLowerCase().trim() },
    });

    if (!user || !(await verifyPassword(parsed.data.password, user.passwordHash))) {
      return NextResponse.json(
        { error: "E-mail ou senha inválidos" },
        { status: 401 }
      );
    }

    await createSession(user.id);

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("[LOGIN_ERROR]", error);

    return NextResponse.json(
      { error: "Erro interno ao fazer login. Verifique o banco de dados e tente novamente." },
      { status: 500 }
    );
  }
}
