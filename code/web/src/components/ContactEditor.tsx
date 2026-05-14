import { useEffect, useState, type FormEvent } from "react";
import type { ContactDetailResponse, ContactFormValues, ContactUpdatePayload } from "../app/types";
import { DocumentPreview } from "./DocumentPreview";
import { OcrAssistPanel } from "./OcrAssistPanel";

const emptyValues: ContactFormValues = {
  full_name: "",
  first_name: "",
  last_name: "",
  company: "",
  job_title: "",
  department: "",
  email: "",
  mobile: "",
  phone: "",
  website: "",
  linkedin: "",
  address: "",
  city: "",
  province: "",
  postal_code: "",
  country: "",
  confidence: "",
  notes: "",
  warnings: "",
};

function methodValue(detail: ContactDetailResponse, methodType: string): string {
  return detail.contact.contact_methods.find((item) => item.method_type === methodType)?.normalized_value ?? "";
}

function detailToForm(detail: ContactDetailResponse): ContactFormValues {
  return {
    full_name: detail.contact.full_name ?? "",
    first_name: detail.contact.first_name ?? "",
    last_name: detail.contact.last_name ?? "",
    company: detail.contact.company ?? "",
    job_title: detail.contact.job_title ?? "",
    department: detail.contact.department ?? "",
    email: methodValue(detail, "email"),
    mobile: methodValue(detail, "mobile"),
    phone: methodValue(detail, "phone"),
    website: detail.contact.website ?? methodValue(detail, "website"),
    linkedin: detail.contact.linkedin ?? methodValue(detail, "linkedin"),
    address: detail.contact.address ?? "",
    city: detail.contact.city ?? "",
    province: detail.contact.province ?? "",
    postal_code: detail.contact.postal_code ?? "",
    country: detail.contact.country ?? "",
    confidence: detail.contact.confidence == null ? "" : String(detail.contact.confidence),
    notes: detail.contact.notes ?? "",
    warnings: detail.contact.warnings.join("\n"),
  };
}

function formToPayload(values: ContactFormValues): ContactUpdatePayload {
  const contactMethods = [];
  if (values.email.trim()) {
    contactMethods.push({
      method_type: "email",
      raw_value: values.email.trim(),
      normalized_value: values.email.trim().toLowerCase(),
      is_primary: true,
    });
  }
  if (values.mobile.trim()) {
    contactMethods.push({
      method_type: "mobile",
      raw_value: values.mobile.trim(),
      normalized_value: values.mobile.trim(),
      is_primary: true,
    });
  }
  if (values.phone.trim()) {
    contactMethods.push({
      method_type: "phone",
      raw_value: values.phone.trim(),
      normalized_value: values.phone.trim(),
      is_primary: true,
    });
  }
  if (values.website.trim()) {
    contactMethods.push({
      method_type: "website",
      raw_value: values.website.trim(),
      normalized_value: values.website.trim(),
      is_primary: true,
    });
  }
  if (values.linkedin.trim()) {
    contactMethods.push({
      method_type: "linkedin",
      raw_value: values.linkedin.trim(),
      normalized_value: values.linkedin.trim(),
      is_primary: true,
    });
  }

  return {
    full_name: values.full_name.trim() || null,
    first_name: values.first_name.trim() || null,
    last_name: values.last_name.trim() || null,
    company: values.company.trim() || null,
    job_title: values.job_title.trim() || null,
    department: values.department.trim() || null,
    website: values.website.trim() || null,
    linkedin: values.linkedin.trim() || null,
    address: values.address.trim() || null,
    city: values.city.trim() || null,
    province: values.province.trim() || null,
    postal_code: values.postal_code.trim() || null,
    country: values.country.trim() || null,
    notes: values.notes.trim() || null,
    confidence: values.confidence.trim() ? Number(values.confidence) : null,
    warnings: values.warnings
      .split("\n")
      .map((warning) => warning.trim())
      .filter(Boolean),
    contact_methods: contactMethods,
  };
}

interface ContactEditorProps {
  detail: ContactDetailResponse | null;
  saving: boolean;
  onSave: (payload: ContactUpdatePayload) => Promise<void>;
}

