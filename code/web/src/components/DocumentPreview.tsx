interface DocumentPreviewProps {
  sourceFile?: string;
  imageUrl?: string;
}

export function DocumentPreview({ sourceFile, imageUrl }: DocumentPreviewProps) {
  if (!imageUrl) {
    return <div className="preview-empty">La tarjeta escaneada aparecera aqui.</div>;
  }

  const lower = (sourceFile ?? "").toLowerCase();
  return (
    <div className="preview-stack">
      <div className="preview-frame">
        {lower.endsWith(".pdf") ? (
          <iframe className="preview-pdf" src={imageUrl} title="Tarjeta escaneada" />
        ) : (
          <img className="preview-image" src={imageUrl} alt="Tarjeta escaneada" />
        )}
      </div>
      <a className="secondary-link" href={imageUrl} target="_blank" rel="noreferrer">
        Abrir original
      </a>
    </div>
  );
}
