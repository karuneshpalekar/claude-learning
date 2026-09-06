export interface User { id: string; name: string; meta: any; }
export interface Order { id: string; userId: string; total: number; items: any; }
export type Result = { ok: boolean; error?: string };
