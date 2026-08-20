import { NextResponse } from "next/server";
import { Role } from "@prisma/client";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canAdmin } from "@/backend/lib/context";
import { requireApiContext, jsonError } from "@/backend/lib/http";
import { hashPassword } from "@/backend/lib/security";
import { audit } from "@/backend/lib/audit";
const schema=z.object({name:z.string().min(2).max(100),email:z.string().email(),password:z.string().min(8),role:z.enum(Role)});
export async function GET(){const auth=await requireApiContext();if("error" in auth)return auth.error;const rows=await prisma.restaurantMember.findMany({where:{restaurantId:auth.ctx.restaurant.id},include:{user:{select:{id:true,name:true,email:true,createdAt:true}}},orderBy:{createdAt:"asc"}});return NextResponse.json(rows);}
export async function POST(request:Request){const auth=await requireApiContext();if("error" in auth)return auth.error;if(!canAdmin(auth.ctx.membership.role))return jsonError("Somente Proprietário ou Administrador",403);const p=schema.safeParse(await request.json().catch(()=>null));if(!p.success)return jsonError("Dados inválidos. Senha mínima: 8 caracteres.");const email=p.data.email.toLowerCase().trim();let user=await prisma.user.findUnique({where:{email}});if(user){const exists=await prisma.restaurantMember.findUnique({where:{restaurantId_userId:{restaurantId:auth.ctx.restaurant.id,userId:user.id}}});if(exists)return jsonError("Usuário já está no restaurante");}else{user=await prisma.user.create({data:{name:p.data.name,email,passwordHash:await hashPassword(p.data.password)}});}const member=await prisma.restaurantMember.create({data:{restaurantId:auth.ctx.restaurant.id,userId:user.id,role:p.data.role}});await audit({restaurantId:auth.ctx.restaurant.id,actorUserId:auth.ctx.user.id,action:"ADD_MEMBER",entity:"RestaurantMember",entityId:member.id,data:{email,role:p.data.role}});return NextResponse.json(member,{status:201});}
