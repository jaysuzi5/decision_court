export type Role = "prosecutor" | "defender" | "judge" | "user";

export interface Intake {
  one_sentence: string;
  leaning: string;
  afraid_of: string;
  values: string;
  constraints: string;
  everything: string;
}

export interface TurnOut {
  role: Role;
  content: string;
  sequence: number;
}

export interface VerdictOut {
  recommendation: string;
  reasoning: string;
  dissent: string;
  next_actions: string[];
  open_question: string;
}

export interface CreateResponse {
  id: string;
  status: string;
  crisis: boolean;
  crisis_message: string | null;
}

const json = { "Content-Type": "application/json" };

export async function createSession(intake: Partial<Intake>): Promise<CreateResponse> {
  const r = await fetch("/api/session", {
    method: "POST",
    headers: json,
    body: JSON.stringify(intake),
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Could not open the case.");
  return r.json();
}

export async function sendReply(id: string, text: string): Promise<void> {
  const r = await fetch(`/api/session/${id}/reply`, {
    method: "POST",
    headers: json,
    body: JSON.stringify({ text }),
  });
  if (r.status === 423) {
    const body = await r.json();
    throw new CrisisError(body.detail?.message ?? "Please reach out for support.");
  }
  if (!r.ok) throw new Error("Your answer was not accepted.");
}

export async function createShare(
  id: string,
  scope: "verdict_only" | "full",
  gallery = false
): Promise<{ token: string; scope: string; gallery: boolean }> {
  const r = await fetch(`/api/session/${id}/share`, {
    method: "POST",
    headers: json,
    body: JSON.stringify({ scope, gallery }),
  });
  if (!r.ok) throw new Error("Could not mint a share link.");
  return r.json();
}

export interface GalleryItem {
  token: string;
  decision: string;
  recommendation: string;
}

export async function fetchGallery(): Promise<GalleryItem[]> {
  const r = await fetch("/api/gallery");
  if (!r.ok) return [];
  return r.json();
}

export function markdownUrl(id: string): string {
  return `/api/session/${id}/markdown`;
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`/api/session/${id}`, { method: "DELETE" });
}

export class CrisisError extends Error {}

export interface Me {
  authenticated: boolean;
  oauth_enabled: boolean;
  name: string;
  email: string;
  picture: string;
}

export interface DocketItem {
  id: string;
  decision: string;
  status: string;
  recommendation: string;
  created_at: string;
}

export async function fetchMe(): Promise<Me> {
  const r = await fetch("/api/auth/me");
  if (!r.ok) return { authenticated: false, oauth_enabled: false, name: "", email: "", picture: "" };
  return r.json();
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
}

export async function fetchDocket(): Promise<DocketItem[]> {
  const r = await fetch("/api/auth/me/sessions");
  if (!r.ok) return [];
  return r.json();
}

export const googleLoginUrl = "/api/auth/google/login";
