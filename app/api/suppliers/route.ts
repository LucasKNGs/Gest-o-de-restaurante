import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";

const schema = z.object({ name: z.string().min(2).max(120), document: z.string().max(30).nullable().optional(), phone: z.string().max(30).nullable().optional(), email: z.string().email().nullable().optional().or(z.literal("")), notes: z.string().max(1000).nullable().optional() });
export async function GET(){ const auth=await requireApiContext(); if("error" in auth)return auth.error; return NextResponse.json(await prisma.supplier.findMany({where:{restaurantId:auth.ctx.restaurant.id},orderBy:{name:"asc"}})); }
export async function POST(request:Request){ const auth=await requireApiContext();if("error" in auth)return auth.error;if(!canManage(auth.ctx.membership.role))return jsonError("Sem permissão",403);const p=schema.safeParse(await request.json().catch(()=>null));if(!p.success)return jsonError("Dados inválidos");const data={...p.data,email:p.data.email||null};const row=await prisma.supplier.create({data:{restaurantId:auth.ctx.restaurant.id,...data}});await audit({restaurantId:auth.ctx.restaurant.id,actorUserId:auth.ctx.user.id,action:"CREATE",entity:"Supplier",entityId:row.id,data});return NextResponse.json(row,{status:201}); }
