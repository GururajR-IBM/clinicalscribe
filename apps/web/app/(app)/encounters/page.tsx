'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { createEncounter, type Encounter } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';

export default function EncountersPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [patientId, setPatientId] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Fetch list from gateway
  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const token = await getToken();
        if (!token) return;
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8000'}/encounters`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (res.ok) {
          const data = (await res.json()) as Encounter[];
          setEncounters(data);
        }
      } catch (_) {
        // Gateway not running locally — show empty state
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [getToken]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!patientId.trim()) return;
    setCreating(true);
    setError(null);
    try {
      // Override window.Clerk token retrieval with real Clerk hook
      const token = await getToken();
      // Temporarily inject token for apiFetch
      (window as Record<string, unknown>).__csToken = token;
      const resp = await createEncounter({ patient_id: patientId.trim() });
      // Persist upload URL so the detail page can use it (15-min SAS TTL)
      localStorage.setItem(`upload_url_${resp.encounter_id}`, resp.upload_url);
      router.push(`/encounters/${resp.encounter_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create encounter');
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Encounters</h1>
      </div>

      {/* New encounter form */}
      <form
        onSubmit={(e) => void handleCreate(e)}
        className="mb-8 flex gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      >
        <input
          type="text"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          placeholder="Patient ID (e.g. PT-00123)"
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          required
        />
        <button
          type="submit"
          disabled={creating}
          className="rounded-lg bg-violet-600 px-5 py-2 text-sm font-semibold text-white shadow hover:bg-violet-700 disabled:opacity-50 transition-colors"
        >
          {creating ? 'Creating…' : '+ New Encounter'}
        </button>
      </form>

      {error && (
        <p className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      )}

      {loading ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : encounters.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-12 text-center">
          <p className="text-slate-400">No encounters yet. Create one above.</p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white shadow-sm">
          {encounters.map((enc) => (
            <li key={enc.encounter_id}>
              <Link
                href={`/encounters/${enc.encounter_id}`}
                className="flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors"
              >
                <div>
                  <p className="font-medium text-slate-900">{enc.patient_id}</p>
                  <p className="text-xs text-slate-400">
                    {new Date(enc.created_at).toLocaleString()}
                  </p>
                </div>
                <StatusBadge status={enc.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
