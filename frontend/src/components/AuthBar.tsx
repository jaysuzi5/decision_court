import { Link } from "react-router-dom";
import { googleLoginUrl, logout, type Me } from "../lib/api";

export default function AuthBar({ me }: { me: Me | null }) {
  if (!me) return <div className="authbar" />;

  if (!me.authenticated) {
    return (
      <div className="authbar">
        {me.oauth_enabled && (
          <a className="g-signin" href={googleLoginUrl}>
            <span className="g-mark">G</span> Sign in with Google
          </a>
        )}
      </div>
    );
  }

  async function signOut() {
    await logout();
    window.location.href = "/";
  }

  return (
    <div className="authbar">
      <Link to="/me" className="docket-link">My docket</Link>
      {me.picture ? (
        <img className="avatar" src={me.picture} alt="" referrerPolicy="no-referrer" />
      ) : (
        <span className="avatar avatar-fallback">{(me.name || "?")[0]}</span>
      )}
      <button className="signout" onClick={signOut}>Sign out</button>
    </div>
  );
}
