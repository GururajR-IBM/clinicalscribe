/** API client — thin wrapper over fetch that injects the Clerk Bearer token. */

const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8000';

async function getToken(): Promise<string | null> {
  // Clerk exposes window.__clerk for client-side token retrieval
  if (typeof window === 'undefined') return null;
  // @ts-expect-error – Clerk global injected by ClerkProvider
  const clerk = window.Clerk;
  if (!clerk) return null;
  return clerk.session?.getToken() ?? null;
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${GATEWAY_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Encounter types (mirrors gateway schemas) ───────────────────────────────

export type EncounterStatus = 'pending' | 'transcribing' | 'drafting' | 'complete' | 'failed';

export interface Encounter {
  encounter_id: string;
  patient_id: string;
  status: EncounterStatus;
  created_at: string;
  updated_at: string;
  notes: string | null;
  soap_draft: SOAPDraft | null;
  error_message: string | null;
}

export interface SOAPDraft {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface CreateEncounterResponse {
  encounter_id: string;
  upload_url: string;
  upload_expires_at: string;
  status: EncounterStatus;
}

// ── API calls ────────────────────────────────────────────────────────────────

export async function createEncounter(payload: {
  patient_id: string;
  notes?: string;
  content_type?: string;
}): Promise<CreateEncounterResponse> {
  return apiFetch('/encounters', {
    method: 'POST',
    body: JSON.stringify({ content_type: 'audio/mpeg', ...payload }),
  });
}

export async function getEncounter(id: string): Promise<Encounter> {
  return apiFetch(`/encounters/${id}`);
}

export async function uploadAudio(uploadUrl: string, file: File): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': file.type || 'audio/mpeg' },
    body: file,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
}
