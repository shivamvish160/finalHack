'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

// Demo-only role picker: api-gateway must be deployed with DEMO_AUTH_BYPASS=true
// for this to work (no real Firebase Auth in this mode -- see auth.py).
const DEMO_ROLES = [
  'OnCallEngineer',
  'IncidentCommander',
  'Approver',
  'ExecutiveViewer',
  'Administrator',
];

export default function LoginPage() {
  const router = useRouter();
  const [role, setRole] = useState(DEMO_ROLES[0]);

  function handleSignIn() {
    window.localStorage.setItem('idToken', role);
    router.push('/incidents');
  }

  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="mb-4 text-xl font-semibold">Demo Sign In</h1>
      <p className="mb-4 text-sm text-gray-600">
        Select a role to sign in as (demo auth bypass -- no password required).
      </p>
      <select
        className="mb-4 w-full rounded border p-2"
        value={role}
        onChange={(e) => setRole(e.target.value)}
      >
        {DEMO_ROLES.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
      <button
        className="w-full rounded bg-blue-600 p-2 text-white hover:bg-blue-700"
        onClick={handleSignIn}
      >
        Sign In
      </button>
    </main>
  );
}
