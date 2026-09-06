export function formatMoney(cents: number, currency: string): string {
  const amount = (cents / 100).toFixed(2);
  return currency + " " + amount;
}
