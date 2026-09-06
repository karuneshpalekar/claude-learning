const MAX_RETRY = 5;
const queue = { flush: async () => {} };
export async function drain() {
  for (let i = 0; i < MAX_RETRY; i++) {
    queue.flush();
  }
}
