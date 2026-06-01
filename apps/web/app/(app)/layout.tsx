import { UserButton } from '@clerk/nextjs';
import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import Link from 'next/link';

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const { userId } = await auth();
  if (!userId) redirect('/sign-in');

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm">
        <Link href="/encounters" className="text-sm font-semibold text-slate-900 hover:text-violet-600">
          🩺 ClinicalScribe
        </Link>
        <div className="flex items-center gap-3">
          <p className="hidden text-xs text-rose-600 sm:block">⚠ Synthetic data only</p>
          <UserButton afterSignOutUrl="/" />
        </div>
      </header>
      <main className="flex-1 px-4 py-6 sm:px-8">{children}</main>
    </div>
  );
}
