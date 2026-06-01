export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-24">
      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-rose-600">
        Not for clinical use · Synthetic data only
      </p>
      <h1 className="mb-4 text-5xl font-bold tracking-tight">ClinicalScribe</h1>
      <p className="mb-8 text-lg text-slate-700">
        A multi-agent, multi-modal documentation copilot for clinicians. Upload audio, scans and
        vitals; review a draft SOAP note with ICD-10 / CPT codes; sign off.
      </p>
      <p className="text-sm text-slate-500">
        Phase 0 — scaffolding. Routes, auth and live progress arrive in Phase 1.
      </p>
    </main>
  );
}
