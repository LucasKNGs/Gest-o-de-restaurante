import { NextResponse } from "next/server";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";
export async function DELETE(_:Request,{params}:{params:Promise<{id:string}>}){const auth=await requireApiContext();if("error" in auth)return auth.error;if(!canManage(auth.ctx.membership.role))return jsonError("Sem permissão",403);const {id}=await params;const row=await prisma.supplier.findFirst({where:{id,restaurantId:auth.ctx.restaurant.id}});if(!row)return jsonError("Fornecedor não encontrado",404);await prisma.supplier.update({where:{id},data:{active:false}});await audit({restaurantId:auth.ctx.restaurant.id,actorUserId:auth.ctx.user.id,action:"DEACTIVATE",entity:"Supplier",entityId:id});return NextResponse.json({ok:true});}
