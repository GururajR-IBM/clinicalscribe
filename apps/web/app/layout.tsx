import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';
import './globals.css';

export const metadata: Metadata = {
  title: 'ClinicalScribe',
  description: 'Multi-agent multi-modal clinical documentation. Synthetic data only.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">{children}</body>
      </html>
    </ClerkProvider>
  );
}
