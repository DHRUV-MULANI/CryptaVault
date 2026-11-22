import { useEffect, useRef, useState } from 'react';
import { Link } from 'wouter';
import {
  ShieldCheck,
  Lock,
  Cloud,
  Share2,
  KeyRound,
  Layers,
  Cpu,
  Globe,
  ArrowRight,
  Sparkles,
  Fingerprint,
  FileLock2,
  Users,
  EyeOff,
  Server,
  CheckCircle2,
  ChevronRight,
} from 'lucide-react';

function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true); },
      { threshold },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

function Reveal({ children, className = '', delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const { ref, visible } = useInView();
  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0px)' : 'translateY(28px)',
        transition: `opacity 0.7s ease ${delay}ms, transform 0.7s ease ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

function Cube3D() {
  return (
    <div className="cv-cube-scene" aria-hidden="true">
      <div className="cv-cube">
        <div className="cv-face cv-front"><ShieldCheck className="h-10 w-10 text-cyan-300" /><span>Encrypt</span></div>
        <div className="cv-face cv-back"><KeyRound className="h-10 w-10 text-violet-300" /><span>Keys</span></div>
        <div className="cv-face cv-right"><Share2 className="h-10 w-10 text-emerald-300" /><span>Share</span></div>
        <div className="cv-face cv-left"><Cloud className="h-10 w-10 text-sky-300" /><span>Store</span></div>
        <div className="cv-face cv-top"><Fingerprint className="h-10 w-10 text-amber-300" /><span>Zero-K</span></div>
        <div className="cv-face cv-bottom"><Layers className="h-10 w-10 text-pink-300" /><span>Vault</span></div>
      </div>
    </div>
  );
}

const FEATURES = [
  { icon: EyeOff, title: 'Zero-Knowledge by Design', desc: 'Your passphrase derives keys in the browser. The server stores ciphertext, encrypted metadata, and auth verifiers — never plaintext.', color: 'text-cyan-300', bg: 'bg-cyan-400/10 border-cyan-400/20' },
  { icon: FileLock2, title: 'Client-Side Encryption', desc: 'Files are encrypted before upload with AES-GCM chunked containers. Keys stay in memory and are cleared on lock.', color: 'text-violet-300', bg: 'bg-violet-400/10 border-violet-400/20' },
  { icon: Share2, title: 'Secure Sharing', desc: 'Create capability links with expiry, max uses, password, and revocation. Decryption keys travel in URL fragments, not to the server.', color: 'text-emerald-300', bg: 'bg-emerald-400/10 border-emerald-400/20' },
  { icon: Users, title: 'Workspaces & Collaboration', desc: 'Organize encrypted files into workspaces. Manage access, roles, and storage targets from one dynamic control plane.', color: 'text-sky-300', bg: 'bg-sky-400/10 border-sky-400/20' },
  { icon: Cpu, title: 'Crypto-Agile Profiles', desc: 'Profile-driven cryptography with modern ciphers, KDFs, integrity checks, and a path to post-quantum readiness.', color: 'text-amber-300', bg: 'bg-amber-400/10 border-amber-400/20' },
  { icon: Server, title: 'Multi-Target Storage', desc: 'Store encrypted blobs on local, S3-compatible, or other configured targets. Metadata stays managed; plaintext stays yours.', color: 'text-pink-300', bg: 'bg-pink-400/10 border-pink-400/20' },
];

const STEPS = [
  { n: '01', title: 'Create your vault', desc: 'Set a passphrase. CryptaVault derives auth and encryption keys locally using strong KDF parameters.' },
  { n: '02', title: 'Encrypt & upload', desc: 'Files are chunked, encrypted in your browser, and uploaded as opaque ciphertext to your workspace storage.' },
  { n: '03', title: 'Share with control', desc: 'Generate secure share links with expiry, usage limits, passwords, and instant revocation.' },
  { n: '04', title: 'Access anywhere', desc: 'Unlock from any device with your passphrase. The server never receives your master key.' },
];

export default function LandingPage(): JSX.Element {
  const [mouse, setMouse] = useState({ x: 0, y: 0 });
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      setMouse({
        x: (e.clientX / window.innerWidth - 0.5) * 2,
        y: (e.clientY / window.innerHeight - 0.5) * 2,
      });
    };
    window.addEventListener('mousemove', onMove);
    return () => window.removeEventListener('mousemove', onMove);
  }, []);

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#050811] text-white">
      <style>{`
        .cv-cube-scene { width: 260px; height: 260px; perspective: 900px; margin: 0 auto; }
        .cv-cube { width: 100%; height: 100%; position: relative; transform-style: preserve-3d; animation: cv-spin 18s linear infinite; }
        .cv-face { position: absolute; width: 260px; height: 260px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:12px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; font-size:12px; color:#e2e8f0; background: linear-gradient(180deg, rgba(15,23,42,0.72), rgba(2,6,23,0.55)); border:1px solid rgba(0,240,255,0.22); box-shadow: inset 0 0 40px rgba(0,240,255,0.06), 0 0 30px rgba(0,240,255,0.08); backdrop-filter: blur(8px); border-radius: 24px; }
        .cv-front  { transform: rotateY(0deg) translateZ(130px); }
        .cv-back   { transform: rotateY(180deg) translateZ(130px); }
        .cv-right  { transform: rotateY(90deg) translateZ(130px); }
        .cv-left   { transform: rotateY(-90deg) translateZ(130px); }
        .cv-top    { transform: rotateX(90deg) translateZ(130px); }
        .cv-bottom { transform: rotateX(-90deg) translateZ(130px); }
        @keyframes cv-spin { 0%{transform:rotateX(-18deg) rotateY(0deg)} 100%{transform:rotateX(-18deg) rotateY(360deg)} }
        .cv-grid { background-image: linear-gradient(rgba(0,240,255,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(0,240,255,0.07) 1px, transparent 1px); background-size: 48px 48px; mask-image: radial-gradient(ellipse 70% 60% at 50% 40%, black 30%, transparent 100%); }
        .cv-orb { position:absolute; border-radius:9999px; filter: blur(80px); opacity:0.55; pointer-events:none; }
        .cv-glow-text { background: linear-gradient(135deg, #fff 0%, #67e8f9 35%, #818cf8 70%, #c084fc 100%); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .cv-border-glow { position:relative; }
        .cv-border-glow::before { content:''; position:absolute; inset:-1px; border-radius:inherit; padding:1px; background:linear-gradient(135deg, rgba(0,240,255,0.35), rgba(168,85,247,0.15), rgba(0,240,255,0.05)); -webkit-mask:linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite:xor; mask-composite:exclude; pointer-events:none; }
        @keyframes cv-float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-12px)} }
        .cv-float { animation: cv-float 7s ease-in-out infinite; }
      `}</style>

      <div className="pointer-events-none fixed inset-0 cv-grid opacity-40" />
      <div className="cv-orb h-[32rem] w-[32rem] bg-cyan-500/20 -top-40 -left-20" style={{ transform: `translate(${mouse.x * -20}px, ${mouse.y * -20}px)` }} />
      <div className="cv-orb h-[28rem] w-[28rem] bg-violet-600/20 top-[30%] right-[-10%]" style={{ transform: `translate(${mouse.x * 25}px, ${mouse.y * 15}px)` }} />
      <div className="cv-orb h-[24rem] w-[24rem] bg-emerald-500/10 bottom-[-10%] left-[30%]" />

      <header className="relative z-20 mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-8">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-glow">
            <ShieldCheck className="h-6 w-6" />
          </span>
          <div>
            <div className="text-lg font-semibold tracking-tight">CryptaVault</div>
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Zero-Knowledge Storage</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <a href="#features" className="btn-ghost hidden sm:inline-flex">Features</a>
          <a href="#how" className="btn-ghost hidden sm:inline-flex">How it works</a>
          <Link href="/auth" className="btn-secondary">Sign in</Link>
          <Link href="/auth" className="btn-primary">Get started <ArrowRight className="h-4 w-4" /></Link>
        </div>
      </header>

      <main className="relative z-10">
        <section className="mx-auto grid max-w-7xl gap-12 px-6 pb-20 pt-10 lg:grid-cols-2 lg:items-center lg:px-8 lg:pt-16">
          <Reveal>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-1.5 text-xs font-medium text-cyan-200">
              <Sparkles className="h-3.5 w-3.5" /> End-to-end encrypted. Crypto-agile. Built for the real web.
            </div>
            <h1 className="mt-6 text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
              Your files. <span className="cv-glow-text">Your keys.</span><br />Your vault.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-300">
              CryptaVault is a zero-knowledge storage framework that encrypts data in your browser before it ever leaves your device. Share securely, manage workspaces, and stay in control — even from the cloud.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link href="/auth" className="btn-primary px-6 py-3 text-sm">Create secure vault <ArrowRight className="h-4 w-4" /></Link>
              <a href="#features" className="btn-secondary px-6 py-3 text-sm">Explore features</a>
            </div>
            <div className="mt-10 flex flex-wrap gap-6 text-sm text-slate-400">
              {['AES-GCM encrypted', 'Passphrase-derived keys', 'Share with expiry & revocation', 'Workspace-ready'].map((t) => (
                <span key={t} className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" />{t}</span>
              ))}
            </div>
          </Reveal>

          <Reveal delay={120} className="relative flex items-center justify-center py-8">
            <div className="absolute inset-0 rounded-full bg-cyan-500/5 blur-3xl" />
            <div className="cv-float relative">
              <Cube3D />
              <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-white/10 bg-slate-950/80 px-4 py-2 text-xs text-slate-300 backdrop-blur">
                <span className="text-cyan-300">●</span> Client-side encryption active
              </div>
            </div>
          </Reveal>
        </section>

        <section className="mx-auto max-w-7xl px-6 pb-20 lg:px-8">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: 'Zero-knowledge boundary', value: 'Enforced', icon: EyeOff },
              { label: 'Encryption before upload', value: 'Always', icon: Lock },
              { label: 'Sharing controls', value: 'Built-in', icon: Share2 },
              { label: 'Access from anywhere', value: 'Secure', icon: Globe },
            ].map((s, i) => (
              <Reveal key={s.label} delay={i * 60}>
                <div className="card cv-border-glow p-5">
                  <s.icon className="h-5 w-5 text-cyan-300" />
                  <div className="mt-3 text-2xl font-semibold text-white">{s.value}</div>
                  <div className="mt-1 text-sm text-slate-400">{s.label}</div>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <Reveal>
            <div className="mx-auto max-w-3xl text-center">
              <div className="badge badge-cyan mb-4">Full framework</div>
              <h2 className="text-4xl font-semibold tracking-tight sm:text-5xl">Everything a modern encrypted vault needs</h2>
              <p className="mt-4 text-lg text-slate-400">CryptaVault combines client-side cryptography, dynamic workspaces, secure sharing, and admin controls into one zero-knowledge platform.</p>
            </div>
          </Reveal>
          <div className="mt-14 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {FEATURES.map((f, i) => (
              <Reveal key={f.title} delay={i * 70}>
                <div className="card card-hover cv-border-glow h-full p-6">
                  <div className={`inline-flex rounded-xl border p-3 ${f.bg}`}>
                    <f.icon className={`h-6 w-6 ${f.color}`} />
                  </div>
                  <h3 className="mt-4 text-xl font-semibold text-white">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{f.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        <section id="how" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
            <Reveal>
              <div className="badge badge-purple mb-4">How it works</div>
              <h2 className="text-4xl font-semibold tracking-tight sm:text-5xl">Security that starts before the network</h2>
              <p className="mt-4 text-lg text-slate-400">The server coordinates storage and access. Your browser does the cryptography. That separation is the core of CryptaVault.</p>
              <div className="mt-8 space-y-4">
                {STEPS.map((s) => (
                  <div key={s.n} className="card flex gap-4 p-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-400/10 font-mono text-sm font-semibold text-cyan-300">{s.n}</div>
                    <div>
                      <div className="font-medium text-white">{s.title}</div>
                      <div className="mt-1 text-sm text-slate-400">{s.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </Reveal>
            <Reveal delay={120}>
              <div className="card cv-border-glow overflow-hidden p-6">
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <div className="flex items-center gap-2 text-sm text-slate-300"><Lock className="h-4 w-4 text-cyan-300" /> Zero-knowledge flow</div>
                  <span className="badge badge-emerald">Live model</span>
                </div>
                <div className="mt-5 space-y-3 font-mono text-[12px] leading-relaxed">
                  {[
                    ['Browser', 'derive(auth_key, master_key) from passphrase + salts', 'text-cyan-300'],
                    ['Browser', 'encrypt(file_chunks) -> ciphertext container', 'text-violet-300'],
                    ['API', 'store(ciphertext, wrapped keys, metadata envelopes)', 'text-sky-300'],
                    ['Browser', 'decrypt only after local unlock', 'text-emerald-300'],
                    ['Share', 'token + URL fragment key -> recipient decrypts locally', 'text-amber-300'],
                  ].map(([actor, text, color]) => (
                    <div key={text} className="rounded-xl border border-white/8 bg-black/20 p-3">
                      <span className={`${color} font-semibold`}>{actor}</span>
                      <span className="text-slate-500"> → </span>
                      <span className="text-slate-300">{text}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-5 rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-sm text-emerald-200">
                  <div className="flex items-center gap-2 font-medium"><ShieldCheck className="h-4 w-4" /> Server never sees plaintext or master keys.</div>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <Reveal>
            <div className="card cv-border-glow relative overflow-hidden p-8 sm:p-12">
              <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 via-transparent to-violet-500/10" />
              <div className="relative grid gap-8 lg:grid-cols-2 lg:items-center">
                <div>
                  <div className="badge badge-emerald mb-4">Ready for users</div>
                  <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Built to move from dev device to real users</h2>
                  <p className="mt-4 text-slate-400">Dynamic API-backed auth, encrypted file flows, workspaces, and share controls — designed to grow into a full internet-ready zero-knowledge platform.</p>
                </div>
                <div className="flex flex-col gap-3 sm:flex-row lg:justify-end">
                  <Link href="/auth" className="btn-primary px-6 py-3">Open CryptaVault <ChevronRight className="h-4 w-4" /></Link>
                  <a href="#features" className="btn-secondary px-6 py-3">See capabilities</a>
                </div>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      <footer className="relative z-10 border-t border-white/8 px-6 py-8 text-sm text-slate-500 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-cyan-400" /> CryptaVault — Zero-knowledge storage framework</div>
          <div className="flex gap-4">
            <Link href="/auth" className="hover:text-slate-300">Sign in</Link>
            <a href="#features" className="hover:text-slate-300">Features</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
