import { useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  Boxes,
  Cloud,
  Fingerprint,
  KeyRound,
  Layers,
  LockKeyhole,
  Share2,
  ShieldAlert,
  Sparkles,
  Terminal,
} from 'lucide-react';
import { Card, PageHeader } from '../components/ui';
import { classNames } from '../lib/format';

const TOPICS = [
  {
    id: 'zk',
    label: 'Zero-knowledge',
    icon: LockKeyhole,
    title: 'The zero-knowledge boundary',
    summary:
      'CryptaVault is designed so the server and storage backends only ever see ciphertext, encrypted manifests, wrapped keys, and non-identifying metadata.',
    sections: [
      {
        heading: 'What never leaves the client',
        body: 'Plaintext, passphrases, master keys, raw per-file keys, decrypted manifests, and share secrets stay inside the client boundary. The static portal is a pure client: it has no network calls for vault operations.',
      },
      {
        heading: 'What is stored',
        body: 'IndexedDB in this browser stores the vault salt, a sealed verifier, AES-GCM ciphertext chunks, keys wrapped by the master key, encrypted manifests, encrypted message bodies, and local audit events. None of these are usable without the passphrase.',
      },
      {
        heading: 'Key hierarchy',
        code: `passphrase\n  └─ PBKDF2-SHA256 (210,000 iterations, 16-byte salt)\n       └─ master key (AES-256-GCM, non-extractable)\n            ├─ wraps per-file key (32 random bytes)\n            │    └─ encrypts chunked file payload\n            ├─ wraps per-message key\n            └─ seals manifests, contact labels, verifier\n\nshare passphrase (optional)\n  └─ PBKDF2-SHA256 → share key\n       └─ wraps the file key inside the share payload`,
      },
      {
        heading: 'Threat model',
        body: 'This protects data at rest in browser storage and in any backend that only stores ciphertext. It does not defend against a compromised endpoint, a malicious browser extension with page access, keyloggers, or an attacker who knows the passphrase. The static demo also cannot enforce remote revocation.',
      },
    ],
  },
  {
    id: 'agility',
    label: 'Crypto agility',
    icon: Boxes,
    title: 'Crypto agility without silent downgrade',
    summary:
      'A stable catalog of 88 algorithms across 9 families, each with a wire ID, lifecycle status, security level, sizes, and runtime requirements.',
    sections: [
      {
        heading: 'Why a catalog',
        body: 'Data encrypted years ago must remain decryptable while new data migrates to stronger primitives. Persisting a stable wire ID in the manifest lets the engine resolve the exact algorithm without guessing from names or key sizes.',
      },
      {
        heading: 'Lifecycle gates',
        body: 'Production algorithms are allowed by default. Experimental entries need an explicit policy flag. Legacy entries need opt-in. Forbidden entries such as MD5, MD4, and SIKE are catalogued for migration awareness but rejected by the engine. Missing runtimes fail closed.',
      },
      {
        heading: 'Wire ID layout',
        code: `0x01xx  symmetric AEAD\n0x02xx  hash\n0x03xx  key derivation\n0x04xx  key encapsulation\n0x05xx  signatures\n0x06xx  PAKE\n0x07xx  secret sharing\n0x08xx  randomness\n0x09xx  quantum / experimental\n\nexample: 0x0101 = aes-256-gcm`,
      },
      {
        heading: 'Adaptive profiles',
        body: 'The six profiles map slider bands to concrete algorithms: PERFORMANCE, STANDARD, BALANCED, STRONG, PQ-STRONG, and MAXIMUM. Profiles are policy, not hardcoded branch logic; the resolver returns a full configuration that the pipeline consumes.',
      },
    ],
  },
  {
    id: 'container',
    label: 'Container format',
    icon: Layers,
    title: 'The encrypted container',
    summary:
      'The Python engine writes CVV2 headers with CVT1 trailers. The browser portal uses a JSON CVW1 container that mirrors the same chunked authenticated-encryption ideas.',
    sections: [
      {
        heading: 'Python container (CVV2)',
        body: 'A deterministic JSON header carries the file id, algorithm bindings for symmetric/hash/signature/KEM/KDF, chunk size, and creation time. The header digest and Merkle root are signed. A CVT1 trailer records the chunk count, Merkle root, and signature. Legacy CVV1 files remain readable.',
      },
      {
        heading: 'Browser container (CVW1)',
        body: 'The portal stores a JSON container with per-chunk IVs and ciphertext. Every chunk is sealed with AES-256-GCM using AAD that binds the file id, chunk index, and final-chunk flag. Reordering, truncation, or cross-file substitution fails authentication.',
      },
      {
        heading: 'Chunk AAD',
        code: `aad = "cryptavault:web:v1:" + fileId + ":" + chunkIndex + ":" + isFinal\n\nsealed = AES-256-GCM(fileKey, chunk, aad)\n\nmanifest = AES-256-GCM(masterKey, {\n  name, type, size, sha256, chunkCount, profile, compression\n})`,
      },
      {
        heading: 'Integrity layers',
        body: 'Each chunk has its own GCM tag. The manifest stores the SHA-256 of the plaintext, and share bundles verify it after decryption. The Python path adds a Merkle root and signature over the header digest. No unauthenticated length field is trusted.',
      },
    ],
  },
  {
    id: 'pq',
    label: 'PQ & cascades',
    icon: Sparkles,
    title: 'Post-quantum defense and layered AEAD',
    summary:
      'Hybrid KEMs and signatures combine classical and post-quantum assumptions. The cascade module layers independent AEADs so both must fail for confidentiality to break.',
    sections: [
      {
        heading: 'Hybrid, not replacement',
        body: 'Hybrid KEM and signature bindings combine a classical primitive with a PQ primitive. An attacker must break both. This avoids betting everything on a young PQ implementation while still addressing harvest-now-decrypt-later risk.',
      },
      {
        heading: 'CascadeAEAD',
        body: 'CascadeAEAD derives an independent key per layer with HKDF-SHA256, encrypts inner-to-outer, and verifies every tag on decryption. A tampered tag fails closed. Layers can be recombined through the catalog without rewriting the pipeline.',
      },
      {
        heading: 'Runtime reality',
        body: 'PQ entries that depend on liboqs are catalogued but marked runtime-unavailable until the dependency is installed. The portal shows this explicitly. The browser portal itself uses WebCrypto AES-GCM and PBKDF2 today; WASM PQ integration is a roadmap item.',
      },
      {
        heading: 'What “parabolic” means',
        body: 'There is no standard “parabolic cryptography.” The real adjacent families are hyperelliptic curves, pairings, and isogenies. Any non-standard scheme should be named precisely, marked experimental, and never presented as a production default.',
      },
    ],
  },
  {
    id: 'sharing',
    label: 'Sharing',
    icon: Share2,
    title: 'Capability links and bundles',
    summary:
      'A share is a second encryption boundary around the file key, so the recipient never needs your vault passphrase or account.',
    sections: [
      {
        heading: 'How a share is built',
        body: 'The portal loads the file key, generates a random share key (or derives one from a passphrase), and wraps the file key with it. The resulting payload carries the already-encrypted container plus the wrapped key. The recipient unwraps the file key, decrypts chunks, and verifies SHA-256 before saving.',
      },
      {
        heading: 'Link vs passphrase',
        body: 'A capability link carries the random share key in the URL fragment. Anyone with the full link can decrypt the shared copy. A passphrase share carries only ciphertext and a salt; the recipient needs both the link and the passphrase.',
      },
      {
        heading: 'Limits of static sharing',
        body: 'Self-contained links cannot be remotely revoked or expired without a server. The share records in this portal are local governance metadata. For enforceable revocation, use the API with authenticated share records and key rotation.',
      },
      {
        heading: 'Large files',
        body: 'URLs have practical size limits. The portal automatically recommends a downloadable .cvshare.json bundle when the encoded link is too large. The bundle is still ciphertext; without a passphrase it also carries the capability key.',
      },
    ],
  },
  {
    id: 'byos',
    label: 'CLI & API',
    icon: Terminal,
    title: 'Install and operate the Python stack',
    summary:
      'The repository ships a core engine, FastAPI backend, CLI, and static portals. The Python packages can be installed locally with uv.',
    sections: [
      {
        heading: 'Install the CLI',
        code: `cd CryptaVault\nuv venv --python 3.11 .venv\nsource .venv/bin/activate\nuv pip install -e packages/core -e packages/cli\n\ncryptavault --help\ncryptavault profile list\ncryptavault encrypt ./secret.pdf --profile MAXIMUM`,
      },
      {
        heading: 'Run the API',
        code: `uv pip install -e packages/api\nuvicorn cryptavault_api.main:app --reload --port 8000\n\n# catalog and profiles\ncurl http://localhost:8000/api/crypto/catalog\ncurl http://localhost:8000/api/crypto/profiles`,
      },
      {
        heading: 'Backends',
        body: 'Storage connectors include local, mock, Supabase, SFTP/FTPS, and cloud adapters. The static portal never calls them. Configure credentials only through environment variables; never commit secrets.',
      },
      {
        heading: 'Tests',
        code: `pytest --hypothesis-seed=0\nruff check .\nblack --check .\nmypy packages/core/cryptavault packages/api/cryptavault_api packages/cli/cryptavault_cli`,
      },
    ],
  },
  {
    id: 'threat',
    label: 'Threat model',
    icon: ShieldAlert,
    title: 'Threat model and honest limits',
    summary:
      'The portal is a serious client-side encryption demo, not an audited password manager. Know exactly what it does and does not protect.',
    sections: [
      {
        heading: 'Protected',
        body: 'Data at rest in browser storage; ciphertext uploaded to a backend that only sees opaque bytes; accidental plaintext leakage through file names or manifests (they are encrypted); chunk reordering, truncation, and cross-file substitution (AAD + GCM); wrong passphrases (verifier + GCM failure).',
      },
      {
        heading: 'Not protected',
        body: 'A compromised device, malicious extension, keylogger, screen capture, or attacker who obtains the passphrase. The static demo does not protect against clearing site data or forgetting the passphrase. It does not provide remote revocation or multi-device sync.',
      },
      {
        heading: 'Cryptographic choices',
        body: 'PBKDF2-SHA256 is used because WebCrypto exposes it without a WASM dependency. Argon2id is stronger against GPU cracking and is the target for the WASM integration; the Python core already supports Argon2id profiles.',
      },
      {
        heading: 'Roadmap, stated plainly',
        body: 'Streaming compression without whole-file buffering, Argon2id in the browser, WASM PQ primitives, authenticated multi-device relay, enforceable share revocation, and a formal third-party audit remain future work. Documentation should never claim these are complete.',
      },
    ],
  },
];

