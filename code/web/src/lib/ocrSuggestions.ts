const emailPattern = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;
const urlPattern = /\b(?:https?:\/\/)?(?:www\.)?[A-Z0-9.-]+\.[A-Z]{2,}(?:\/[^\s]*)?\b/gi;
const phonePattern = /(?:\+?\d[\d\s()./-]{6,}\d)/g;

function unique(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}

export function extractOcrSuggestions(markdown: string) {
  const lines = unique(
    markdown
      .split(/\r?\n/)
      .map((line) => line.replace(/^#+\s*/, "").trim())
      .filter((line) => line && !line.startsWith("![") && !line.startsWith("[tbl-")),
  );

  const emails = unique(markdown.match(emailPattern) ?? []).map((value) => value.toLowerCase());
  const urls = unique(
    (markdown.match(urlPattern) ?? []).filter((value) => !value.includes("@")),
  ).map((value) => (value.startsWith("http") ? value : `https://${value}`));
  const phones = unique(markdown.match(phonePattern) ?? []);

  const rankedTextLines = lines.filter((line) => line.length > 3 && line.length < 80);
  const nameCandidates = rankedTextLines.filter((line) => !/\d{4,}/.test(line) && line.split(" ").length >= 2 && line.split(" ").length <= 5).slice(0, 8);
  const companyCandidates = rankedTextLines.filter((line) => /s\.l\.|sl|sa|group|solutions|consulting|studio|corp|empresa|company/i.test(line) || line === line.toUpperCase()).slice(0, 8);
  const titleCandidates = rankedTextLines.filter((line) => /director|manager|sales|ventas|ceo|cto|marketing|engineer|responsable|consultor/i.test(line)).slice(0, 8);
  const addressCandidates = rankedTextLines.filter((line) => /calle|c\/|avenida|avda|plaza|street|road|paseo|poligono/i.test(line)).slice(0, 8);

  return {
    emails,
    urls,
    phones,
    lines: rankedTextLines.slice(0, 12),
    nameCandidates,
    companyCandidates,
    titleCandidates,
    addressCandidates,
  };
}
