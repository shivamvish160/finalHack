'use client';

import { useEffect, useState } from 'react';

interface Prediction {
  serviceName: string;
  predictedFailureWindow?: string;
  confidence?: number;
  rationale?: string;
  isAnomalyOnly?: boolean;
  anomalyProbability?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

export default function PredictiveHealthDashboardPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [anomalies, setAnomalies] = useState<Prediction[]>([]);

  useEffect(() => {
    async function load() {
      const token = window.localStorage.getItem('idToken') ?? '';
      const headers = { Authorization: `Bearer ${token}` };
      const [predRes, anomRes] = await Promise.all([
        fetch(`${API_BASE}/predictions?activeOnly=true`, { headers }),
        fetch(`${API_BASE}/predictions/anomalies`, { headers }),
      ]);
      if (predRes.ok) setPredictions(await predRes.json());
      if (anomRes.ok) setAnomalies(await anomRes.json());
    }
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Predictive Health Dashboard</h1>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-2">Active Predictions ({predictions.length})</h2>
        <div className="space-y-3">
          {predictions.map((p, idx) => (
            <div key={idx} className="rounded border p-3">
              <p className="font-semibold">{p.serviceName}</p>
              <p className="text-sm text-gray-500">Window: {p.predictedFailureWindow}</p>
              <p className="text-sm">Confidence: {Math.round((p.confidence ?? 0) * 100)}%</p>
              <p className="text-sm text-gray-700 mt-1">{p.rationale}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">Flagged Anomaly Trends ({anomalies.length})</h2>
        <ul className="list-disc pl-5 text-sm">
          {anomalies.map((a, idx) => (
            <li key={idx}>
              {a.serviceName} — anomaly probability {Math.round((a.anomalyProbability ?? 0) * 100)}%
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
