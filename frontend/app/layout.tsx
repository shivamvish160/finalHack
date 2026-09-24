import './globals.css';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'SRE Agentic Incident Platform',
  description: 'Agentic AI Incident Prevention & Resolution Platform',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
