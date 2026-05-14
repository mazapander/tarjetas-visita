import { extractOcrSuggestions } from "../lib/ocrSuggestions";

interface OcrAssistPanelProps {
  markdown: string;
  onApplyField: (field: string, value: string) => void;
}

function SuggestionGroup({
  title,
  items,
  onPick,
}: {
  title: string;
  items: string[];
  onPick: (value: string) => void;
}) {
  if (!items.length) return null;
  return (
    <section className="suggestion-group">
      <h4>{title}</h4>
      <div className="chip-list">
        {items.map((item) => (
          <button key={`${title}:${item}`} type="button" className="chip-button" onClick={() => onPick(item)}>
            {item}
          </button>
        ))}
      </div>
    </section>
  );
}

export function OcrAssistPanel({ markdown, onApplyField }: OcrAssistPanelProps) {
  const suggestions = extractOcrSuggestions(markdown);

  return (
    <div className="ocr-assist">
      <div className="ocr-assist-header">
        <div>
          <p className="eyebrow">Asistente OCR</p>
          <h3>Importar entidades detectadas</h3>
        </div>
      </div>
      <SuggestionGroup title="Nombre" items={suggestions.nameCandidates} onPick={(value) => onApplyField("full_name", value)} />
      <SuggestionGroup title="Empresa" items={suggestions.companyCandidates} onPick={(value) => onApplyField("company", value)} />
      <SuggestionGroup title="Cargo" items={suggestions.titleCandidates} onPick={(value) => onApplyField("job_title", value)} />
      <SuggestionGroup title="Direccion" items={suggestions.addressCandidates} onPick={(value) => onApplyField("address", value)} />
      <SuggestionGroup title="Emails" items={suggestions.emails} onPick={(value) => onApplyField("email", value)} />
      <SuggestionGroup title="Movil / telefono" items={suggestions.phones} onPick={(value) => onApplyField("mobile", value)} />
      <SuggestionGroup title="Web / LinkedIn" items={suggestions.urls} onPick={(value) => onApplyField(value.includes("linkedin") ? "linkedin" : "website", value)} />
      <details className="ocr-details">
        <summary>OCR completo</summary>
        <pre>{markdown || "Sin OCR disponible."}</pre>
      </details>
    </div>
  );
}
