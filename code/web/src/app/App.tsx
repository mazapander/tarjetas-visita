import { startTransition, useDeferredValue, useEffect, useState } from "react";
import {
  downloadSelection,
  fetchContactDetail,
  fetchContacts,
  fetchSummary,
  processCards,
  softDeleteContact,
  updateContact,
} from "./api";
import type { ContactDetailResponse, ContactSummary, ContactUpdatePayload, DashboardSummary } from "./types";
import { ContactEditor } from "../components/ContactEditor";
import { ContactsTable } from "../components/ContactsTable";
import { ContactsToolbar } from "../components/ContactsToolbar";
import { Panel } from "../components/Panel";
import { StatsGrid } from "../components/StatsGrid";

export function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [contacts, setContacts] = useState<ContactSummary[]>([]);
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [activeContactId, setActiveContactId] = useState<number | null>(null);
  const [activeDetail, setActiveDetail] = useState<ContactDetailResponse | null>(null);
  const [status, setStatus] = useState("Cargando...");
  const [processing, setProcessing] = useState(false);
  const [saving, setSaving] = useState(false);

  const selectedCount = selectedIds.size;

  const refreshList = async (searchValue: string) => {
    const [nextSummary, nextContacts] = await Promise.all([fetchSummary(), fetchContacts(searchValue)]);
    setSummary(nextSummary);
    setContacts(nextContacts.items);
    setStatus(nextContacts.items.length ? `${nextContacts.total_count} contacto(s)` : "No hay contactos visibles.");
    setSelectedIds((current) => {
      const visibleIds = new Set(nextContacts.items.map((contact) => contact.contact_id));
      return new Set([...current].filter((contactId) => visibleIds.has(contactId)));
    });
  };

  useEffect(() => {
    void refreshList(deferredSearch).catch((error: Error) => setStatus(error.message));
  }, [deferredSearch]);

  const openContact = async (contactId: number) => {
    setActiveContactId(contactId);
    const detail = await fetchContactDetail(contactId);
    setActiveDetail(detail);
  };

  const toggleAll = (checked: boolean) => {
    setSelectedIds(() => new Set(checked ? contacts.map((contact) => contact.contact_id) : []));
  };

  const toggleSelected = (contactId: number, checked: boolean) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(contactId);
      else next.delete(contactId);
      return next;
    });
  };

  const runProcess = async () => {
    setProcessing(true);
    setStatus("Procesando...");
    try {
      await processCards();
      await refreshList(deferredSearch);
    } finally {
      setProcessing(false);
    }
  };

  const removeContact = async (contactId: number) => {
    await softDeleteContact(contactId);
    setSelectedIds((current) => {
      const next = new Set(current);
      next.delete(contactId);
      return next;
    });
    if (activeContactId === contactId) {
      setActiveContactId(null);
      setActiveDetail(null);
    }
    await refreshList(deferredSearch);
  };

  const saveDetail = async (payload: ContactUpdatePayload) => {
    if (!activeContactId) return;
    setSaving(true);
    try {
      await updateContact(activeContactId, payload);
      await refreshList(deferredSearch);
      const detail = await fetchContactDetail(activeContactId);
      setActiveDetail(detail);
    } finally {
      setSaving(false);
    }
  };

  const exportCsv = async () => {
    await downloadSelection("/api/exports/outlook.csv", [...selectedIds], "outlook-selected.csv");
  };

  const exportVcf = async () => {
    await downloadSelection("/api/exports/contacts.vcf", [...selectedIds], "contacts-selected.vcf");
  };

  return (
    <main className="app-shell">
      <ContactsToolbar
        search={search}
        selectedCount={selectedCount}
        processing={processing}
        onSearchChange={(value) => startTransition(() => setSearch(value))}
        onProcess={() => void runProcess()}
        onExportCsv={() => void exportCsv()}
        onExportVcf={() => void exportVcf()}
      />

      <StatsGrid summary={summary} />

      <section className="workspace">
        <Panel
          title="Contactos"
          eyebrow="Lista operativa"
          actions={<span className="status-pill">{status}</span>}
          className="contacts-panel"
        >
          <ContactsTable
            contacts={contacts}
            selectedIds={selectedIds}
            activeContactId={activeContactId}
            onToggleAll={toggleAll}
            onToggleSelected={toggleSelected}
            onOpen={(contactId) => void openContact(contactId)}
            onDelete={(contactId) => void removeContact(contactId)}
          />
        </Panel>

        <ContactEditor detail={activeDetail} saving={saving} onSave={saveDetail} />
      </section>
    </main>
  );
}
