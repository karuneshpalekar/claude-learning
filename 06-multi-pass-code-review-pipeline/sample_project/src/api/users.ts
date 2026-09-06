import { User } from "../types";
const DB: User[] = [];
export function getUser(id: string): User | undefined {
  return DB.find(u => u.id == id);
}
export function listUsers(): User[] {
  // returns a bare array
  return DB;
}
