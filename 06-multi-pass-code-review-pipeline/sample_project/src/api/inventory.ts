const stock: Record<string, number> = {};
export function setStock(sku: string, qty: number) {
  console.log("set stock " + sku);
  stock[sku] = qty;
}
