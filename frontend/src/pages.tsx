import { FormEvent, useEffect, useState, type ReactNode } from "react";
import {
  Link,
  NavLink,
  useLocation,
  useMatch,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { SESSION_EXPIRED_EVENT, api, errorText } from "./api/client";
import type { SessionBody } from "./api/types";
import { CASE_EVENT } from "./workspace/context";
import { TABS } from "./workspace/WorkspaceLayout";
import { ErrorBox, Panel } from "./ui";

export function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      await api.login(String(form.get("username")), String(form.get("password")));
      navigate("/");
    } catch (err) {
      setError(errorText(err, "Sign-in failed."));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="auth-layout">
      <section className="auth-story">
        <div className="brand-mark">VAGEXA</div>
        <h1>Financial crime intelligence for investigators.</h1>
        <p>
          VAGEXA traces money across the accounts in a case, examines the domains and addresses
          connected to it, and shows which links the stored evidence actually supports.
        </p>
        <ol>
          <li>
            Follow a payment through intermediary accounts, with every hop tied to a statement row.
          </li>
          <li>See fan-in and fan-out rule matches with the rows that triggered them.</li>
          <li>Inspect DNS and hosting observations, kept with their observation times.</li>
          <li>
            Read cross-domain links as supported, corroborated, or unresolved, never as proof of
            ownership.
          </li>
        </ol>
        <p className="small">
          This deployment holds synthetic demonstration data only. Nothing shown is an official
          record.
        </p>
      </section>
      <section className="auth-form">
        <form className="panel" onSubmit={onSubmit}>
          <h1>Sign in</h1>
          <p className="lede" style={{ marginBottom: 14 }}>
            Authorised users only. Accounts are issued by an administrator.
          </p>
          {params.get("expired") ? (
            <p className="notice caution">Your session ended. Sign in again to continue.</p>
          ) : null}
          <label className="field">
            Username
            <input name="username" autoComplete="username" required />
          </label>
          <label className="field">
            Password
            <input name="password" type="password" autoComplete="current-password" required />
          </label>
          {error ? <ErrorBox message={error} /> : null}
          <button
            className="primary"
            type="submit"
            disabled={pending}
            style={{ marginTop: 10, width: "100%" }}
          >
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </div>
  );
}

export function Shell({
  children,
  session,
  onLogout,
}: {
  children: ReactNode;
  session: SessionBody;
  onLogout: () => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const match = useMatch("/cases/:caseId/*");
  const caseId = match?.params.caseId && match.params.caseId !== "new" ? match.params.caseId : null;
  const [opened, setOpened] = useState<{ id: string; reference: string } | null>(null);

  useEffect(() => {
    function onCase(event: Event) {
      const detail = (event as CustomEvent<{ id: string; reference: string }>).detail;
      setOpened(detail);
    }
    function onExpired() {
      navigate("/login?expired=1", { replace: true });
    }
    window.addEventListener(CASE_EVENT, onCase);
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => {
      window.removeEventListener(CASE_EVENT, onCase);
      window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
    };
  }, [navigate]);

  const canOpen = session.permissions.includes("cases.create");
  const reference = opened && opened.id === caseId ? opened.reference : null;

  return (
    <div className="app-shell">
      <aside className="rail">
        <div className="rail-brand">
          <div className="brand-mark">VAGEXA</div>
          <span className="brand-sub">Financial crime intelligence</span>
        </div>
        <nav className="rail-section" aria-label="Primary">
          <NavLink to="/" end>
            Overview
          </NavLink>
          <NavLink to="/cases" end>
            Investigations
          </NavLink>
          {canOpen ? <NavLink to="/cases/new">Open an investigation</NavLink> : null}
        </nav>
        {caseId ? (
          <nav className="rail-section" aria-label="Current investigation">
            <div className="rail-title">Current investigation</div>
            <div className="rail-case">{reference ?? "Loading…"}</div>
            {TABS.map((tab) => {
              const to = `/cases/${caseId}${tab.path ? `/${tab.path}` : ""}`;
              const active = tab.path
                ? location.pathname.startsWith(to)
                : location.pathname === to || location.pathname === `${to}/`;
              return (
                <Link key={tab.label} to={to} className={active ? "active" : ""}>
                  {tab.label}
                </Link>
              );
            })}
          </nav>
        ) : null}
        <div className="rail-foot">
          <div className="rail-user">
            <strong>{session.user.display_name}</strong>
            {session.roles.join(", ")} · {session.data_mode} mode
          </div>
          <NavLink to="/account">Account</NavLink>
          <button className="rail-link" type="button" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>
      <main>{children}</main>
    </div>
  );
}

export function NewCasePage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      const created = await api.createCase({
        reference: String(form.get("reference")),
        title: String(form.get("title")),
        opened_on: String(form.get("opened_on")),
      });
      navigate(`/cases/${created.id}`);
    } catch (err) {
      setError(errorText(err, "The investigation could not be opened."));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stack" style={{ maxWidth: 560 }}>
      <div>
        <h1>Open an investigation</h1>
        <p className="lede">
          This deployment stores new investigations as synthetic. They are not official files.
        </p>
      </div>
      <Panel>
        <form onSubmit={onSubmit}>
          <label className="field">
            Reference
            <input name="reference" required maxLength={64} />
          </label>
          <label className="field">
            Title
            <input name="title" required maxLength={200} />
          </label>
          <label className="field">
            Opened on
            <input
              name="opened_on"
              type="date"
              required
              defaultValue={new Date().toISOString().slice(0, 10)}
            />
          </label>
          {error ? <ErrorBox message={error} /> : null}
          <button className="primary" type="submit" disabled={pending}>
            {pending ? "Saving…" : "Create investigation"}
          </button>
        </form>
      </Panel>
    </div>
  );
}

export function AccountPage() {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      await api.changePassword(
        String(form.get("current_password")),
        String(form.get("new_password")),
      );
      setMessage("Password changed. Other sessions were signed out.");
    } catch (err) {
      setError(errorText(err, "The password could not be changed."));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stack" style={{ maxWidth: 560 }}>
      <div>
        <h1>Account</h1>
        <p className="lede">
          Change your password. There is no public registration or email reset.
        </p>
      </div>
      <Panel>
        <form onSubmit={onSubmit}>
          <label className="field">
            Current password
            <input
              name="current_password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          <label className="field">
            New password
            <input
              name="new_password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          {error ? <ErrorBox message={error} /> : null}
          {message ? <p className="notice">{message}</p> : null}
          <button className="primary" type="submit" disabled={pending}>
            {pending ? "Saving…" : "Change password"}
          </button>
        </form>
      </Panel>
    </div>
  );
}

export function ForbiddenPage() {
  return (
    <div className="stack">
      <h1>Not allowed</h1>
      <p className="lede">
        Your role does not allow that action. Hiding a control is not what stopped it.
      </p>
      <Link to="/cases">Back to investigations</Link>
    </div>
  );
}

export function useSession() {
  const [session, setSession] = useState<SessionBody | null | undefined>(undefined);

  useEffect(() => {
    api
      .me()
      .then(setSession)
      .catch(() => setSession(null));
  }, []);

  return session;
}
