import { clsx } from 'clsx';
import type { EncounterStatus } from '@/lib/api';

const LABELS: Record<EncounterStatus, string> = {
  pending: 'Pending',
  transcribing: 'Transcribing…',
  drafting: 'Drafting SOAP…',
  complete: 'Complete',
  failed: 'Failed',
};

const COLORS: Record<EncounterStatus, string> = {
  pending: 'bg-slate-100 text-slate-600',
  transcribing: 'bg-sky-100 text-sky-700',
  drafting: 'bg-violet-100 text-violet-700',
  complete: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
};

export function StatusBadge({ status }: { status: EncounterStatus }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        COLORS[status],
      )}
    >
      {LABELS[status]}
    </span>
  );
}
