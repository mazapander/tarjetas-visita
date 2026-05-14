import type {
  ContactDetailResponse,
  ContactUpdatePayload,
  ContactsResponse,
  DashboardSummary,
  ProcessResult,
} from "./types";

async function ensureOk(response: Response): Promise<Response> {
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response;
}

export async function fetchSummary(): Promise<DashboardSummary> {
  return ensureOk(await fetch("/api/dashboard/summary")).then((response) => response.json());
}

export async function fetchContacts(search: string): Promise<ContactsResponse> {
  const query = search.trim();
  const url = `/api/contacts?limit=200${query ? `&search=${encodeURIComponent(query)}` : ""}`;
  return ensureOk(await fetch(url)).then((response) => response.json());
}

export async function fetchContactDetail(contactId: number): Promise<ContactDetailResponse> {
  return ensureOk(await fetch(`/api/contacts/${contactId}`)).then((response) => response.json());
}

export async function processCards(): Promise<ProcessResult> {
  return ensureOk(
    await fetch("/api/pipeline/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "new_or_changed" }),
    }),
  ).then((response) => response.json());
}

export async function updateContact(contactId: number, payload: ContactUpdatePayload): Promise<void> {
  await ensureOk(
    await fetch(`/api/contacts/${contactId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function softDeleteContact(contactId: number): Promise<void> {
  await ensureOk(await fetch(`/api/contacts/${contactId}/delete`, { method: "POST" }));
}

export async function downloadSelection(url: string, contactIds: number[], filename: string): Promise<void> {
  const response = await ensureOk(
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contact_ids: contactIds }),
    }),
  );
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
