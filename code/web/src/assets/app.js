const metricsEl = document.querySelector("#metrics");
const contactsEl = document.querySelector("#contacts");
const statusEl = document.querySelector("#status");
const searchEl = document.querySelector("#search");
const processButton = document.querySelector("#process-button");
const exportCsvButton = document.querySelector("#export-csv-button");
const exportVcfButton = document.querySelector("#export-vcf-button");
const selectAllEl = document.querySelector("#select-all");
const detailTitleEl = document.querySelector("#detail-title");
const previewFrameEl = document.querySelector("#preview-frame");
const openOriginalEl = document.querySelector("#open-original");
const contactFormEl = document.querySelector("#contact-form");
const saveButton = document.querySelector("#save-button");
const ocrMarkdownEl = document.querySelector("#ocr-markdown");

const state = {
  contacts: [],
  selectedIds: new Set(),
  activeContactId: null,
  activeDetail: null,
};

async function getJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function downloadSelection(url, filename) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contact_ids: Array.from(state.selectedIds) }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
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

function renderMetrics(summary) {
  const items = [
    ["Documentos", summary.total_documents],
    ["Contactos", summary.total_contacts],
    ["Baja confianza", summary.low_confidence_contacts],
    ["Sin email", summary.contacts_without_email],
    ["Sin telefono", summary.contacts_without_phone],
    ["Warnings", summary.contacts_with_warnings],
    ["Duplicados", summary.possible_duplicates],
  ];
  metricsEl.innerHTML = items
    .map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value ?? 0}</strong></div>`)
    .join("");
}

function primaryMethod(contact, types) {
  const method = contact.contact_methods.find((item) => types.includes(item.method_type));
  return method ? method.normalized_value : "";
}

function updateActionButtons() {
  const count = state.selectedIds.size;
  const suffix = count ? ` (${count})` : "";
  exportCsvButton.textContent = `Exportar CSV${suffix}`;
  exportVcfButton.textContent = `Exportar VCF${suffix}`;
  const visibleIds = state.contacts.map((contact) => contact.contact_id);
  const allSelected = visibleIds.length > 0 && visibleIds.every((contactId) => state.selectedIds.has(contactId));
  selectAllEl.checked = allSelected;
}

function renderContacts(payload) {
  state.contacts = payload.items;
  if (!payload.items.length) {
    contactsEl.innerHTML = "";
    statusEl.textContent = "No hay contactos visibles. Procesa nuevas tarjetas o revisa las detecciones.";
    updateActionButtons();
    return;
  }
  statusEl.textContent = `${payload.total_count} contacto(s)`;
  contactsEl.innerHTML = payload.items
    .map((contact) => {
      const contactValue = primaryMethod(contact, ["email"]) || primaryMethod(contact, ["mobile", "phone"]);
      const checked = state.selectedIds.has(contact.contact_id) ? "checked" : "";
      const active = state.activeContactId === contact.contact_id ? "active-row" : "";
      return `<tr class="${active}" data-id="${contact.contact_id}">
        <td class="select-col"><input class="row-selector" data-select-id="${contact.contact_id}" type="checkbox" ${checked} aria-label="Seleccionar contacto" /></td>
        <td><button class="name-link" type="button" data-open-id="${contact.contact_id}">${contact.full_name || "(sin nombre)"}</button></td>
        <td>${contact.company || ""}</td>
        <td>${contact.job_title || ""}</td>
        <td>${contactValue}</td>
        <td>${contact.confidence ?? ""}</td>
        <td class="action-col"><button class="delete-chip" type="button" data-delete-id="${contact.contact_id}" aria-label="Ocultar deteccion">x</button></td>
      </tr>`;
    })
    .join("");
  updateActionButtons();
}

function renderPreview(documentData) {
  if (!documentData || !documentData.image_url) {
    previewFrameEl.innerHTML = '<p class="empty-state">No hay vista previa disponible.</p>';
    openOriginalEl.classList.add("hidden");
    openOriginalEl.removeAttribute("href");
    return;
  }
  const source = documentData.image_url;
  const lower = (documentData.source_file || "").toLowerCase();
  if (lower.endsWith(".pdf")) {
    previewFrameEl.innerHTML = `<iframe class="preview-pdf" src="${source}" title="Tarjeta escaneada"></iframe>`;
  } else {
    previewFrameEl.innerHTML = `<img class="preview-image" src="${source}" alt="Tarjeta escaneada" />`;
  }
  openOriginalEl.href = source;
  openOriginalEl.classList.remove("hidden");
}

function fillForm(contact) {
  const email = primaryMethod(contact, ["email"]);
  const mobile = primaryMethod(contact, ["mobile"]);
  const phone = primaryMethod(contact, ["phone"]);
  contactFormEl.elements.full_name.value = contact.full_name || "";
  contactFormEl.elements.first_name.value = contact.first_name || "";
  contactFormEl.elements.last_name.value = contact.last_name || "";
  contactFormEl.elements.company.value = contact.company || "";
  contactFormEl.elements.job_title.value = contact.job_title || "";
  contactFormEl.elements.department.value = contact.department || "";
  contactFormEl.elements.email.value = email;
  contactFormEl.elements.mobile.value = mobile;
  contactFormEl.elements.phone.value = phone;
  contactFormEl.elements.website.value = contact.website || "";
  contactFormEl.elements.linkedin.value = contact.linkedin || "";
  contactFormEl.elements.address.value = contact.address || "";
  contactFormEl.elements.city.value = contact.city || "";
  contactFormEl.elements.province.value = contact.province || "";
  contactFormEl.elements.postal_code.value = contact.postal_code || "";
  contactFormEl.elements.country.value = contact.country || "";
  contactFormEl.elements.confidence.value = contact.confidence ?? "";
  contactFormEl.elements.notes.value = contact.notes || "";
  contactFormEl.elements.warnings.value = (contact.warnings || []).join("\n");
}

function renderDetail(detail) {
  state.activeDetail = detail;
  state.activeContactId = detail.contact.contact_id;
  detailTitleEl.textContent = detail.contact.full_name || detail.contact.company || "Detalle";
  fillForm(detail.contact);
  renderPreview(detail.document);
  ocrMarkdownEl.textContent = detail.ocr.markdown || "Sin OCR disponible.";
  saveButton.disabled = false;
}

function buildMethodsFromForm() {
  const email = contactFormEl.elements.email.value.trim();
  const mobile = contactFormEl.elements.mobile.value.trim();
  const phone = contactFormEl.elements.phone.value.trim();
  const website = contactFormEl.elements.website.value.trim();
  const linkedin = contactFormEl.elements.linkedin.value.trim();
  const methods = [];
  if (email) methods.push({ method_type: "email", raw_value: email, normalized_value: email.toLowerCase(), is_primary: true });
  if (mobile) methods.push({ method_type: "mobile", raw_value: mobile, normalized_value: mobile, is_primary: true });
  if (phone) methods.push({ method_type: "phone", raw_value: phone, normalized_value: phone, is_primary: true });
  if (website) methods.push({ method_type: "website", raw_value: website, normalized_value: website, is_primary: true });
  if (linkedin) methods.push({ method_type: "linkedin", raw_value: linkedin, normalized_value: linkedin, is_primary: true });
  return methods;
}

async function loadDashboard() {
  const summary = await getJson("/api/dashboard/summary");
  renderMetrics(summary);
  const query = searchEl.value.trim();
  const contacts = await getJson(`/api/contacts?limit=200${query ? `&search=${encodeURIComponent(query)}` : ""}`);
  renderContacts(contacts);
}

async function openContact(contactId) {
  const detail = await getJson(`/api/contacts/${contactId}`);
  renderDetail(detail);
  renderContacts({ total_count: state.contacts.length, items: state.contacts });
}

contactsEl.addEventListener("click", async (event) => {
  const openButton = event.target.closest("[data-open-id]");
  if (openButton) {
    await openContact(Number(openButton.dataset.openId));
    return;
  }
  const deleteButton = event.target.closest("[data-delete-id]");
  if (deleteButton) {
    const contactId = Number(deleteButton.dataset.deleteId);
    await getJson(`/api/contacts/${contactId}/delete`, { method: "POST" });
    state.selectedIds.delete(contactId);
    if (state.activeContactId === contactId) {
      state.activeContactId = null;
      state.activeDetail = null;
      detailTitleEl.textContent = "Selecciona un contacto";
      previewFrameEl.innerHTML = '<p class="empty-state">La tarjeta escaneada aparecera aqui.</p>';
      openOriginalEl.classList.add("hidden");
      ocrMarkdownEl.textContent = "Selecciona un contacto para ver el OCR.";
      contactFormEl.reset();
      saveButton.disabled = true;
    }
    await loadDashboard();
  }
});

contactsEl.addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-select-id]");
  if (!checkbox) return;
  const contactId = Number(checkbox.dataset.selectId);
  if (checkbox.checked) {
    state.selectedIds.add(contactId);
  } else {
    state.selectedIds.delete(contactId);
  }
  updateActionButtons();
});

selectAllEl.addEventListener("change", () => {
  if (selectAllEl.checked) {
    state.contacts.forEach((contact) => state.selectedIds.add(contact.contact_id));
  } else {
    state.contacts.forEach((contact) => state.selectedIds.delete(contact.contact_id));
  }
  renderContacts({ total_count: state.contacts.length, items: state.contacts });
});

searchEl.addEventListener("input", () => {
  window.clearTimeout(searchEl._timer);
  searchEl._timer = window.setTimeout(loadDashboard, 250);
});

processButton.addEventListener("click", async () => {
  processButton.disabled = true;
  statusEl.textContent = "Procesando...";
  try {
    await getJson("/api/pipeline/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "new_or_changed" }),
    });
    await loadDashboard();
  } finally {
    processButton.disabled = false;
  }
});

saveButton.addEventListener("click", async () => {
  if (!state.activeDetail) return;
  saveButton.disabled = true;
  try {
    await getJson(`/api/contacts/${state.activeDetail.contact.contact_id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: contactFormEl.elements.full_name.value.trim() || null,
        first_name: contactFormEl.elements.first_name.value.trim() || null,
        last_name: contactFormEl.elements.last_name.value.trim() || null,
        company: contactFormEl.elements.company.value.trim() || null,
        job_title: contactFormEl.elements.job_title.value.trim() || null,
        department: contactFormEl.elements.department.value.trim() || null,
        website: contactFormEl.elements.website.value.trim() || null,
        linkedin: contactFormEl.elements.linkedin.value.trim() || null,
        address: contactFormEl.elements.address.value.trim() || null,
        city: contactFormEl.elements.city.value.trim() || null,
        province: contactFormEl.elements.province.value.trim() || null,
        postal_code: contactFormEl.elements.postal_code.value.trim() || null,
        country: contactFormEl.elements.country.value.trim() || null,
        notes: contactFormEl.elements.notes.value.trim() || null,
        confidence: contactFormEl.elements.confidence.value === "" ? null : Number(contactFormEl.elements.confidence.value),
        warnings: contactFormEl.elements.warnings.value
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
        contact_methods: buildMethodsFromForm(),
      }),
    });
    await loadDashboard();
    await openContact(state.activeDetail.contact.contact_id);
  } finally {
    saveButton.disabled = false;
  }
});

exportCsvButton.addEventListener("click", async () => {
  await downloadSelection("/api/exports/outlook.csv", "outlook-selected.csv");
});

exportVcfButton.addEventListener("click", async () => {
  await downloadSelection("/api/exports/contacts.vcf", "contacts-selected.vcf");
});

loadDashboard().catch((error) => {
  statusEl.textContent = error.message;
});
