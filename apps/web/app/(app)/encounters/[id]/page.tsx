'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { getEncounter, uploadAudio, type Encounter } from '@/lib/api';
import { useEncounterSSE } from '@/hooks/useEncounterSSE';
import { StatusBadge } from '@/components/StatusBadge';
import { SOAPCard } from '@/components/SOAPCard';
import { AudioDropzone } from '@/components/AudioDropzone';

const MAX_BYTES = 25 * 1024 * 1024;

function ProgressBar({ status }: { status: Encounter['status'] }) {
  const steps = ['pending', 'transcribing', 'drafting', 'complete'] as const;
  const idx = steps.indexOf(status as (typeof steps)[number]);
  const pct = idx < 0 ? 0 : Math.round(((idx + 1) / steps.length) * 100);
  return (
    <div className="mt-3 h-1.5 w-full rounded-full bg-slate-100">
      <div
        className="h-1.5 rounded-full bg-violet-500 transition-all duration-700"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function EncounterDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();

  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [uploadUrl, setUploadUrl] = useState<string | null>(null);
  const [uploadStep, setUploadStep] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle');
  const [uploadError, setUploadError] = useState<string | null>(null);

  const sse = useEncounterSSE(id, token);

  // Fetch token once
  useEffect(() => {
    getToken().then(setToken).catch(console.error);
  }, [getToken]);

  // Load encounter from gateway
  useEffect(() => {
    if (!token) return;
    getEncounter(id)
      .then(setEncounter)
      .catch(console.error);
  }, [id, token]);

  // Merge SSE status into local encounter
  useEffect(() => {
    if (!sse.status) return;
    setEncounter((prev) =>
      prev
        ? {
            ...prev,
            status: sse.status!,
            soap_draft: sse.soap_draft ?? prev.soap_draft,
          }
        : prev,
    );
  }, [sse.status, sse.soap_draft]);

  const handleFile = useCallback(
    async (file: File) => {
      if (file.size > MAX_BYTES) {
        setUploadError('File exceeds 25 MB limit.');
        return;
      }
      if (!uploadUrl) {
        setUploadError('No upload URL available. Refresh the page.');
        return;
      }
      setUploadStep('uploading');
      setUploadError(null);
      try {
        await uploadAudio(uploadUrl, file);
        setUploadStep('done');
      } catch (err) {
        setUploadError(err instanceof Error ? err.message : 'Upload failed');
        setUploadStep('error');
      }
    },
    [uploadUrl],
  );

  // Retrieve upload URL from encounter after creation
  useEffect(() => {
    // The gateway returns upload_url only in the creation response.
    // We store it in localStorage keyed by encounter_id so the detail page can access it.
    const stored = localStorage.getItem(`upload_url_${id}`);
    if (stored) setUploadUrl(stored);
  }, [id]);

  const status = encounter?.status ?? 'pending';
  const soap = encounter?.soap_draft ?? sse.soap_draft;

  return (
    <div className="mx-auto max-w-2xl">
      {/* Header */}
      <div className="mb-6">
        <p className="mb-1 text-xs text-slate-400">Encounter {id}</p>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-900">
            {encounter?.patient_id ?? 'Loading…'}
          </h1>
          <StatusBadge status={status} />
        </div>
        {status !== 'complete' && status !== 'failed' && (
          <ProgressBar status={status} />
        )}
        {sse.error && (
          <p className="mt-2 text-xs text-red-600">Stream error: {sse.error}</p>
        )}
      </div>

      {/* Upload zone — only when pending and upload URL available */}
      {status === 'pending' && (
        <div className="mb-6">
          {uploadUrl ? (
            <>
              <AudioDropzone
                onFile={(f) => void handleFile(f)}
                disabled={uploadStep === 'uploading' || uploadStep === 'done'}
              />
              {uploadStep === 'uploading' && (
                <p className="mt-2 text-xs text-slate-500">Uploading to Azure Blob Storage…</p>
              )}
              {uploadStep === 'done' && (
                <p className="mt-2 text-xs text-emerald-600">
                  Upload complete — transcription starting…
                </p>
              )}
              {uploadError && (
                <p className="mt-2 text-xs text-red-600">{uploadError}</p>
              )}
            </>
          ) : (
            <div className="rounded-xl border-2 border-dashed border-slate-200 p-8 text-center">
              <p className="text-sm text-slate-400">
                Upload URL expired or unavailable. Create a new encounter.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Live status while processing */}
      {(status === 'transcribing' || status === 'drafting') && (
        <div className="mb-6 rounded-xl border border-violet-100 bg-violet-50 px-5 py-4">
          <p className="text-sm font-medium text-violet-700">
            {status === 'transcribing'
              ? '🎙 Transcribing audio with Whisper…'
              : '🤖 Generating SOAP note (GPT-4o-mini → GPT-4o critic)…'}
          </p>
          <p className="mt-1 text-xs text-violet-400">This page updates automatically.</p>
        </div>
      )}

      {/* SOAP Note */}
      {soap && status === 'complete' && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-900">SOAP Note (Draft)</h2>
          <SOAPCard soap={soap} />
          <p className="mt-3 text-xs text-slate-400">
            AI-generated draft. Physician review required before use.
          </p>
        </div>
      )}

      {/* Error state */}
      {status === 'failed' && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
          <p className="font-medium text-red-700">Processing failed</p>
          {encounter?.error_message && (
            <p className="mt-1 text-sm text-red-600">{encounter.error_message}</p>
          )}
          <p className="mt-2 text-xs text-red-400">
            Please create a new encounter and try again.
          </p>
        </div>
      )}
    </div>
  );
}
