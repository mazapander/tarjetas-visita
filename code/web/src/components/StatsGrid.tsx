import type { DashboardSummary } from "../app/types";

const metricConfig: Array<[label: string, key: keyof DashboardSummary]> = [
  ["Documentos", "total_documents"],
  ["Contactos", "total_contacts"],
  ["Baja confianza", "low_confidence_contacts"],
  ["Sin email", "contacts_without_email"],
  ["Sin telefono", "contacts_without_phone"],
  ["Warnings", "contacts_with_warnings"],
  ["Duplicados", "possible_duplicates"],
];

export function StatsGrid({ summary }: { summary: DashboardSummary | null }) {
  return (
    <section className="metrics">
      {metricConfig.map(([label, key]) => (
        <article key={key} className="metric-card">
          <span>{label}</span>
          <strong>{summary ? summary[key] : "..."}</strong>
        </article>
      ))}
    </section>
  );
}
