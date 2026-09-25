'use client';

import { useEffect, useState } from 'react';

interface PendingApproval {
  actionId: string;
  incidentId: string;
  runbookId: string;
  fixScript: string;
  rollbackScript: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  status: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

export default function ApprovalConsolePage() {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);

  async function load() {
    const token = window.localStorage.getItem('demoRole') ?? '';
    const res = await fetch(`${API_BASE}/approvals?status=pending`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setApprovals(await res.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function decide(actionId: string, decision: 'approve' | 'reject') {
    const token = window.localStorage.getItem('demoRole') ?? '';
    await fetch(`${API_BASE}/approvals/${actionId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ decision, comments: '' }),
    });
    load();
  }

  const riskColor: Record<string, string> = { Low: 'text-green-600', Medium: 'text-orange-600', High: 'text-red-600' };

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Approval Console</h1>
      <div className="space-y-4">
        {approvals.map((a) => (
          <div key={a.actionId} className="rounded border p-4">
            <p className="text-sm text-gray-500">
              Incident {a.incidentId} — Runbook {a.runbookId}
            </p>
            <p className={`font-semibold ${riskColor[a.riskLevel]}`}>Risk: {a.riskLevel}</p>
            <pre className="bg-gray-100 p-2 rounded text-xs mt-2 whitespace-pre-wrap">{a.fixScript}</pre>
            <details className="mt-1">
              <summary className="text-sm cursor-pointer">Rollback plan</summary>
              <pre className="bg-gray-100 p-2 rounded text-xs whitespace-pre-wrap">{a.rollbackScript}</pre>
            </details>
            <div className="mt-3 space-x-2">
              <button
                onClick={() => decide(a.actionId, 'approve')}
                className="bg-green-600 text-white px-3 py-1 rounded"
              >
                Approve
              </button>
              <button onClick={() => decide(a.actionId, 'reject')} className="bg-red-600 text-white px-3 py-1 rounded">
                Reject
              </button>
            </div>
          </div>
        ))}
        {approvals.length === 0 && <p className="text-gray-500">No pending approvals.</p>}
      </div>
    </main>
  );
}
