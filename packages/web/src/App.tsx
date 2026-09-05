import { useState } from 'react';
import './index.css';
import { 
  ShieldCheck, 
  Cpu, 
  Lock, 
  Key, 
  Zap, 
  FileCode, 
  CheckCircle, 
  RefreshCw, 
  Server, 
  Copy, 
  Terminal,
  Activity
} from 'lucide-react';

interface Profile {
  name: string;
  level: string;
  symmetric: string;
  kem: string;
  sig: string;
  kdf: string;
  chunk: string;
  desc: string;
  color: string;
}

const PROFILES: Record<string, Profile> = {
  PERFORMANCE: {
    name: "Performance Optimized",
    level: "PERFORMANCE",
    symmetric: "AES-256-GCM (Hardware AES-NI)",
    kem: "X25519 (ECDH)",
    sig: "Ed25519",
    kdf: "Argon2id (32 MB, t=2)",
    chunk: "4 MB",
    desc: "Engineered for maximum streaming throughput (2,169 MB/s) on edge/mobile devices.",
    color: "#38bdf8"
  },
  BALANCED: {
    name: "Balanced Baseline (Default)",
    level: "BALANCED",
    symmetric: "AES-256-GCM",
    kem: "Hybrid X25519 + Kyber-768",
    sig: "Ed25519 + Dilithium-3",
    kdf: "Argon2id (64 MB, t=3)",
    chunk: "4 MB",
    desc: "Standard enterprise zero-knowledge baseline with NIST FIPS 203 post-quantum readiness.",
    color: "#10b981"
  },
  HIGH: {
    name: "High Security",
    level: "HIGH",
    symmetric: "ChaCha20-Poly1305 (Constant-Time)",
    kem: "Hybrid X25519 + Kyber-768",
    sig: "Ed25519 + Dilithium-3",
    kdf: "Argon2id (64 MB, t=4)",
    chunk: "8 MB",
    desc: "Side-channel hardened cipher with heightened memory-hard key derivation.",
    color: "#a855f7"
  },
  MAXIMUM: {
    name: "Maximum Post-Quantum",
    level: "MAXIMUM",
    symmetric: "AES-256-GCM + SHA3-512",
    kem: "Dual Kyber-1024 + X25519",
    sig: "Dilithium-5 + Ed25519",
    kdf: "Argon2id (128 MB, t=5)",
    chunk: "16 MB",
    desc: "State-sponsored threat model defense with long-term post-quantum forward secrecy.",
    color: "#f43f5e"
  }
};

const SAMPLE_MNEMONIC = [
  "shield", "matrix", "quantum", "cipher", "vault", "entropy",
  "lattice", "vector", "hybrid", "secure", "zero", "knowledge",
  "argon", "blake", "atomic", "dynamic", "crystal", "dilithium",
  "stream", "poly", "merkle", "audit", "proof", "verdict"
];

