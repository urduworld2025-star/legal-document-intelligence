import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import styles from "./NavBar.module.css";

export function NavBar() {
  const { user, logout } = useAuth();

  return (
    <nav className={styles.nav}>
      <Link to={user ? "/dashboard" : "/"} className={styles.brand}>
        <span className={styles.monogram} aria-hidden="true">
          LI
        </span>
        <span className={styles.brandText}>Legal Document Intelligence</span>
      </Link>
      <div className={styles.links}>
        {user && (
          <>
            <NavLink
              to="/dashboard"
              className={({ isActive }) => `${styles.link} ${isActive ? styles.linkActive : ""}`}
            >
              Matters
            </NavLink>
            <NavLink
              to="/quick-analyze"
              className={({ isActive }) => `${styles.link} ${isActive ? styles.linkActive : ""}`}
            >
              Quick Analyze (not saved)
            </NavLink>
            {user.role === "attorney" && (
              <NavLink
                to="/admin"
                className={({ isActive }) => `${styles.link} ${isActive ? styles.linkActive : ""}`}
              >
                Admin
              </NavLink>
            )}
          </>
        )}
      </div>
      {user && (
        <div className={styles.userArea}>
          <span className={styles.userInfo}>
            {user.name} <span className={styles.role}>({user.role})</span>
          </span>
          <button type="button" className={styles.logoutButton} onClick={() => logout()}>
            Log out
          </button>
        </div>
      )}
    </nav>
  );
}
