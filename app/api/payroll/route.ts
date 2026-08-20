import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";
const schema=z.object({employeeId:z.string(),referenceMonth:z.string().regex(/^\d{4}-\d{2}$/),grossAmount:z.coerce.number().positive(),deductions:z.coerce.number().nonnegative().default(0),dueDate:z.coerce.date(),notes:z.string().max(1000).nullable().optional()});
export async function GET(){const auth=await requireApiContext();if("error" in auth)return auth.error;const rows=await prisma.payrollEntry.findMany({where:{restaurantId:auth.ctx.restaurant.id},orderBy:[{referenceMonth:"desc"},{dueDate:"asc"}],include:{employee:true}});return NextResponse.json(decimalToNumber(rows));}
export async function POST(request:Request){const auth=await requireApiContext();if("error" in auth)return auth.error;if(!canManage(auth.ctx.membership.role))return jsonError("Sem permissão",403);const p=schema.safeParse(await request.json().catch(()=>null));if(!p.success)return jsonError("Dados inválidos");const employee=await prisma.employee.findFirst({where:{id:p.data.employeeId,restaurantId:auth.ctx.restaurant.id}});if(!employee)return jsonError("Funcionário inválido");const net=p.data.grossAmount-p.data.deductions;if(net<0)return jsonError("Descontos não podem superar o bruto");const row=await prisma.payrollEntry.create({data:{restaurantId:auth.ctx.restaurant.id,...p.data,netAmount:net}});await audit({restaurantId:auth.ctx.restaurant.id,actorUserId:auth.ctx.user.id,action:"CREATE",entity:"PayrollEntry",entityId:row.id,data:p.data});return NextResponse.json(decimalToNumber(row),{status:201});}