export function ContactEditor({ detail, saving, onSave }: ContactEditorProps) {
  const [values, setValues] = useState<ContactFormValues>(emptyValues);

  useEffect(() => {
    setValues(detail ? detailToForm(detail) : emptyValues);
  }, [detail]);

  if (!detail) {
    return (
      <section className="panel detail-panel">
        <header className="detail-header">
          <div>
            <p className="eyebrow">Detalle</p>
            <h2>Selecciona un contacto</h2>
          </div>
        </header>
        <div className="detail-empty">Abre un registro desde la lista para ver la tarjeta, editar campos y reutilizar entidades detectadas en el OCR.</div>
      </section>
    );
  }

  const updateField = (field: keyof ContactFormValues, value: string) => {
    setValues((current) => ({ ...current, [field]: value }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSave(formToPayload(values));
  };

  return (
    <section className="panel detail-panel">
      <header className="detail-header">
        <div>
          <p className="eyebrow">Detalle</p>
          <h2>{detail.contact.full_name || detail.contact.company || "Contacto"}</h2>
        </div>
        <button type="submit" form="contact-editor-form" disabled={saving}>
          {saving ? "Guardando..." : "Guardar cambios"}
        </button>
      </header>

      <div className="detail-grid">
        <DocumentPreview sourceFile={detail.document.source_file} imageUrl={detail.document.image_url} />

        <form id="contact-editor-form" className="editor-form" onSubmit={submit}>
          <label>
            Nombre completo
            <input value={values.full_name} onChange={(event) => updateField("full_name", event.target.value)} />
          </label>
          <label>
            Nombre
            <input value={values.first_name} onChange={(event) => updateField("first_name", event.target.value)} />
          </label>
          <label>
            Apellidos
            <input value={values.last_name} onChange={(event) => updateField("last_name", event.target.value)} />
          </label>
          <label>
            Empresa
            <input value={values.company} onChange={(event) => updateField("company", event.target.value)} />
          </label>
          <label>
            Cargo
            <input value={values.job_title} onChange={(event) => updateField("job_title", event.target.value)} />
          </label>
          <label>
            Departamento
            <input value={values.department} onChange={(event) => updateField("department", event.target.value)} />
          </label>
          <label>
            Email
            <input value={values.email} onChange={(event) => updateField("email", event.target.value)} />
          </label>
          <label>
            Movil
            <input value={values.mobile} onChange={(event) => updateField("mobile", event.target.value)} />
          </label>
          <label>
            Telefono
            <input value={values.phone} onChange={(event) => updateField("phone", event.target.value)} />
          </label>
          <label>
            Web
            <input value={values.website} onChange={(event) => updateField("website", event.target.value)} />
          </label>
          <label>
            LinkedIn
            <input value={values.linkedin} onChange={(event) => updateField("linkedin", event.target.value)} />
          </label>
          <label className="full-span">
            Direccion
            <input value={values.address} onChange={(event) => updateField("address", event.target.value)} />
          </label>
          <label>
            Ciudad
            <input value={values.city} onChange={(event) => updateField("city", event.target.value)} />
          </label>
          <label>
            Provincia
            <input value={values.province} onChange={(event) => updateField("province", event.target.value)} />
          </label>
          <label>
            Codigo postal
            <input value={values.postal_code} onChange={(event) => updateField("postal_code", event.target.value)} />
          </label>
          <label>
            Pais
            <input value={values.country} onChange={(event) => updateField("country", event.target.value)} />
          </label>
          <label>
            Confianza
            <input value={values.confidence} onChange={(event) => updateField("confidence", event.target.value)} />
          </label>
          <label className="full-span">
            Notas
            <textarea rows={3} value={values.notes} onChange={(event) => updateField("notes", event.target.value)} />
          </label>
          <label className="full-span">
            Warnings
            <textarea rows={3} value={values.warnings} onChange={(event) => updateField("warnings", event.target.value)} />
          </label>
        </form>
      </div>

      <OcrAssistPanel markdown={detail.ocr.markdown} onApplyField={(field, value) => updateField(field as keyof ContactFormValues, value)} />
    </section>
  );
}
