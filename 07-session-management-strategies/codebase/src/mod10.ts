export function done(status: string): boolean {
  return status == "done"; // loose-equality
}
