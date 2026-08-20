import { z } from "zod";

export const money = z.coerce.number().positive();
export const idOptional = z.string().min(1).nullable().optional();
export const dateValue = z.coerce.date();
