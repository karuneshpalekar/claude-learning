"""Generates sample_project/src/ — 14 small TypeScript files with planted issues.

Design of the plant:
- Recurring local patterns that MUST be judged consistently:
    * loose equality (==/!=)       in users.ts, orders.ts, collection.ts
    * forEach(async ...)           in array.ts, collection.ts
    * console.log debug lines      in logger.ts, paymentService.ts, inventory.ts
    * `: any` types                in types.ts, cart.ts, product.ts
    * floating (un-awaited) promise in orderService.ts, retryService.ts
- Cross-file issues invisible to any single-file pass:
    * api/users.ts returns a bare array; api/orders.ts returns { data: [...] }  (API shape drift)
    * utils/format.ts defines formatMoney(cents, currency); cart.ts calls it (currency, cents)
    * paymentService.ts uses MAX_RETRIES; retryService.ts uses MAX_RETRY       (config key drift)

The file ORDER below is fixed so the single-pass attention-dilution simulation
is reproducible: early files (full attention) vs late files (attention spent).
"""

from __future__ import annotations

import pathlib

FILES: list[tuple[str, str]] = [
    ("src/types.ts", """
export interface User { id: string; name: string; meta: any; }
export interface Order { id: string; userId: string; total: number; items: any; }
export type Result = { ok: boolean; error?: string };
"""),
    ("src/api/users.ts", """
import { User } from "../types";
const DB: User[] = [];
export function getUser(id: string): User | undefined {
  return DB.find(u => u.id == id);
}
export function listUsers(): User[] {
  // returns a bare array
  return DB;
}
"""),
    ("src/utils/array.ts", """
export function eachAsync<T>(items: T[], fn: (x: T) => Promise<void>): void {
  items.forEach(async (item) => {
    await fn(item);
  });
}
"""),
    ("src/utils/logger.ts", """
export function log(msg: string): void {
  console.log("[app] " + msg);
}
export function warn(msg: string): void {
  console.log("[warn] " + msg);
}
"""),
    ("src/services/orderService.ts", """
import { Order } from "../types";
const repo = { save: async (o: Order) => o };
export async function placeOrder(o: Order) {
  repo.save(o);
  return o.id;
}
"""),
    ("src/api/orders.ts", """
import { Order } from "../types";
const DB: Order[] = [];
export function getOrder(id: string) {
  return DB.find(o => o.id != null && o.id == id);
}
export function listOrders() {
  return { data: DB };
}
"""),
    ("src/models/cart.ts", """
import { formatMoney } from "../utils/format";
export class Cart {
  lines: any[] = [];
  totalLabel(currency: string, cents: number): string {
    return formatMoney(currency, cents);
  }
}
"""),
    ("src/utils/format.ts", """
export function formatMoney(cents: number, currency: string): string {
  const amount = (cents / 100).toFixed(2);
  return currency + " " + amount;
}
"""),
    ("src/services/paymentService.ts", """
const MAX_RETRIES = 3;
export async function charge(amount: number): Promise<boolean> {
  for (let i = 0; i < MAX_RETRIES; i++) {
    console.log("charge attempt " + i);
  }
  return true;
}
"""),
    ("src/services/retryService.ts", """
const MAX_RETRY = 5;
const queue = { flush: async () => {} };
export async function drain() {
  for (let i = 0; i < MAX_RETRY; i++) {
    queue.flush();
  }
}
"""),
    ("src/utils/collection.ts", """
export function partition<T>(items: T[], pred: (x: T) => boolean) {
  const yes: T[] = [];
  items.forEach(async (x) => {
    if (pred(x) == true) yes.push(x);
  });
  return yes;
}
"""),
    ("src/models/product.ts", """
export class Product {
  id = "";
  attributes: any = {};
  price = 0;
}
"""),
    ("src/api/inventory.ts", """
const stock: Record<string, number> = {};
export function setStock(sku: string, qty: number) {
  console.log("set stock " + sku);
  stock[sku] = qty;
}
"""),
    ("src/index.ts", """
export * from "./api/users";
export * from "./api/orders";
export * from "./api/inventory";
export * from "./services/orderService";
export * from "./services/paymentService";
"""),
]


def write(root: pathlib.Path) -> list[pathlib.Path]:
    written = []
    for rel, body in FILES:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body.lstrip("\n"))
        written.append(p)
    return written


if __name__ == "__main__":
    root = pathlib.Path(__file__).parent / "sample_project"
    paths = write(root)
    print(f"wrote {len(paths)} files under {root}")
