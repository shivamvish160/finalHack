'use client';

import { useEffect, useState } from 'react';

interface ExecutiveMetrics {
  affectedCustomers?: number;
  affectedUsers?: number;
  revenueAtRisk?: number;
  slaCreditExposure?: number;
  averageMttrMinutes?: number;
  resolutionSuccessRatePct?: number;
  predictedIncidentCount?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

export default function ExecutiveDashboardPage() {
  const [metrics, setMetrics] = useState<ExecutiveMetrics>({});

  useEffect(() => {
    async function load() {
      const token = window.localStorage.getItem('idToken') ?? '';
      const res = await fetch(`${API_BASE}/executive/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setMetrics(await res.json());
    }
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  const cards = [
    { label: 'Revenue at Risk', value: metrics.revenueAtRisk != null ? `$${metrics.revenueAtRisk.toLocaleString()}` : '—' },
    { label: 'SLA Credit Exposure', value: metrics.slaCreditExposure != null ? `$${metrics.slaCreditExposure.toLocaleString()}` : '—' },
    { label: 'Affected Customers', value: metrics.affectedCustomers ?? '—' },
    { label: 'Affected Users', value: metrics.affectedUsers ?? '—' },
    { label: 'Avg. MTTR (minutes)', value: metrics.averageMttrMinutes != null ? Math.round(metrics.averageMttrMinutes) : '—' },
    { label: 'Resolution Success Rate', value: metrics.resolutionSuccessRatePct != null ? `${metrics.resolutionSuccessRatePct}%` : '—' },
    { label: 'Predicted Incidents', value: metrics.predictedIncidentCount ?? '—' },
  ];

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-6">Executive Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded border p-4 bg-white shadow-sm">
            <p className="text-sm text-gray-500">{card.label}</p>
            <p className="text-2xl font-bold">{card.value}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
