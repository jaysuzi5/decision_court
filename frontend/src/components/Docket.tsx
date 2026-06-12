import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchDocket, fetchMe, type DocketItem } from "../lib/api";

export default function Docket() {
  const [items, setItems] = useState<DocketItem[] | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchMe().then((me) => {
      if (!me.authenticated) {
        navigate("/");
        return;
      }
      fetchDocket().then(setItems);
    });
  }, [navigate]);

  return (
    <div className="page wide">
      <header className="bench">
        <span className="gavel-sm">⚖</span> My Docket — your decisions on trial
      </header>

      {items === null && <p style={{ textAlign: "center" }}>Loading…</p>}
      {items && items.length === 0 && (
        <p style={{ textAlign: "center", color: "var(--muted)" }}>
          No cases yet. <Link to="/">Bring your first decision to court.</Link>
        </p>
      )}

      <div className="docket-list">
        {items?.map((it) => (
          <Link key={it.id} to={`/c/${it.id}`} className="docket-row">
            <div className="d-main">
              <div className="d-decision">{it.decision}</div>
              {it.recommendation && <div className="d-rec">{it.recommendation}</div>}
            </div>
            <div className={`d-status s-${it.status}`}>
              {it.status === "done" ? "Verdict" : "In progress"}
            </div>
          </Link>
        ))}
      </div>

      <p className="disclaimer" style={{ textAlign: "center" }}>
        <Link to="/">New case</Link>
      </p>
    </div>
  );
}
