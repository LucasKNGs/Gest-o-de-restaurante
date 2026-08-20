import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";
const schema=z.object({name:z.string().min(2).max(120),unit:z.string().min(1).max(20).default("un"),currentStock:z.coerce.number().nonnegative().default(0),minimumStock:z.coerce.number().nonnegative().default(0),averageCost:z.coerce.number().nonnegative().default(0)});
export async function GET(){const auth=await requireApiContext();if("error" in auth)return auth.error;const rows=await prisma.inventoryItem.findMany({where:{restaurantId:auth.ctx.restaurant.id,active:true},orderBy:{name:"asc"}});return NextResponse.json(decimalToNumber(rows));}
export async function POST(request:Request){const auth=await requireApiContext();if("error" in auth)return auth.error;if(!canManage(auth.ctx.membership.role))return jsonError("Sem permissão",403);const p=schema.safeParse(await request.json().catch(()=>null));if(!p.success)return jsonError("Dados inválidos");const row=await prisma.inventoryItem.create({data:{restaurantId:auth.ctx.restaurant.id,...p.data}});await audit({restaurantId:auth.ctx.restaurant.id,actorUserId:auth.ctx.user.id,action:"CREATE",entity:"InventoryItem",entityId:row.id,data:p.data});return NextResponse.json(decimalToNumber(row),{status:201});}
