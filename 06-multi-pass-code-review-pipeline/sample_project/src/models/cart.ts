import { formatMoney } from "../utils/format";
export class Cart {
  lines: any[] = [];
  totalLabel(currency: string, cents: number): string {
    return formatMoney(currency, cents);
  }
}