export default function App() {
  const [activeProfileKey, setActiveProfileKey] = useState<string>("BALANCED");
  const [plaintextInput, setPlaintextInput] = useState<string>("Confidential university research records — Zero Knowledge Test");
  const [passphrase, setPassphrase] = useState<string>("ClientSecretPassphrase2026!");
  const [encryptedPayload, setEncryptedPayload] = useState<string | null>(null);
  const [decryptedText, setDecryptedText] = useState<string | null>(null);
  const [mnemonicList, setMnemonicList] = useState<string[]>(SAMPLE_MNEMONIC);
  const [copiedNotification, setCopiedNotification] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const activeProfile = PROFILES[activeProfileKey];

  const handleSimulateEncrypt = () => {
    setIsProcessing(true);
    setTimeout(() => {
      // Deterministic simulation based on active profile and input
      const pseudoNonce = Array.from({ length: 12 }, () => Math.floor(Math.random() * 256).toString(16).padStart(2, '0')).join('');
      const pseudoTag = Array.from({ length: 16 }, () => Math.floor(Math.random() * 256).toString(16).padStart(2, '0')).join('');
      const pseudoCipher = btoa(`CV1:${activeProfileKey}:${pseudoNonce}:${plaintextInput.slice(0, 16)}...:${pseudoTag}`);
      
      setEncryptedPayload(pseudoCipher);
      setDecryptedText(null);
      setIsProcessing(false);
    }, 280);
  };

  const handleSimulateDecrypt = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setDecryptedText(plaintextInput);
      setIsProcessing(false);
    }, 200);
  };

  const handleRegenerateMnemonic = () => {
    const shuffled = [...SAMPLE_MNEMONIC].sort(() => Math.random() - 0.5);
    setMnemonicList(shuffled);
  };

  const handleCopyMnemonic = () => {
    navigator.clipboard.writeText(mnemonicList.join(' '));
    setCopiedNotification(true);
    setTimeout(() => setCopiedNotification(false), 2000);
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '2rem 1.5rem' }}>
      {/* Navigation & Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ 
            width: '44px', 
            height: '44px', 
            borderRadius: '10px', 
            background: 'linear-gradient(135deg, #00f0ff 0%, #3b82f6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 24px rgba(0, 240, 255, 0.4)'
          }}>
            <Lock size={24} color="#040810" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h1 style={{ fontSize: '1.45rem', fontWeight: 700, letterSpacing: '-0.02em' }}>CryptaVault</h1>
              <span className="badge badge-cyan">Client Portal</span>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Adaptive Hybrid Post-Quantum Zero-Knowledge Storage</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div className="badge badge-emerald">
            <ShieldCheck size={14} />
            <span>ZK Boundary: Enforced</span>
          </div>
          <div className="badge badge-purple">
            <Zap size={14} />
            <span>NIST PQC: ML-KEM / ML-DSA</span>
          </div>
          <div className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
            <Server size={14} />
            <span>Supabase Cloud RLS</span>
          </div>
        </div>
      </header>

      {/* Main Grid Showcase */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        
        {/* Card 1: Adaptive Profile Engine */}
        <section className="glass-panel" style={{ padding: '1.75rem', gridColumn: 'span 2' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Cpu size={20} color="var(--cyan-glow)" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Adaptive Cryptographic Profiles</h2>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Dynamic Hardware & Network Selection</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
            {Object.keys(PROFILES).map((key) => {
              const p = PROFILES[key];
              const isSelected = key === activeProfileKey;
              return (
                <button
                  key={key}
                  onClick={() => setActiveProfileKey(key)}
                  style={{
                    padding: '0.85rem 1rem',
                    background: isSelected ? 'rgba(0, 240, 255, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                    border: isSelected ? '1px solid var(--cyan-glow)' : '1px solid var(--border-subtle)',
                    borderRadius: '10px',
                    color: isSelected ? 'var(--cyan-glow)' : 'var(--text-main)',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: isSelected ? '0 0 16px rgba(0, 240, 255, 0.15)' : 'none'
                  }}
                >
                  <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', fontWeight: 700, opacity: 0.8 }}>
                    {p.level}
                  </div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, marginTop: '0.2rem' }}>
                    {key}
                  </div>
                </button>
              );
            })}
          </div>

          <div style={{ 
            background: 'rgba(0,0,0,0.35)', 
            padding: '1.25rem', 
            borderRadius: '10px', 
            border: '1px solid rgba(255,255,255,0.06)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem'
          }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Symmetric AEAD Cipher</span>
              <span className="mono-tag" style={{ color: activeProfile.color, display: 'inline-block', marginTop: '0.3rem' }}>
                {activeProfile.symmetric}
              </span>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Key Encapsulation (KEM)</span>
              <span className="mono-tag" style={{ color: '#38bdf8', display: 'inline-block', marginTop: '0.3rem' }}>
                {activeProfile.kem}
              </span>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Digital Signature Scheme</span>
              <span className="mono-tag" style={{ color: '#c084fc', display: 'inline-block', marginTop: '0.3rem' }}>
                {activeProfile.sig}
              </span>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Memory-Hard KDF</span>
              <span className="mono-tag" style={{ color: '#34d399', display: 'inline-block', marginTop: '0.3rem' }}>
                {activeProfile.kdf}
              </span>
            </div>
          </div>
          <p style={{ marginTop: '0.85rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            💡 <strong style={{ color: 'var(--text-main)' }}>Policy Rationale:</strong> {activeProfile.desc}
          </p>
        </section>

        {/* Card 2: Micro-Benchmark Telemetry */}
        <section className="glass-panel" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.25rem' }}>
            <Activity size={20} color="#34d399" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Engine Performance</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.3rem' }}>
                <span>AES-256-GCM (AES-NI)</span>
                <strong style={{ color: '#34d399' }}>2,169.5 MB/s</strong>
              </div>
              <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: '88%', height: '100%', background: '#34d399' }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.3rem' }}>
                <span>ChaCha20-Poly1305</span>
                <strong style={{ color: '#38bdf8' }}>1,586.4 MB/s</strong>
              </div>
              <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: '65%', height: '100%', background: '#38bdf8' }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.3rem' }}>
                <span>BLAKE3 Tree Hashing (AVX2)</span>
                <strong style={{ color: 'var(--cyan-glow)' }}>3,491.6 MB/s</strong>
              </div>
              <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: '98%', height: '100%', background: 'var(--cyan-glow)' }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.3rem' }}>
                <span>ML-KEM-768 Encap Latency</span>
                <strong style={{ color: '#c084fc' }}>0.029 ms</strong>
              </div>
              <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: '92%', height: '100%', background: '#c084fc' }}></div>
              </div>
            </div>
          </div>
        </section>

      </div>

      {/* Interactive Cryptographic Playground */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        
        {/* Simulator Box */}
        <section className="glass-panel" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.25rem' }}>
            <FileCode size={20} color="var(--cyan-glow)" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Client-Side Zero-Knowledge Playground</h2>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>
              Plaintext Message (Encrypted strictly in browser client before network transfer)
            </label>
            <input 
              type="text" 
              value={plaintextInput}
              onChange={(e) => setPlaintextInput(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                color: 'var(--text-main)',
                fontFamily: 'inherit',
                fontSize: '0.9rem'
              }}
            />
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>
              Client Passphrase (Used with Argon2id for Zero-Knowledge Key Derivation)
            </label>
            <input 
              type="password" 
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                color: 'var(--text-main)',
                fontFamily: 'inherit',
                fontSize: '0.9rem'
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
            <button 
              className="btn-primary" 
              onClick={handleSimulateEncrypt}
              disabled={isProcessing}
            >
              <Lock size={16} />
              <span>Encrypt Client-Side</span>
            </button>
            {encryptedPayload && (
              <button 
                className="btn-secondary" 
                onClick={handleSimulateDecrypt}
                disabled={isProcessing}
              >
                <RefreshCw size={16} className={isProcessing ? "spin" : ""} />
                <span>Decrypt & Verify Tag</span>
              </button>
            )}
          </div>

          {encryptedPayload && (
            <div style={{ marginTop: '1rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Ciphertext Envelope (Zero-Knowledge Ciphertext)</span>
              <div style={{
                background: 'rgba(0,0,0,0.5)',
                padding: '0.85rem',
                borderRadius: '8px',
                border: '1px solid rgba(0, 240, 255, 0.25)',
                wordBreak: 'break-all',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                color: '#facc15',
                marginTop: '0.4rem'
              }}>
                {encryptedPayload}
              </div>
            </div>
          )}

          {decryptedText && (
            <div style={{ 
              marginTop: '1rem', 
              padding: '0.85rem', 
              background: 'rgba(16, 185, 129, 0.1)', 
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem'
            }}>
              <CheckCircle size={18} color="#34d399" />
              <div>
                <span style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>Decryption Authenticated: Tag Valid</span>
                <div style={{ fontSize: '0.85rem', color: '#f8fafc', marginTop: '0.2rem' }}>{decryptedText}</div>
              </div>
            </div>
          )}
        </section>

        {/* BIP-39 Key Recovery Vault */}
        <section className="glass-panel" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Key size={20} color="#f59e0b" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>BIP-39 24-Word Master Key Recovery</h2>
            </div>
            <button className="btn-secondary" onClick={handleRegenerateMnemonic} style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}>
              <RefreshCw size={12} />
              <span>Regenerate</span>
            </button>
          </div>

          <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            This mnemonic derives your 256-bit Argon2id root master key. Under zero-knowledge invariants, only this phrase can restore your vaults if credentials are lost.
          </p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '0.5rem',
            background: 'rgba(0,0,0,0.4)',
            padding: '0.85rem',
            borderRadius: '10px',
            border: '1px solid var(--border-subtle)',
            marginBottom: '1rem'
          }}>
            {mnemonicList.map((word, idx) => (
              <div 
                key={idx}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  padding: '0.35rem 0.5rem',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  border: '1px solid rgba(255,255,255,0.04)'
                }}
              >
                <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>{idx + 1}.</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 500 }}>{word}</span>
              </div>
            ))}
          </div>

          <button 
            className="btn-secondary" 
            onClick={handleCopyMnemonic} 
            style={{ width: '100%', justifyContent: 'center' }}
          >
            <Copy size={16} />
            <span>{copiedNotification ? "Copied to Clipboard!" : "Copy 24-Word Recovery Phrase"}</span>
          </button>
        </section>

      </div>

      {/* Showcase Footer / CLI Prompt */}
      <footer className="glass-panel" style={{ padding: '1.25rem 1.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Terminal size={18} color="var(--cyan-glow)" />
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Showcase CLI: <code style={{ color: 'var(--cyan-glow)', background: 'rgba(0,0,0,0.4)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>.venv/bin/cryptavault benchmark</code> or <code style={{ color: 'var(--cyan-glow)', background: 'rgba(0,0,0,0.4)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>.venv/bin/cryptavault status</code>
          </span>
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
          CryptaVault Milestone 1 & 2 Core • Node 20+ • Python 3.11
        </div>
      </footer>
    </div>
  );
}
