import { NextResponse } from "next/server";
import { CategoryType } from "@prisma/client";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";

const schema = z.object({ name: z.string().min(2).max(80), type: z.enum(CategoryType) });
const slugify = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export async function GET(){const auth=await requireApiContext();if("error" in auth)return auth.error;return NextResponse.json(await prisma.category.findMany({where:{restaurantId:auth.ctx.restaurant.id},orderBy:{name:"asc"}}));}
export async function POST(request:Request){const auth=await requireApiContext();if("error" in auth)return auth.error;if(!canManage(auth.ctx.membership.role))return jsonError("Sem permissão",403);const p=schema.safeParse(await request.json().catch(()=>null));if(!p.success)return jsonError("Dados inválidos");const slug=slugify(p.data.name);if(!slug)return jsonError("Nome inválido");const row=await prisma.category.create({data:{restaurantId:auth.ctx.restaurant.id,name:p.data.name,slug,type:p.data.type}}).catch(()=>null);if(!row)return jsonError("Já existe uma categoria com nome equivalente",409);await audit({restaurantId:auth.ctx.restaurant.id,actorUserId:auth.ctx.user.id,action:"CREATE",entity:"Category",entityId:row.id,data:p.data});return NextResponse.json(row,{status:201});}
