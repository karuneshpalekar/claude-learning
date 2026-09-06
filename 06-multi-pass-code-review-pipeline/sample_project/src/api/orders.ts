import { Order } from "../types";
const DB: Order[] = [];
export function getOrder(id: string) {
  return DB.find(o => o.id != null && o.id == id);
}
export function listOrders() {
  return { data: DB };
}
