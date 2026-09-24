'use client';

import { useEffect, useState } from 'react';

interface IncidentSummary {
  incident_id: string;
  status: string;
  opened_at: string;
  root_cause?: string;
  confidence?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

export default function LiveIncidentConsolePage() {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const token = window.localStorage.getItem('idToken') ?? '';
        const res = await fetch(`${API_BASE}/incidents?status=all`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          setIncidents(await res.json());
        }
      } finally {
        setLoading(false);
      }
    }
    load();
    // Realtime refresh: poll every 5s as a REST fallback; production wiring
    // uses a Firestore onSnapshot listener per design.md's realtime note.
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Live Incident Console</h1>
      {loading && <p>Loading incidents...</p>}
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b">
            <th className="py-2">Incident</th>
            <th>Status</th>
            <th>Root Cause</th>
            <th>Confidence</th>
            <th>Opened</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.incident_id} className="border-b hover:bg-gray-50">
              <td className="py-2">
                <a href={`/incidents/${incident.incident_id}/timeline`} className="text-blue-600 underline">
                  {incident.incident_id}
                </a>
              </td>
              <td>
                <span
                  className={
                    incident.status === 'Resolved' || incident.status === 'Closed'
                      ? 'text-green-600'
                      : 'text-orange-600 font-semibold'
                  }
                >
                  {incident.status}
                </span>
              </td>
              <td>{incident.root_cause ?? '—'}</td>
              <td>{incident.confidence != null ? `${Math.round(incident.confidence * 100)}%` : '—'}</td>
              <td>{incident.opened_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
