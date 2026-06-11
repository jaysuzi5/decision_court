import React from "react";

// Minimal renderer: paragraphs + **bold** + headings. No external markdown dep.
function inline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? (
      <strong key={i}>{p.slice(2, -2)}</strong>
    ) : (
      <React.Fragment key={i}>{p}</React.Fragment>
    )
  );
}

export default function RichText({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/);
  return (
    <>
      {blocks.map((b, i) => {
        const t = b.trim();
        if (!t) return null;
        if (t.startsWith("### ")) return <h4 key={i}>{inline(t.slice(4))}</h4>;
        if (t.startsWith("## ")) return <h3 key={i}>{inline(t.slice(3))}</h3>;
        return (
          <p key={i}>
            {t.split("\n").map((line, j) => (
              <React.Fragment key={j}>
                {j > 0 && <br />}
                {inline(line)}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
}
