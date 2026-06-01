/** useEncounterSSE — subscribes to GET /encounters/{id}/events and returns live status. */

import { useEffect, useState } from 'react';
import type { Encounter, EncounterStatus } from '@/lib/api';

const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8000';

export interface SSEState {
  status: EncounterStatus | null;
  soap_draft: Encounter['soap_draft'];
  error: string | null;
  done: boolean;
}

export function useEncounterSSE(encounterId: string | null, token: string | null): SSEState {
  const [state, setState] = useState<SSEState>({
    status: null,
    soap_draft: null,
    error: null,
    done: false,
  });

  useEffect(() => {
    if (!encounterId || !token) return;

    const url = `${GATEWAY_URL}/encounters/${encounterId}/events`;
    const es = new EventSource(`${url}?token=${encodeURIComponent(token)}`);

    es.addEventListener('status_change', (ev) => {
      const data = JSON.parse(ev.data) as {
        status: EncounterStatus;
        soap_draft?: Encounter['soap_draft'];
      };
      setState((prev) => ({
        ...prev,
        status: data.status,
        soap_draft: data.soap_draft ?? prev.soap_draft,
        done: data.status === 'complete' || data.status === 'failed',
      }));
      if (data.status === 'complete' || data.status === 'failed') {
        es.close();
      }
    });

    es.addEventListener('error', (ev) => {
      const data = (ev as MessageEvent).data;
      setState((prev) => ({ ...prev, error: data ?? 'Stream error', done: true }));
      es.close();
    });

    es.onerror = () => {
      setState((prev) => ({ ...prev, error: 'Connection lost', done: true }));
      es.close();
    };

    return () => es.close();
  }, [encounterId, token]);

  return state;
}
