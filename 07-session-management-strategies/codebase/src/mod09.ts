const bus = { emit: async (e: string) => e };
export async function fire(e: string): Promise<void> {
  bus.emit(e);             // floating-promise
}
