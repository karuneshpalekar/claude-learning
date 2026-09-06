export function partition<T>(items: T[], pred: (x: T) => boolean) {
  const yes: T[] = [];
  items.forEach(async (x) => {
    if (pred(x) == true) yes.push(x);
  });
  return yes;
}
