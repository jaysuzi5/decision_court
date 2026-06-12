import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchGallery, type GalleryItem } from "../lib/api";

export default function Gallery() {
  const [items, setItems] = useState<GalleryItem[] | null>(null);

  useEffect(() => {
    fetchGallery().then(setItems);
  }, []);

  return (
    <div className="page wide">
      <header className="bench">
        <span className="gavel-sm">⚖</span> The Gallery — verdicts people chose to share
      </header>

      {items === null && <p style={{ textAlign: "center" }}>Loading…</p>}
      {items && items.length === 0 && (
        <p style={{ textAlign: "center", color: "var(--muted)" }}>
          No public verdicts yet. <Link to="/">Be the first to put a decision on trial.</Link>
        </p>
      )}

      <div className="gallery-grid">
        {items?.map((it) => (
          <Link key={it.token} to={`/share/${it.token}`} className="gallery-card">
            <div className="g-decision">{it.decision}</div>
            <div className="g-rec">{it.recommendation}</div>
            <div className="g-more">Read the verdict →</div>
          </Link>
        ))}
      </div>

      <p className="disclaimer" style={{ textAlign: "center" }}>
        <Link to="/">Put your own decision on trial</Link>
      </p>
    </div>
  );
}
