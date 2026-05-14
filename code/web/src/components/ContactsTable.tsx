import type { ContactSummary } from "../app/types";

function primaryValue(contact: ContactSummary) {
  const email = contact.contact_methods.find((item) => item.method_type === "email");
  if (email) return email.normalized_value;
  const phone = contact.contact_methods.find((item) => item.method_type === "mobile" || item.method_type === "phone");
  return phone?.normalized_value ?? "";
}

interface ContactsTableProps {
  contacts: ContactSummary[];
  selectedIds: Set<number>;
  activeContactId: number | null;
  onToggleAll: (checked: boolean) => void;
  onToggleSelected: (contactId: number, checked: boolean) => void;
  onOpen: (contactId: number) => void;
  onDelete: (contactId: number) => void;
}

export function ContactsTable({
  contacts,
  selectedIds,
  activeContactId,
  onToggleAll,
  onToggleSelected,
  onOpen,
  onDelete,
}: ContactsTableProps) {
  const allSelected = contacts.length > 0 && contacts.every((contact) => selectedIds.has(contact.contact_id));

  if (!contacts.length) {
    return <div className="status-row">No hay contactos visibles para los filtros actuales.</div>;
  }

  return (
    <div className="table-shell">
      <table>
        <thead>
          <tr>
            <th className="select-col">
              <input
                type="checkbox"
                aria-label="Seleccionar todo"
                checked={allSelected}
                onChange={(event) => onToggleAll(event.target.checked)}
              />
            </th>
            <th>Nombre</th>
            <th>Empresa</th>
            <th>Cargo</th>
            <th>Contacto</th>
            <th>Confianza</th>
            <th className="action-col">X</th>
          </tr>
        </thead>
        <tbody>
          {contacts.map((contact) => (
            <tr key={contact.contact_id} className={activeContactId === contact.contact_id ? "active-row" : undefined}>
              <td className="select-col">
                <input
                  type="checkbox"
                  checked={selectedIds.has(contact.contact_id)}
                  onChange={(event) => onToggleSelected(contact.contact_id, event.target.checked)}
                  aria-label={`Seleccionar ${contact.full_name ?? contact.company ?? "contacto"}`}
                />
              </td>
              <td>
                <button type="button" className="inline-link" onClick={() => onOpen(contact.contact_id)}>
                  {contact.full_name || "(sin nombre)"}
                </button>
              </td>
              <td>{contact.company || ""}</td>
              <td>{contact.job_title || ""}</td>
              <td>{primaryValue(contact)}</td>
              <td>{contact.confidence ?? ""}</td>
              <td className="action-col">
                <button type="button" className="delete-chip" onClick={() => onDelete(contact.contact_id)}>
                  x
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
