import { useState } from 'react';
import './index.css';
import { 
  ShieldAlert, 
  Database, 
  KeyRound, 
  Terminal, 
  Lock, 
  CheckCircle2, 
  XCircle, 
  RefreshCw,
  Clock,
  Radio
} from 'lucide-react';

interface AuditEvent {
  id: string;
  timestamp: string;
  type: 'VERIFY_SUCCESS' | 'TAMPER_BLOCKED' | 'KEY_ROTATE' | 'MERKLE_AUDIT';
  details: string;
  target: string;
  status: 'SUCCESS' | 'BLOCKED';
}

const INITIAL_AUDIT_LOGS: AuditEvent[] = [
  {
    id: "evt-9481",
    timestamp: "18:14:35",
    type: "TAMPER_BLOCKED",
    details: "AEAD authentication tag mismatch on block #004. Decryption rejected.",
    target: "vault/financial_q3.enc",
    status: "BLOCKED"
  },
  {
    id: "evt-9480",
    timestamp: "18:12:48",
    type: "VERIFY_SUCCESS",
    details: "Post-quantum hybrid signature verified (Ed25519 + Dilithium3).",
    target: "keys/mk-a52bbfc1",
    status: "SUCCESS"
  },
  {
    id: "evt-9479",
    timestamp: "18:11:02",
    type: "KEY_ROTATE",
    details: "Cascade key rotation triggered. 12 data keys re-wrapped client-side.",
    target: "keystore/vault.keystore",
    status: "SUCCESS"
  },
  {
    id: "evt-9478",
    timestamp: "18:05:19",
    type: "MERKLE_AUDIT",
    details: "O(log n) tree consistency audit verified against root hash 2d2bdc...",
    target: "cluster/node-eu-west-1",
    status: "SUCCESS"
  }
];

export default function App() {
  const [auditLogs, setAuditLogs] = useState<AuditEvent[]>(INITIAL_AUDIT_LOGS);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      const newEvt: AuditEvent = {
        id: `evt-${Math.floor(1000 + Math.random() * 9000)}`,
        timestamp: new Date().toLocaleTimeString(),
        type: "MERKLE_AUDIT",
        details: "Automated tamper-evident audit proof verified successfully.",
        target: "storage/manifest_delta.enc",
        status: "SUCCESS"
      };
      setAuditLogs([newEvt, ...auditLogs.slice(0, 5)]);
      setIsRefreshing(false);
    }, 400);
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '2rem 1.5rem' }}>
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ 
            width: '44px', 
            height: '44px', 
            borderRadius: '10px', 
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 24px rgba(16, 185, 129, 0.4)'
          }}>
            <ShieldAlert size={24} color="#040810" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h1 style={{ fontSize: '1.45rem', fontWeight: 700, letterSpacing: '-0.02em' }}>CryptaVault</h1>
              <span className="badge badge-emerald">Admin & SOC Console</span>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Zero-Knowledge Multi-Backend Security Operations & Infrastructure</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button 
            onClick={handleRefresh}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-main)',
              padding: '0.55rem 1rem',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              fontSize: '0.85rem'
            }}
          >
            <RefreshCw size={14} className={isRefreshing ? "spin" : ""} />
            <span>Poll Audit Events</span>
          </button>
        </div>
      </header>

      {/* Metric Counters */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
            <span>ZK Boundary Integrity</span>
            <Lock size={16} color="#34d399" />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#34d399' }}>100.0%</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>Plaintext never stored on backend</div>
        </div>

        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
            <span>Post-Quantum Ready Nodes</span>
            <Radio size={16} color="#00f0ff" />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--cyan-glow)' }}>ML-KEM-768</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>NIST FIPS 203 Lattice KEM Active</div>
        </div>

        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
            <span>Tamper Attempts Blocked</span>
            <ShieldAlert size={16} color="#f43f5e" />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f43f5e' }}>24 / 24</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>100% Fail-closed AEAD tag defense</div>
        </div>

        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
            <span>Cloud Storage Targets</span>
            <Database size={16} color="#c084fc" />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#c084fc' }}>4 Backends</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>Supabase • AWS S3 • Cloudflare R2 • MinIO</div>
        </div>
      </div>

      {/* Real-time Audit Table */}
      <section className="glass-panel" style={{ padding: '1.75rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Clock size={18} color="var(--cyan-glow)" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Zero-Knowledge Audit Trail & Event Stream</h2>
          </div>
          <span className="badge badge-emerald">Live Stream</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                <th style={{ padding: '0.75rem 1rem' }}>Event ID</th>
                <th style={{ padding: '0.75rem 1rem' }}>Time</th>
                <th style={{ padding: '0.75rem 1rem' }}>Action Type</th>
                <th style={{ padding: '0.75rem 1rem' }}>Target Artifact</th>
                <th style={{ padding: '0.75rem 1rem' }}>Cryptographic Verification</th>
                <th style={{ padding: '0.75rem 1rem' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((log) => (
                <tr key={log.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{log.id}</td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-dim)' }}>{log.timestamp}</td>
                  <td style={{ padding: '0.85rem 1rem' }}>
                    <span className="mono-tag" style={{ color: log.type === 'TAMPER_BLOCKED' ? '#f43f5e' : '#38bdf8' }}>
                      {log.type}
                    </span>
                  </td>
                  <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{log.target}</td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-muted)', fontSize: '0.825rem' }}>{log.details}</td>
                  <td style={{ padding: '0.85rem 1rem' }}>
                    {log.status === 'SUCCESS' ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: '#34d399', fontSize: '0.8rem', fontWeight: 600 }}>
                        <CheckCircle2 size={14} /> VALID
                      </span>
                    ) : (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: '#f43f5e', fontSize: '0.8rem', fontWeight: 600 }}>
                        <XCircle size={14} /> BLOCKED
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Key Hierarchy Architecture Card */}
      <section className="glass-panel" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.25rem' }}>
          <KeyRound size={20} color="#f59e0b" />
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>3-Tier Cryptographic Key Hierarchy</h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.25rem', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span className="badge badge-purple">Tier 1 • Root</span>
              <strong style={{ fontSize: '0.9rem' }}>Master Key (MK)</strong>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Client-derived root key via Argon2id (64MB memory-hard). Never transmitted over network or saved to database. Protected by BIP-39 mnemonic.
            </p>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.25rem', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span className="badge badge-cyan">Tier 2 • Intermediate</span>
              <strong style={{ fontSize: '0.9rem' }}>Storage Key (SK)</strong>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Per-vault intermediate key wrapped by Master Key. Allows fast cascade re-wrapping without decrypting underlying bulk data.
            </p>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.25rem', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span className="badge badge-emerald">Tier 3 • Operational</span>
              <strong style={{ fontSize: '0.9rem' }}>Data Key (DK)</strong>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Unique ephemeral key generated per file / chunk. Encrypted via AES-256-GCM / ChaCha20-Poly1305. Destroyed with memory zeroing.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Terminal size={14} />
          <span>CryptaVault CLI Audit: <code>.venv/bin/cryptavault merkle --dir docs</code></span>
        </div>
        <span>Zero-Knowledge Multi-Cloud Storage Architecture</span>
      </footer>
    </div>
  );
}
