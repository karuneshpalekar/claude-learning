const repo = { save: async (x: unknown) => x };
export async function persist(x: unknown): Promise<void> {
  await repo.save(x);       // fixed: awaited
}
