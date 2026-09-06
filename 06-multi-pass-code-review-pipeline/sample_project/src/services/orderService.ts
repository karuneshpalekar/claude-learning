import { Order } from "../types";
const repo = { save: async (o: Order) => o };
export async function placeOrder(o: Order) {
  repo.save(o);
  return o.id;
}
