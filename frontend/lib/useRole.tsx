'use client';

import { useEffect, useState } from 'react';

interface CurrentUser {
  uid: string;
  role: string;
  displayName?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

/** T62: shared hook for consistent role-based navigation gating across all
 * 8 frontend pages (FR-034). */
export function useCurrentUser(): CurrentUser | null {
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    async function load() {
      const token = window.localStorage.getItem('idToken') ?? '';
      const res = await fetch(`${API_BASE}/me`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setUser(await res.json());
    }
    load();
  }, []);

  return user;
}

const NAV_ITEMS: { label: string; href: string; roles?: string[] }[] = [
  { label: 'Live Incident Console', href: '/incidents' },
  { label: 'Approval Console', href: '/approvals', roles: ['Approver', 'IncidentCommander', 'Administrator'] },
  { label: 'Predictive Health', href: '/predictions' },
  { label: 'Executive Dashboard', href: '/executive', roles: ['ExecutiveViewer', 'IncidentCommander', 'Administrator'] },
];

export function RoleGatedNav() {
  const user = useCurrentUser();

  return (
    <nav className="flex gap-4 p-4 border-b bg-white">
      {NAV_ITEMS.filter((item) => !item.roles || (user && item.roles.includes(user.role))).map((item) => (
        <a key={item.href} href={item.href} className="text-sm font-medium text-gray-700 hover:text-blue-600">
          {item.label}
        </a>
      ))}
      {user && <span className="ml-auto text-sm text-gray-400">{user.role}</span>}
    </nav>
  );
}
