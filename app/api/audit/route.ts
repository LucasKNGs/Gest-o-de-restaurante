import { NextResponse } from "next/server";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError } from "@/backend/lib/http";
export async function GET(){const auth=await requireApiContext();if("error" in auth)return auth.error;if(!canManage(auth.ctx.membership.role))return jsonError("Sem permissão",403);const rows=await prisma.auditLog.findMany({where:{restaurantId:auth.ctx.restaurant.id},orderBy:{createdAt:"desc"},take:300,include:{actor:{select:{name:true,email:true}}}});return NextResponse.json(rows);}
