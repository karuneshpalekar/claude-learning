const MAX_RETRIES = 3;
export async function charge(amount: number): Promise<boolean> {
  for (let i = 0; i < MAX_RETRIES; i++) {
    console.log("charge attempt " + i);
  }
  return true;
}
