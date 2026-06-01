import Link from 'next/link';
import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';

export default async function HomePage() {
  const { userId } = await auth();
  if (userId) redirect('/encounters');

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-rose-600">
        Not for clinical use · Synthetic data only
      </p>
      <h1 className="mb-4 text-5xl font-bold tracking-tight text-slate-900">ClinicalScribe</h1>
      <p className="mb-8 max-w-lg text-center text-lg text-slate-600">
        A multi-agent, multi-modal documentation copilot for clinicians. Upload audio, review a
        draft SOAP note with ICD-10 codes, and sign off.
      </p>
      <Link
        href="/sign-in"
        className="rounded-lg bg-violet-600 px-6 py-3 text-sm font-semibold text-white shadow hover:bg-violet-700 transition-colors"
      >
        Sign in to get started
      </Link>
    </main>
  );
}
