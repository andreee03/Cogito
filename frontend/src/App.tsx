import { NavLink, Route, Routes, Link } from "react-router-dom";
import { useDemoMode } from "./hooks/useDemoMode";
import { ItemPage } from "./pages/ItemPage";
import { ListPage } from "./pages/ListPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SettingsPage } from "./pages/SettingsPage";
import { EmptyState } from "./components/ui";

const NAV = [
  {
    to: "/",
    label: "Ma liste",
    icon: <path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />,
  },
  {
    to: "/profil",
    label: "Mes goûts",
    icon: <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" />,
  },
  {
    to: "/reglages",
    label: "Réglages",
    icon: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
      </>
    ),
  },
];

export default function App() {
  const demo = useDemoMode();
  return (
    <div className="app">
      {demo && (
        <div className="demo-banner">
          Mode démo · données fictives — <Link to="/reglages">connecter le back-end</Link>
        </div>
      )}
      <header className="topbar">
        <Link to="/" className="logo" aria-label="Cogito, accueil">
          Cogito<span className="logo__dot">.</span>
        </Link>
        <nav className="topnav" aria-label="Navigation principale">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} className="topnav__link">
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="main">
        <Routes>
          <Route path="/" element={<ListPage />} />
          <Route path="/articles/:id" element={<ItemPage />} />
          <Route path="/profil" element={<ProfilePage />} />
          <Route path="/reglages" element={<SettingsPage />} />
          <Route
            path="*"
            element={
              <div className="page">
                <EmptyState title="Page introuvable" action={<Link className="btn btn--ghost" to="/">Retour à ma liste</Link>} />
              </div>
            }
          />
        </Routes>
      </main>

      <nav className="tabbar" aria-label="Navigation">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === "/"} className="tabbar__link">
            <svg viewBox="0 0 24 24" aria-hidden>
              {n.icon}
            </svg>
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
