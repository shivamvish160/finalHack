'use client';

import { useEffect, useState } from 'react';

interface RunbookMatch {
  runbookId: string | null;
  similarityScore: number;
  recommendedActions: string | null;
  belowThreshold: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

export default function RunbookRecommendationViewPage({ params }: { params: { incidentId: string } }) {
  const [match, setMatch] = useState<RunbookMatch | null>(null);

  useEffect(() => {
    async function load() {
      const token = window.localStorage.getItem('demoRole') ?? '';
      const res = await fetch(`${API_BASE}/incidents/${params.incidentId}/runbook-matches`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setMatch(await res.json());
    }
    load();
  }, [params.incidentId]);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Runbook Recommendation — {params.incidentId}</h1>
      {!match && <p>Loading...</p>}
      {match?.belowThreshold && (
        <p className="text-orange-600 font-semibold">
          No confident runbook match found (similarity {Math.round((match.similarityScore ?? 0) * 100)}%).
        </p>
      )}
      {match && !match.belowThreshold && (
        <div className="rounded border p-4 max-w-2xl">
          <p className="text-sm text-gray-500">Runbook: {match.runbookId}</p>
          <p className="mt-1">Similarity: {Math.round(match.similarityScore * 100)}%</p>
          <h2 className="font-semibold mt-3">Recommended Actions</h2>
          <pre className="bg-gray-100 p-3 rounded text-sm whitespace-pre-wrap">{match.recommendedActions}</pre>
        </div>
      )}
    </main>
  );
}
