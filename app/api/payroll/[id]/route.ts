import { NextResponse } from "next/server";
import { PaymentMethod } from "@prisma/client";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";
import { refsBelongToRestaurant } from "@/backend/lib/ownership";
const schema=z.object({paymentMethod:z.enum(PaymentMethod),accountId:z.string().nullable().optional(),paidAt:z.coerce.date().optional()});
export async function PATCH(request:Request,{params}:{params:Promise<{id:string}>}){const auth=await requireApiContext();if("error" in auth)return auth.error;if(!canManage(auth.ctx.membership.role))return jsonError("Sem permissão",403);const {id}=await params;const p=schema.safeParse(await request.json().catch(()=>null));if(!p.success)return jsonError("Dados inválidos");if(!(await refsBelongToRestaurant(auth.ctx.restaurant.id,{accountId:p.data.accountId})))return jsonError("Conta inválida",403);const row=await prisma.payrollEntry.findFirst({where:{id,restaurantId:auth.ctx.restaurant.id},include:{employee:true}});if(!row)return jsonError("Folha não encontrada",404);if(row.status==="PAID")return jsonError("Já pago");const paidAt=p.data.paidAt||new Date();const updated=await prisma.$transaction(async tx=>{const mov=await tx.transaction.create({data:{restaurantId:auth.ctx.restaurant.id,createdByUserId:auth.ctx.user.id,type:"EXPENSE",description:`Salário - ${row.employee.name} - ${row.referenceMonth}`,amount:row.netAmount,occurredAt:paidAt,paymentMethod:p.data.paymentMethod,accountId:p.data.accountId||null,reference:`PAYROLL:${row.id}`}});return tx.payrollEntry.update({where:{id},data:{status:"PAID",paidAt,transactionId:mov.id}})});await audit({restaurantId:auth.ctx.restaurant.id,actorUserId:auth.ctx.user.id,action:"PAY",entity:"PayrollEntry",entityId:id,data:p.data});return NextResponse.json(decimalToNumber(updated));}
