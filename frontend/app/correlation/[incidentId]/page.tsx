'use client';

import { useEffect, useState } from 'react';

interface CorrelatedAlert {
  alert_id: string;
  node_id: string;
  service_name: string;
  severity: string;
  alert_type: string;
  message: string;
  timestamp: string;
  topologyMappingStatus: 'Mapped' | 'Unmapped';
}

interface DependencyGraph {
  nodes: { node_id: string; node_name?: string; mapped: boolean }[];
  edges: { from: string; to: string; basis: string }[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

export default function AlertCorrelationViewPage({ params }: { params: { incidentId: string } }) {
  const [alerts, setAlerts] = useState<CorrelatedAlert[]>([]);
  const [graph, setGraph] = useState<DependencyGraph>({ nodes: [], edges: [] });

  useEffect(() => {
    async function load() {
      const token = window.localStorage.getItem('demoRole') ?? '';
      const headers = { Authorization: `Bearer ${token}` };
      const [alertsRes, graphRes] = await Promise.all([
        fetch(`${API_BASE}/incidents/${params.incidentId}/alerts`, { headers }),
        fetch(`${API_BASE}/incidents/${params.incidentId}/dependency-graph`, { headers }),
      ]);
      if (alertsRes.ok) setAlerts(await alertsRes.json());
      if (graphRes.ok) setGraph(await graphRes.json());
    }
    load();
  }, [params.incidentId]);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Alert Correlation View — {params.incidentId}</h1>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-2">Correlated Alerts ({alerts.length})</h2>
        <table className="w-full text-left border-collapse text-sm">
          <thead>
            <tr className="border-b">
              <th className="py-1">Alert</th>
              <th>Node</th>
              <th>Service</th>
              <th>Severity</th>
              <th>Message</th>
              <th>Topology</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.alert_id} className="border-b">
                <td className="py-1">{a.alert_id}</td>
                <td>{a.node_id}</td>
                <td>{a.service_name}</td>
                <td>{a.severity}</td>
                <td>{a.message}</td>
                <td>
                  <span className={a.topologyMappingStatus === 'Mapped' ? 'text-green-600' : 'text-gray-400 italic'}>
                    {a.topologyMappingStatus}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">Dependency / Blast-Radius Graph</h2>
        <ul className="list-disc pl-5">
          {graph.nodes.map((n) => (
            <li key={n.node_id}>
              {n.node_name ?? n.node_id} {n.mapped ? '' : '(unmapped)'}
            </li>
          ))}
        </ul>
        <p className="text-sm text-gray-500 mt-2">{graph.edges.length} inferred dependency edge(s)</p>
      </section>
    </main>
  );
}
