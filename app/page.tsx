import { redirect } from "next/navigation";
import { getRestaurantContext } from "@/backend/lib/context";

export default async function Home() {
  const ctx = await getRestaurantContext();
  redirect(ctx ? "/dashboard" : "/login");
}
