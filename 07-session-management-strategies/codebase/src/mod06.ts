interface Cfg { db?: { host?: string } }
export function dbHost(cfg: Cfg): string {
  return cfg.db?.host ?? "localhost";   // fixed: guarded access + default
}
