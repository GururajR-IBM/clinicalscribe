import type { SOAPDraft } from '@/lib/api';

interface Props {
  soap: SOAPDraft;
}

const SECTIONS: { key: keyof SOAPDraft; label: string }[] = [
  { key: 'subjective', label: 'Subjective' },
  { key: 'objective', label: 'Objective' },
  { key: 'assessment', label: 'Assessment' },
  { key: 'plan', label: 'Plan' },
];

export function SOAPCard({ soap }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm divide-y divide-slate-100">
      <div className="px-5 py-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-rose-600">
          ⚠ Not for clinical use · Synthetic demonstration only
        </p>
      </div>
      {SECTIONS.map(({ key, label }) => (
        <div key={key} className="px-5 py-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
            {label}
          </p>
          <p className="text-sm leading-relaxed text-slate-800">{soap[key]}</p>
        </div>
      ))}
    </div>
  );
}