export default function AcademyPage(): JSX.Element {
  const [active, setActive] = useState(TOPICS[0].id);
  const topic = TOPICS.find((item) => item.id === active) ?? TOPICS[0];
  const TopicIcon = topic.icon;

  return (
    <div className="animate-in">
      <PageHeader
        eyebrow="Academy"
        title="How the system actually works"
        description="A precise, implementation-aligned guide to the zero-knowledge boundary, crypto agility, container framing, post-quantum layers, sharing, and the limits of this deployment."
        action={
          <a
            className="btn-secondary"
            href="https://github.com/DHRUV-MULANI/CryptaVault#readme"
            target="_blank"
            rel="noreferrer"
          >
            <BookOpen className="h-4 w-4" /> Repository docs
          </a>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
        <div className="card !p-2">
          {TOPICS.map((item) => (
            <button
              key={item.id}
              onClick={() => setActive(item.id)}
              className={classNames(
                'mb-1 flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm transition-colors',
                active === item.id
                  ? 'bg-cyan-500/10 text-cyan-100'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200',
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </button>
          ))}
          <div className="mt-2 rounded-xl border border-white/8 bg-white/[0.02] p-3">
            <div className="flex items-center gap-2 text-[11px] text-slate-400">
              <Fingerprint className="h-3.5 w-3.5 text-emerald-300" />
              Implementation-aligned
            </div>
            <p className="mt-1.5 text-[10px] leading-relaxed text-slate-500">
              This page is written against the code in this repository, including known gaps.
            </p>
          </div>
        </div>

        <Card>
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-300">
              <TopicIcon className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-lg font-semibold text-white">{topic.title}</h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-400">{topic.summary}</p>
            </div>
          </div>

          <div className="mt-5 space-y-5">
            {topic.sections.map((section) => (
              <div key={section.heading}>
                <h3 className="text-sm font-semibold text-slate-100">{section.heading}</h3>
                {'body' in section && section.body ? (
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{section.body}</p>
                ) : null}
                {'code' in section && section.code ? (
                  <pre className="code-block mt-2.5">{section.code}</pre>
                ) : null}
              </div>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap gap-2 border-t border-white/8 pt-4">
            {[
              { label: 'Crypto catalog', href: '/catalog', icon: Boxes },
              { label: 'CLI install docs', href: 'https://github.com/DHRUV-MULANI/CryptaVault#cli', icon: Terminal },
              { label: 'API routes', href: 'https://github.com/DHRUV-MULANI/CryptaVault/blob/main/docs/API.md', icon: Cloud },
            ].map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="btn-secondary !py-1.5 !text-xs"
                target={link.href.startsWith('http') ? '_blank' : undefined}
                rel="noreferrer"
              >
                <link.icon className="h-3.5 w-3.5" /> {link.label}
                <ArrowRight className="h-3 w-3" />
              </a>
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {[
          {
            icon: KeyRound,
            title: 'Rotate, don’t reuse',
            body: 'Changing the vault passphrase re-wraps every file and message key. The data ciphertext is not re-encrypted, so rotation is fast and safe.',
          },
          {
            icon: LockKeyhole,
            title: 'Lock on idle',
            body: 'The master key lives in memory only. Auto-lock clears it after the configured idle window; reload always requires the passphrase.',
          },
          {
            icon: ShieldAlert,
            title: 'Backup the ciphertext',
            body: 'Encrypted backups export the whole IndexedDB store. They remain useless without the passphrase, and can be restored on another device.',
          },
        ].map((card) => (
          <Card key={card.title}>
            <card.icon className="h-5 w-5 text-cyan-300" />
            <h3 className="mt-3 text-sm font-semibold text-white">{card.title}</h3>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{card.body}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
