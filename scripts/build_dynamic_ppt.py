"""Build the CryptaVault dynamic-stack presentation.

Run: .venv/bin/python scripts/build_dynamic_ppt.py
Output: docs/CryptaVault_Dynamic_Stack.pptx
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

BG = RGBColor(8, 15, 30)
PANEL = RGBColor(15, 27, 48)
PANEL_2 = RGBColor(20, 35, 60)
WHITE = RGBColor(248, 250, 252)
MUTED = RGBColor(148, 163, 184)
CYAN = RGBColor(34, 211, 238)
EMERALD = RGBColor(52, 211, 153)
AMBER = RGBColor(251, 191, 36)
ROSE = RGBColor(251, 113, 133)
INDIGO = RGBColor(129, 140, 248)
LINE = RGBColor(51, 65, 85)
FONT = "Segoe UI"
MONO = "Consolas"

W = 13.333
H = 7.5


def rgb(hex_value: str) -> RGBColor:
    value = hex_value.lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def fill(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color


def no_line(shape) -> None:
    shape.line.fill.background()


def rect(slide, x, y, w, h, color, radius=True):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    fill(shape, color)
    no_line(shape)
    if radius:
        shape.adjustments[0] = 0.08
    return shape


def text(
    slide,
    value,
    x,
    y,
    w,
    h,
    *,
    size=18,
    color=WHITE,
    bold=False,
    font=FONT,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    italic=False,
    spacing=1.0,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = spacing
    run = p.add_run()
    run.text = value
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return box


def bullets(slide, items, x, y, w, h, *, size=16, color=WHITE, bullet_color=CYAN, spacing=10):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for index, item in enumerate(items):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.space_after = Pt(spacing)
        p.line_spacing = 1.05
        mark = p.add_run()
        mark.text = "•  "
        mark.font.name = FONT
        mark.font.size = Pt(size)
        mark.font.bold = True
        mark.font.color.rgb = bullet_color
        run = p.add_run()
        run.text = item
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.color.rgb = color
    return box


def slide_base(prs, section, title, subtitle=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    background = slide.background.fill
    background.solid()
    background.fore_color.rgb = BG
    rect(slide, 0, 0, W, 0.08, CYAN, radius=False)
    text(slide, section.upper(), 0.7, 0.42, 5, 0.3, size=10, color=CYAN, bold=True)
    text(slide, title, 0.7, 0.72, 11.8, 0.7, size=30, color=WHITE, bold=True)
    if subtitle:
        text(slide, subtitle, 0.72, 1.42, 11.4, 0.45, size=13, color=MUTED)
    return slide


def footer(slide, number, label="CryptaVault · Dynamic Zero-Knowledge Stack"):
    text(slide, label, 0.7, 7.05, 8, 0.25, size=8, color=LINE)
    text(slide, f"{number:02d}", 12.2, 7.05, 0.4, 0.25, size=8, color=MUTED, align=PP_ALIGN.RIGHT)


def card(slide, x, y, w, h, title, body, accent=CYAN, *, title_size=15, body_size=11):
    rect(slide, x, y, w, h, PANEL)
    rect(slide, x, y, 0.06, h, accent)
    text(slide, title, x + 0.28, y + 0.22, w - 0.5, 0.35, size=title_size, color=WHITE, bold=True)
    text(
        slide,
        body,
        x + 0.28,
        y + 0.66,
        w - 0.52,
        h - 0.82,
        size=body_size,
        color=MUTED,
        spacing=1.04,
    )


def arrow(slide, x1, y1, x2, y2, color=CYAN, width=1.6):
    connector = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    connector.line.color.rgb = color
    connector.line.width = Pt(width)
    connector.line.end_arrowhead = True
    return connector


def pill(slide, value, x, y, w, color=CYAN):
    shape = rect(slide, x, y, w, 0.34, PANEL_2)
    shape.line.color.rgb = color
    shape.line.width = Pt(0.8)
    text(slide, value, x, y + 0.055, w, 0.25, size=9, color=color, bold=True, align=PP_ALIGN.CENTER)


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    # 1 — Title
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = BG
    rect(slide, 0, 0, 0.12, H, CYAN, radius=False)
    text(
        slide,
        "FINAL YEAR PROJECT  •  NOVEMBER 2026",
        1.0,
        1.35,
        8,
        0.3,
        size=11,
        color=CYAN,
        bold=True,
    )
    text(slide, "CryptaVault", 1.0, 1.8, 10.5, 1.0, size=56, color=WHITE, bold=True)
    text(slide, "Adaptive hybrid zero-knowledge storage", 1.0, 2.8, 10.5, 0.6, size=25, color=WHITE)
    text(
        slide,
        "A full-stack system where the browser and CLI encrypt before upload —\n"
        "and the server remains useful without ever holding the keys.",
        1.02,
        3.55,
        9.7,
        1.0,
        size=15,
        color=MUTED,
        spacing=1.15,
    )
    pill(slide, "React + Vite", 1.0, 5.15, 1.6)
    pill(slide, "FastAPI", 2.75, 5.15, 1.45, EMERALD)
    pill(slide, "Neon Postgres", 4.35, 5.15, 1.85, INDIGO)
    pill(slide, "S3 ciphertext", 6.35, 5.15, 1.7, AMBER)
    pill(slide, "Typer CLI", 8.2, 5.15, 1.5, ROSE)
    text(
        slide,
        "165 tests passing  •  web/API/CLI share one wire format",
        1.02,
        6.25,
        10,
        0.35,
        size=12,
        color=LINE,
    )
    footer(slide, 1)

    # 2 — Problem
    slide = slide_base(
        prs,
        "01 / Problem",
        "The cloud can store the ciphertext. It should not hold the keys.",
        "Server-side encryption protects the disk, not the user from the provider.",
    )
    card(
        slide,
        0.7,
        2.0,
        3.85,
        3.3,
        "Provider can decrypt",
        "SSE-KMS and bucket policies leave master keys inside the cloud trust boundary. A breach, insider, or subpoena can expose plaintext.",
        ROSE,
    )
    card(
        slide,
        4.73,
        2.0,
        3.85,
        3.3,
        "Metadata leaks context",
        "File names, types, and manifests reveal business content even when payload encryption is present. Names must be sealed too.",
        AMBER,
    )
    card(
        slide,
        8.76,
        2.0,
        3.85,
        3.3,
        "Harvest now, decrypt later",
        "Long-lived archives captured today can be attacked when quantum capability arrives. The design must remain upgradeable.",
        CYAN,
    )
    rect(slide, 0.7, 5.55, 11.9, 0.95, PANEL_2)
    text(
        slide,
        "CryptaVault inverts the trust model",
        0.95,
        5.78,
        4.4,
        0.35,
        size=15,
        color=WHITE,
        bold=True,
    )
    text(
        slide,
        "The client encrypts. The backend coordinates identity, roles, versions, quotas and sharing policy — without keys.",
        4.55,
        5.79,
        7.75,
        0.4,
        size=11.5,
        color=MUTED,
    )
    footer(slide, 2)

    # 3 — Contributions
    slide = slide_base(
        prs,
        "02 / Contribution",
        "What this project actually delivers",
        "Not a mock-up: a working local full stack, a cross-client format, and a documented security boundary.",
    )
    card(
        slide,
        0.7,
        1.95,
        5.85,
        2.15,
        "Zero-knowledge client",
        "PBKDF2 verifier + master key derived locally. Per-file AES-256-GCM keys wrapped before upload. Metadata sealed under an AAD bound to the file ID.",
        CYAN,
    )
    card(
        slide,
        6.8,
        1.95,
        5.85,
        2.15,
        "Dynamic collaboration",
        "Workspaces, owner/admin/editor/viewer roles, quotas, immutable versions, trash/restore, admin controls, live dashboard.",
        EMERALD,
    )
    card(
        slide,
        0.7,
        4.28,
        5.85,
        2.15,
        "Server-enforced shares",
        "Expiry, max uses, revocation and passphrase checks are policy, not client advice. Capability material stays out of the database.",
        AMBER,
    )
    card(
        slide,
        6.8,
        4.28,
        5.85,
        2.15,
        "Web ↔ CLI interoperability",
        "The same CVW1 container and share manifest work in React/WebCrypto and in a Python Typer client using httpx and cryptography.",
        INDIGO,
    )
    footer(slide, 3)

    # 4 — Architecture
    slide = slide_base(
        prs,
        "03 / Architecture",
        "Two clients, one boundary, three server responsibilities",
        "Plaintext never crosses the vertical line.",
    )
    rect(slide, 0.6, 1.85, 5.45, 4.7, PANEL)
    rect(slide, 0.6, 1.85, 5.45, 0.5, rgb("#0E7490"))
    text(
        slide,
        "CLIENT BOUNDARY — ZERO KNOWLEDGE",
        0.85,
        1.96,
        4.9,
        0.3,
        size=11,
        color=WHITE,
        bold=True,
    )
    rect(slide, 0.9, 2.65, 2.35, 1.5, PANEL_2)
    text(slide, "React + Vite", 1.05, 2.86, 2.0, 0.3, size=15, color=CYAN, bold=True)
    text(
        slide, "Web Crypto\nPBKDF2 · AES-GCM · SHA-256", 1.05, 3.24, 2.0, 0.75, size=10, color=MUTED
    )
    rect(slide, 3.42, 2.65, 2.35, 1.5, PANEL_2)
    text(slide, "Typer CLI", 3.57, 2.86, 2.0, 0.3, size=15, color=ROSE, bold=True)
    text(
        slide,
        "httpx · cryptography\nsame CVW1 wire format",
        3.57,
        3.24,
        2.0,
        0.75,
        size=10,
        color=MUTED,
    )
    text(
        slide,
        "Passphrase → verifier + master key → per-file key\nFile → gzip → chunks → AES-256-GCM",
        0.95,
        4.5,
        4.8,
        0.75,
        size=12,
        color=WHITE,
        bold=True,
        align=PP_ALIGN.CENTER,
    )
    text(
        slide,
        "Only ciphertext, wrapped keys and encrypted manifests go right →",
        0.8,
        5.6,
        5.05,
        0.4,
        size=10,
        color=MUTED,
        align=PP_ALIGN.CENTER,
    )
    arrow(slide, 6.15, 3.95, 7.1, 3.95, CYAN, 2.2)

    rect(slide, 7.25, 1.85, 5.45, 4.7, PANEL)
    rect(slide, 7.25, 1.85, 5.45, 0.5, rgb("#065F46"))
    text(
        slide,
        "SERVER BOUNDARY — COORDINATION ONLY",
        7.5,
        1.96,
        5.0,
        0.3,
        size=11,
        color=WHITE,
        bold=True,
    )
    rect(slide, 7.55, 2.65, 4.85, 0.85, PANEL_2)
    text(slide, "FastAPI 2.0.0", 7.75, 2.82, 2.5, 0.3, size=14, color=EMERALD, bold=True)
    text(
        slide,
        "auth · workspaces · files · shares · admin",
        9.55,
        2.85,
        2.65,
        0.3,
        size=9,
        color=MUTED,
    )
    rect(slide, 7.55, 3.72, 2.3, 1.42, PANEL_2)
    text(slide, "Neon Postgres", 7.72, 3.9, 2.0, 0.3, size=13, color=INDIGO, bold=True)
    text(
        slide,
        "users, roles, quotas\nencrypted metadata\nwrapped keys, share policy",
        7.72,
        4.26,
        1.95,
        0.8,
        size=9,
        color=MUTED,
    )
    rect(slide, 10.05, 3.72, 2.35, 1.42, PANEL_2)
    text(slide, "S3 / SeaweedFS", 10.22, 3.9, 2.05, 0.3, size=13, color=AMBER, bold=True)
    text(
        slide,
        "ciphertext objects\nCVW1 JSON\nno plaintext",
        10.22,
        4.26,
        1.9,
        0.8,
        size=9,
        color=MUTED,
    )
    text(
        slide,
        "JWT + role checks on every route\nShare expiry · use limits · revocation · quota",
        7.55,
        5.45,
        4.85,
        0.65,
        size=10.5,
        color=WHITE,
        align=PP_ALIGN.CENTER,
    )
    footer(slide, 4)

    # 5 — Key flow
    slide = slide_base(
        prs,
        "04 / Crypto flow",
        "Keys are derived and used only on the client",
        "A fresh raw key per version; the master key never leaves memory.",
    )
    steps = [
        ("Passphrase", "user secret", CYAN),
        ("PBKDF2\nSHA-256", "210,000 iterations", INDIGO),
        ("Verifier +\nmaster key", "separate salts", CYAN),
        ("Per-file\nraw key", "256-bit random", EMERALD),
        ("AES-256-GCM\nchunks", "fresh nonce + AAD", AMBER),
        ("Wrapped key +\nsealed manifest", "sent to API", ROSE),
    ]
    x = 0.7
    for index, (title, body, color) in enumerate(steps):
        rect(slide, x, 2.35, 1.82, 1.7, PANEL)
        rect(slide, x, 2.35, 1.82, 0.06, color)
        text(
            slide,
            title,
            x + 0.1,
            2.6,
            1.62,
            0.62,
            size=12.5,
            color=WHITE,
            bold=True,
            align=PP_ALIGN.CENTER,
        )
        text(slide, body, x + 0.1, 3.32, 1.62, 0.5, size=9.5, color=MUTED, align=PP_ALIGN.CENTER)
        if index < len(steps) - 1:
            arrow(slide, x + 1.85, 3.2, x + 2.03, 3.2, LINE, 1.4)
        x += 2.02
    rect(slide, 0.7, 4.5, 11.9, 1.75, PANEL_2)
    text(slide, "AAD binds every chunk", 0.98, 4.72, 3.5, 0.3, size=13, color=CYAN, bold=True)
    text(
        slide,
        "cryptavault:web:v1:<fileId>:<chunkIndex>:<isFinal>",
        0.98,
        5.09,
        6.4,
        0.32,
        size=13,
        color=WHITE,
        font=MONO,
    )
    text(
        slide,
        "Changing the order, index, final flag, file ID or ciphertext fails authentication before release.",
        0.98,
        5.55,
        10.9,
        0.4,
        size=10.5,
        color=MUTED,
    )
    footer(slide, 5)

    # 6 — Container
    slide = slide_base(
        prs,
        "05 / Wire format",
        "CVW1: the portable container",
        "Web and CLI produce byte-compatible JSON containers.",
    )
    rect(slide, 0.7, 1.95, 6.25, 4.55, rgb("#0F172A"))
    code = (
        "{\n"
        '  "magic": "CVW1",\n'
        '  "v": 1,\n'
        '  "fileId": "31e229ff-...",\n'
        '  "createdAt": "2026-11-08T...",\n'
        '  "profile": "BALANCED",\n'
        '  "compression": "gzip",\n'
        '  "chunkSize": 4194304,\n'
        '  "chunks": [\n'
        '    { "i": 0, "f": 1,\n'
        '      "iv": "base64...",\n'
        '      "ct": "base64..." }\n'
        "  ]\n"
        "}"
    )
    text(
        slide, code, 0.98, 2.16, 5.7, 4.15, size=10.5, color=rgb("#A5F3FC"), font=MONO, spacing=0.95
    )
    bullets(
        slide,
        [
            "A fresh 96-bit nonce per chunk; no key/nonce reuse.",
            "Gzip is optional; the manifest records the real mode.",
            "Chunk size comes from the selected profile (4–16 MiB).",
            "Plaintext SHA-256 is sealed in the manifest for integrity.",
            "Unknown magic/version fails closed — no silent downgrade.",
        ],
        7.3,
        2.1,
        5.15,
        3.5,
        size=13,
        spacing=13,
    )
    rect(slide, 7.3, 5.50, 5.0, 0.9, PANEL_2)
    text(
        slide,
        "Same file: browser upload → CLI download → hash verified",
        7.52,
        5.72,
        4.6,
        0.45,
        size=11,
        color=EMERALD,
        bold=True,
    )
    footer(slide, 6)

    # 7 — Data split
    slide = slide_base(
        prs,
        "06 / Data split",
        "What Neon sees vs what S3 sees",
        "The server can coordinate without content.",
    )
    rect(slide, 0.7, 1.95, 5.8, 4.55, PANEL)
    text(slide, "NEON POSTGRES", 0.98, 2.15, 4, 0.3, size=12, color=INDIGO, bold=True)
    bullets(
        slide,
        [
            "email, display name, account role",
            "auth salt + verifier + KDF iterations",
            "vault salt + sealed vault check",
            "workspace names, members, roles",
            "encrypted manifest + meta IV",
            "wrapped raw key + wrapped IV",
            "ciphertext size, profile, storage key",
            "share token, expiry, uses, revocation",
            "quota, suspension, feature flags",
        ],
        1.0,
        2.62,
        5.1,
        3.4,
        size=12,
        bullet_color=INDIGO,
        spacing=8,
    )
    rect(slide, 6.8, 1.95, 5.8, 4.55, PANEL)
    text(slide, "S3-COMPATIBLE STORAGE", 7.08, 2.15, 4.5, 0.3, size=12, color=AMBER, bold=True)
    bullets(
        slide,
        [
            "CVW1 JSON object per file version",
            "base64 ciphertext chunks",
            "no plaintext, no file name",
            "no master key, no raw file key",
            "storage key: workspaces/<ws>/files/<id>/vN.cv",
            "SeaweedFS locally; S3/R2-compatible contract",
            "health checks and fallback target selection",
        ],
        7.1,
        2.62,
        5.1,
        3.2,
        size=12,
        bullet_color=AMBER,
        spacing=10,
    )
    text(
        slide,
        "The database is useful for policy. It is useless for decryption.",
        0.75,
        6.73,
        11.8,
        0.3,
        size=12,
        color=MUTED,
        italic=True,
        align=PP_ALIGN.CENTER,
    )
    footer(slide, 7)

    # 8 — Web
    slide = slide_base(
        prs,
        "07 / Web client",
        "A live product surface, not a crypto demo",
        "Every page is wired to the FastAPI/Neon/S3 stack.",
    )
    entries = [
        ("Dashboard", "live quota, storage mix, decrypted recents", CYAN),
        ("Vault", "upload, versions, trash, rename, share", EMERALD),
        ("Workspaces", "members, roles, storage target", INDIGO),
        ("Shares", "revoke, use counts, saved links", AMBER),
        ("Admin", "users, quotas, suspension, flags", ROSE),
        ("Status", "health, readiness, WebCrypto self-test", CYAN),
    ]
    for index, (title, body, color) in enumerate(entries):
        col = index % 3
        row = index // 3
        card(
            slide,
            0.7 + col * 4.0,
            1.95 + row * 2.15,
            3.75,
            1.85,
            title,
            body,
            color,
            title_size=14,
            body_size=11,
        )
    rect(slide, 0.7, 6.25, 11.9, 0.58, PANEL_2)
    text(
        slide,
        "Login → PBKDF2 → master key in memory → auto-lock → JWT session → remote workspace switch",
        0.95,
        6.4,
        11.4,
        0.3,
        size=11,
        color=WHITE,
        align=PP_ALIGN.CENTER,
    )
    footer(slide, 8)

    # 9 — CLI
    slide = slide_base(
        prs,
        "08 / CLI",
        "One command group closes the parity gap",
        "The remote CLI uses the same API and container rules as the browser.",
    )
    rect(slide, 0.7, 1.95, 7.15, 4.45, rgb("#0F172A"))
    terminal = (
        "$ cryptavault remote auth login \\\n"
        "    --email demo@cryptavault.dev\n\n"
        "$ cryptavault remote files upload report.pdf \\\n"
        "    --profile BALANCED\n\n"
        "$ cryptavault remote files versions FILE_ID\n"
        "$ cryptavault remote files download FILE_ID \\\n"
        "    --output restored.pdf\n\n"
        "$ cryptavault remote files share FILE_ID \\\n"
        "    --ttl 24 --max-uses 5\n\n"
        "$ cryptavault remote shares decrypt 'http://.../#/s/...'\n"
    )
    text(
        slide,
        terminal,
        0.98,
        2.13,
        6.55,
        4.05,
        size=10.5,
        color=rgb("#A7F3D0"),
        font=MONO,
        spacing=0.95,
    )
    bullets(
        slide,
        [
            "Session file: JWT + vault bootstrap only.",
            "Passphrase prompted per command; master key never stored.",
            "Fresh key and nonce for every version.",
            "Share manifests are web-compatible.",
            "Smoke-tested: v1/v2 round-trip, rename, capability share, passphrase share, delete.",
        ],
        8.15,
        2.05,
        4.3,
        3.8,
        size=12,
        spacing=12,
    )
    footer(slide, 9)

    # 10 — Sharing
    slide = slide_base(
        prs,
        "09 / Secure sharing",
        "The database never stores a decryptable link",
        "Policy is server-enforced; capability material stays in the URL fragment.",
    )
    rect(slide, 0.7, 1.95, 11.9, 0.85, PANEL_2)
    text(
        slide,
        "http://localhost:3000/#/s/<token>?m=<manifest>&k=<capability-key>",
        0.95,
        2.16,
        11.3,
        0.35,
        size=13,
        color=CYAN,
        font=MONO,
    )
    card(
        slide,
        0.7,
        3.05,
        3.75,
        2.15,
        "Manifest m",
        "Name, type, size, hash, profile, compression, chunk count and the share-wrapped file key.",
        INDIGO,
    )
    card(
        slide,
        4.73,
        3.05,
        3.75,
        2.15,
        "Capability k",
        "Random 256-bit key for link shares, or PBKDF2-derived for passphrase shares. Omitted when a passphrase is used.",
        AMBER,
    )
    card(
        slide,
        8.76,
        3.05,
        3.85,
        2.15,
        "Server policy",
        "Token, file/version, expiry, max uses, password verifier, revocation flag, use count.",
        ROSE,
    )
    rect(slide, 0.7, 5.55, 11.9, 0.98, PANEL)
    text(
        slide,
        "Every public download checks:",
        0.95,
        5.74,
        3.2,
        0.3,
        size=11,
        color=WHITE,
        bold=True,
    )
    text(
        slide,
        "not revoked  •  not expired  •  uses < max  •  file live  •  version exists  •  passphrase valid",
        3.75,
        5.74,
        8.55,
        0.3,
        size=11,
        color=EMERALD,
        bold=True,
    )
    footer(slide, 10)

    # 11 — Security analysis table
    slide = slide_base(
        prs,
        "10 / Security analysis",
        "Threats and mitigations",
        "The boundary is explicit, including residual risk.",
    )
    rows = [
        (
            "Database breach",
            "No plaintext, master key, raw file key or capability key",
            "Ciphertext + wrapped keys only",
        ),
        (
            "Object storage breach",
            "AES-GCM ciphertext; per-file keys remain wrapped",
            "No key material in objects",
        ),
        (
            "Chunk tampering / reorder",
            "AAD binds file ID, index and final flag",
            "Decryption fails closed",
        ),
        (
            "Metadata tampering",
            "Manifest sealed with master key and file-bound AAD",
            "Name/size/hash cannot be forged",
        ),
        (
            "Share replay",
            "Revocation, expiry, use limit checked per download",
            "HTTP 410 after policy fails",
        ),
        (
            "Role escalation",
            "JWT identity + workspace role check per route",
            "Owner/admin/editor/viewer",
        ),
        ("Quota abuse", "Pre-upload ciphertext quota check", "HTTP 413"),
    ]
    table_shape = slide.shapes.add_table(
        len(rows) + 1, 3, Inches(0.7), Inches(1.9), Inches(11.9), Inches(4.65)
    )
    table = table_shape.table
    table.columns[0].width = Inches(3.0)
    table.columns[1].width = Inches(4.9)
    table.columns[2].width = Inches(4.0)
    headers = ["Threat", "Control", "Result"]
    for col, value in enumerate(headers):
        cell = table.cell(0, col)
        cell.text = value
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb("#0E7490")
        for p in cell.text_frame.paragraphs:
            for run in p.runs:
                run.font.name = FONT
                run.font.size = Pt(10.5)
                run.font.bold = True
                run.font.color.rgb = WHITE
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row):
            cell = table.cell(row_index, col_index)
            cell.text = value
            cell.fill.solid()
            cell.fill.fore_color.rgb = PANEL if row_index % 2 else PANEL_2
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.name = FONT
                    run.font.size = Pt(9.5)
                    run.font.color.rgb = WHITE if col_index == 0 else MUTED
    text(
        slide,
        "Residual: compromised client, recipient keeps plaintext after revoke, no shared workspace key, no independent audit.",
        0.7,
        6.7,
        11.9,
        0.3,
        size=9.5,
        color=AMBER,
        italic=True,
        align=PP_ALIGN.CENTER,
    )
    footer(slide, 11)

    # 12 — Results
    slide = slide_base(
        prs,
        "11 / Results",
        "A tested, runnable deliverable",
        "Evidence from the local stack and the repository suite.",
    )
    stats = [
        ("165", "Python tests passing", CYAN),
        ("0", "plaintext bytes sent to server", EMERALD),
        ("4", "workspace roles enforced", INDIGO),
        ("2", "clients, one wire format", AMBER),
    ]
    for index, (value, label, color) in enumerate(stats):
        rect(slide, 0.7 + index * 3.05, 1.95, 2.85, 1.55, PANEL)
        text(slide, value, 0.95 + index * 3.05, 2.12, 2.35, 0.7, size=38, color=color, bold=True)
        text(slide, label, 0.97 + index * 3.05, 2.88, 2.4, 0.4, size=9.5, color=MUTED)
    bullets(
        slide,
        [
            "Ruff and mypy clean for core, API and CLI.",
            "Web typecheck and production Vite build pass.",
            "Web/API/Neon/SeaweedFS upload, version, download, share and admin smoke flows pass.",
            "CLI v1/v2 round-trip, rename, capability share, passphrase share and permanent delete pass.",
            "Share policy verified: revoked/exhausted links return HTTP 410.",
        ],
        0.76,
        3.85,
        6.0,
        2.6,
        size=12.5,
        spacing=11,
    )
    rect(slide, 7.15, 3.8, 5.45, 2.4, PANEL_2)
    text(slide, "Zero-knowledge evidence", 7.42, 4.0, 4.8, 0.3, size=13, color=CYAN, bold=True)
    text(
        slide,
        "Neon contains wrapped keys and encrypted manifests. SeaweedFS contains CVW1 JSON. Neither can reconstruct the passphrase, master key or plaintext.",
        7.42,
        4.4,
        4.9,
        1.2,
        size=11,
        color=MUTED,
    )
    text(
        slide,
        "Server cannot read content. Client can verify integrity.",
        7.42,
        5.62,
        4.9,
        0.35,
        size=10.5,
        color=EMERALD,
        bold=True,
    )
    footer(slide, 12)

    # 13 — Demo flow
    slide = slide_base(
        prs,
        "12 / Demonstration",
        "A 10-minute end-to-end path",
        "The same story works in the browser and the terminal.",
    )
    steps = [
        ("1", "Login", "demo@cryptavault.dev", CYAN),
        ("2", "Upload", "gzip + chunk + AES-GCM", EMERALD),
        ("3", "Version", "immutable v2, restore v1", INDIGO),
        ("4", "Share", "expiry + uses + passphrase", AMBER),
        ("5", "Open incognito", "server policy + client decrypt", ROSE),
        ("6", "Revoke", "HTTP 410 on reload", CYAN),
        ("7", "CLI", "same file, same format", EMERALD),
        ("8", "Admin", "quota, roles, health", INDIGO),
    ]
    for index, (number, title, body, color) in enumerate(steps):
        col = index % 4
        row = index // 4
        x = 0.7 + col * 3.05
        y = 2.0 + row * 2.25
        rect(slide, x, y, 2.75, 1.85, PANEL)
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(x + 0.2), Inches(y + 0.2), Inches(0.45), Inches(0.45)
        )
        fill(circle, color)
        no_line(circle)
        text(
            slide,
            number,
            x + 0.2,
            y + 0.27,
            0.45,
            0.3,
            size=12,
            color=BG,
            bold=True,
            align=PP_ALIGN.CENTER,
        )
        text(slide, title, x + 0.78, y + 0.24, 1.75, 0.35, size=14, color=WHITE, bold=True)
        text(slide, body, x + 0.22, y + 0.9, 2.35, 0.65, size=10.5, color=MUTED)
    footer(slide, 13)

    # 14 — Limitations
    slide = slide_base(
        prs,
        "13 / Limitations",
        "What is deliberately not claimed",
        "Final-year rigor means naming the gaps.",
    )
    card(
        slide,
        0.7,
        1.95,
        5.85,
        2.1,
        "No shared workspace vault key",
        "Workspace membership shares policy, not a common key. Another member's uploads need that member's master key.",
        ROSE,
    )
    card(
        slide,
        6.8,
        1.95,
        5.85,
        2.1,
        "No dynamic passphrase rotation",
        "Re-wrapping account keys and migrating all versions is future work; the UI disables the action.",
        AMBER,
    )
    card(
        slide,
        0.7,
        4.25,
        5.85,
        2.1,
        "Cloud connectors are config-ready",
        "Google Drive, Dropbox and OneDrive need OAuth apps and credentials. SeaweedFS is the working demo backend.",
        INDIGO,
    )
    card(
        slide,
        6.8,
        4.25,
        5.85,
        2.1,
        "Streaming and policy scope",
        "Flags now block sharing, versions, cloud connectors and non-admin writes during maintenance. The dynamic path still buffers whole files in memory.",
        CYAN,
    )
    text(
        slide,
        "Next: workspace key envelopes, HMAC content tags, bounded-memory streaming, OAuth connectors, Playwright E2E.",
        0.75,
        6.62,
        11.85,
        0.3,
        size=10.5,
        color=MUTED,
        align=PP_ALIGN.CENTER,
    )
    footer(slide, 14)

    # 15 — Conclusion
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = BG
    rect(slide, 0, 0, 0.12, H, EMERALD, radius=False)
    text(slide, "CONCLUSION", 1.0, 1.0, 5, 0.35, size=11, color=EMERALD, bold=True)
    text(
        slide,
        "CryptaVault proves the boundary.",
        1.0,
        1.5,
        11.2,
        0.85,
        size=42,
        color=WHITE,
        bold=True,
    )
    text(
        slide,
        "A real API, real database, real object storage, browser client and CLI —\n"
        "coordinating files and sharing without holding the keys or the plaintext.",
        1.02,
        2.55,
        10.8,
        0.9,
        size=17,
        color=MUTED,
        spacing=1.15,
    )
    rect(slide, 1.0, 4.15, 11.2, 0.06, CYAN, radius=False)
    text(
        slide,
        "Zero-knowledge is not a claim in the README. It is the shape of the data flow.",
        1.0,
        4.55,
        11.0,
        0.5,
        size=19,
        color=CYAN,
        bold=True,
    )
    text(
        slide,
        "Questions  •  Live demo  •  Code walkthrough",
        1.0,
        5.55,
        9,
        0.4,
        size=14,
        color=WHITE,
    )
    text(slide, "github.com/DHRUV-MULANI/CryptaVault", 1.0, 6.15, 9, 0.35, size=11, color=MUTED)
    footer(slide, 15)

    output = Path("docs/CryptaVault_Dynamic_Stack.pptx")
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    print(output)


if __name__ == "__main__":
    build()
