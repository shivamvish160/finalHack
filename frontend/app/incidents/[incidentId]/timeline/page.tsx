'use client';

import { useEffect, useState } from 'react';

interface TimelineEvent {
  event_time: string;
  event_type: string;
  reference: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? '';

export default function IncidentTimelinePage({ params }: { params: { incidentId: string } }) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);

  useEffect(() => {
    async function load() {
      const token = window.localStorage.getItem('demoRole') ?? '';
      const res = await fetch(`${API_BASE}/incidents/${params.incidentId}/timeline`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setEvents(await res.json());
    }
    load();
  }, [params.incidentId]);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Incident Timeline — {params.incidentId}</h1>
      <ol className="border-l-2 border-gray-300 pl-4 space-y-4">
        {events.map((event, idx) => (
          <li key={idx} className="relative">
            <span className="absolute -left-[1.4rem] top-1 w-2 h-2 bg-blue-600 rounded-full" />
            <p className="text-sm text-gray-500">{event.event_time}</p>
            <p className="font-medium">
              {event.event_type}: {event.reference}
            </p>
          </li>
        ))}
      </ol>
    </main>
  );
}
