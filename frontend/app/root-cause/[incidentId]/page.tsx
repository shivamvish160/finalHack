'use client';

import { useEffect, useState } from 'react';

interface IncidentDetail {
  incident_id: string;
  status: string;
  root_cause?: string;
  confidence?: number;
  reasoning?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

export default function RootCauseAnalysisViewPage({ params }: { params: { incidentId: string } }) {
  const [incident, setIncident] = useState<IncidentDetail | null>(null);

  useEffect(() => {
    async function load() {
      const token = window.localStorage.getItem('demoRole') ?? '';
      const res = await fetch(`${API_BASE}/incidents/${params.incidentId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setIncident(await res.json());
    }
    load();
  }, [params.incidentId]);

  if (!incident) return <main className="p-8">Loading...</main>;

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Root Cause Analysis — {incident.incident_id}</h1>
      <div className="rounded border p-4 max-w-2xl">
        <p className="text-sm text-gray-500">Status: {incident.status}</p>
        <h2 className="text-xl font-semibold mt-2">{incident.root_cause ?? 'Root cause not yet identified'}</h2>
        {incident.confidence != null && (
          <p className="mt-1">
            Confidence: <span className="font-mono">{Math.round(incident.confidence * 100)}%</span>
          </p>
        )}
        {incident.reasoning && <p className="mt-3 text-gray-700">{incident.reasoning}</p>}
      </div>
    </main>
  );
}
