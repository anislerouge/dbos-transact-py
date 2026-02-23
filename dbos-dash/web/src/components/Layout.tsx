import { Link } from 'react-router-dom'
import { ReactNode } from 'react'

const styles = {
  container: { display: 'flex', minHeight: '100vh' } as const,
  sidebar: {
    width: 220, background: '#1a1a2e', color: '#fff', padding: '20px 0',
    display: 'flex', flexDirection: 'column' as const,
  },
  logo: { padding: '0 20px 20px', fontSize: 18, fontWeight: 700, borderBottom: '1px solid #333' },
  nav: { padding: '20px 0', display: 'flex', flexDirection: 'column' as const, gap: 4 },
  link: {
    color: '#ccc', textDecoration: 'none', padding: '8px 20px', fontSize: 14,
    display: 'block', transition: 'background 0.2s',
  },
  main: { flex: 1, padding: 24 },
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={styles.container}>
      <aside style={styles.sidebar}>
        <div style={styles.logo}>DBOS Dash</div>
        <nav style={styles.nav}>
          <Link to="/" style={styles.link}>Dashboard</Link>
          <Link to="/workflows" style={styles.link}>Workflows</Link>
          <Link to="/queues" style={styles.link}>Queues</Link>
        </nav>
      </aside>
      <main style={styles.main}>{children}</main>
    </div>
  )
}
