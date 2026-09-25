'use client';

import { useEffect, useState } from 'react';

interface IncidentSummary {
  incident_id: string;
  title: string | null;
  status: string;
  severity: string | null;
  affected_region: string | null;
  started_at: string;
  resolved_at: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

export default function LiveIncidentConsolePage() {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const token = window.localStorage.getItem('demoRole') ?? '';
        if (!token) {
          setError('Not signed in -- go to /login first.');
          return;
        }
        const res = await fetch(`${API_BASE}/incidents?status=all`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          const body = await res.text();
          setError(`Request failed (${res.status}): ${body}`);
          return;
        }
        setIncidents(await res.json());
        setError(null);
      } catch (e) {
        setError(`Network error: ${e instanceof Error ? e.message : String(e)}`);
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
      {error && (
        <p className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">{error}</p>
      )}
      {!loading && !error && incidents.length === 0 && (
        <p className="text-gray-500">No incidents yet -- run the alert replay to generate some.</p>
      )}
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b">
            <th className="py-2">Incident</th>
            <th>Title</th>
            <th>Status</th>
            <th>Severity</th>
            <th>Region</th>
            <th>Started</th>
            <th>Views</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.incident_id} className="border-b hover:bg-gray-50">
              <td className="py-2 font-mono text-xs">{incident.incident_id}</td>
              <td>{incident.title ?? '—'}</td>
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
              <td>{incident.severity ?? '—'}</td>
              <td>{incident.affected_region ?? '—'}</td>
              <td>{incident.started_at}</td>
              <td className="space-x-2 whitespace-nowrap text-sm">
                <a href={`/incidents/${incident.incident_id}/timeline`} className="text-blue-600 underline">
                  Timeline
                </a>
                <a href={`/root-cause/${incident.incident_id}`} className="text-blue-600 underline">
                  Root Cause
                </a>
                <a href={`/runbooks/${incident.incident_id}`} className="text-blue-600 underline">
                  Runbooks
                </a>
                <a href={`/correlation/${incident.incident_id}`} className="text-blue-600 underline">
                  Correlation
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}

