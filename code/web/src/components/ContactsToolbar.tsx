interface ContactsToolbarProps {
  search: string;
  selectedCount: number;
  processing: boolean;
  onSearchChange: (value: string) => void;
  onProcess: () => void;
  onExportCsv: () => void;
  onExportVcf: () => void;
}

export function ContactsToolbar({
  search,
  selectedCount,
  processing,
  onSearchChange,
  onProcess,
  onExportCsv,
  onExportVcf,
}: ContactsToolbarProps) {
  const suffix = selectedCount ? ` (${selectedCount})` : "";
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Extraccion local</p>
        <h1>Tarjetas de visita</h1>
      </div>
      <div className="topbar-actions">
        <input
          className="search-input"
          type="search"
          placeholder="Buscar nombre, empresa, email..."
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
        <button type="button" onClick={onProcess} disabled={processing}>
          {processing ? "Procesando..." : "Procesar"}
        </button>
        <button type="button" className="secondary-button" onClick={onExportCsv}>
          {`Exportar CSV${suffix}`}
        </button>
        <button type="button" className="secondary-button" onClick={onExportVcf}>
          {`Exportar VCF${suffix}`}
        </button>
      </div>
    </header>
  );
}
