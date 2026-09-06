export function eachAsync<T>(items: T[], fn: (x: T) => Promise<void>): void {
  items.forEach(async (item) => {
    await fn(item);
  });
}
