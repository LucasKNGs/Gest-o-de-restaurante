import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";
const schema=z.object({name:z.string().min(2).max(120),roleName:z.string().max(80).nullable().optional(),document:z.string().max(30).nullable().optional(),monthlySalary:z.coerce.number().nonnegative().nullable().optional(),hiredAt:z.coerce.date().nullable().optional()});
export async function GET(){const auth=await requireApiContext();if("error" in auth)return auth.error;const rows=await prisma.employee.findMany({where:{restaurantId:auth.ctx.restaurant.id},orderBy:{name:"asc"}});return NextResponse.json(decimalToNumber(rows));}
export async function POST(request:Request){const auth=await requireApiContext();if("error" in auth)return auth.error;if(!canManage(auth.ctx.membership.role))return jsonError("Sem permissão",403);const p=schema.safeParse(await request.json().catch(()=>null));if(!p.success)return jsonError("Dados inválidos");const row=await prisma.employee.create({data:{restaurantId:auth.ctx.restaurant.id,...p.data}});await audit({restaurantId:auth.ctx.restaurant.id,actorUserId:auth.ctx.user.id,action:"CREATE",entity:"Employee",entityId:row.id,data:p.data});return NextResponse.json(decimalToNumber(row),{status:201});}
