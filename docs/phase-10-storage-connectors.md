# Phase P10 — Storage Connectors (Week 12)

## Objective
Implement the `StorageConnector` ABC, mock connector, and concrete connectors for Local filesystem, SFTP, FTP, Google Drive, OneDrive, Dropbox, plus URI auto-detection.

## Prerequisites
- P0 (Setup Gate) — OAuth credentials obtained for GDrive/OneDrive/Dropbox.
- P7 (Pipeline Gate) — pipeline orchestrator ready to integrate storage.

## Tasks

### Task 10.1 — StorageConnector ABC + Mock Connector
**Files**: `packages/core/cryptavault/storage/base.py`
**Action**:
- `StorageConnector` ABC: `authenticate()`, `upload(stream, remote_path)`, `download(remote_path) -> stream`, `list(prefix)`, `delete(remote_path)`, `stat(remote_path)`, `move(src, dst)`, `mkdir(path)`.
- Streams = file-like or generators (no full load).
- `MockStorage` in-memory dict for unit tests.
**Verify**: Mock round-trips all methods; streaming download yields chunks.
**Done**: ABC contract clear; mock enables pipeline tests without network.

### Task 10.2 — Local Filesystem Connector
**Files**: `packages/core/cryptavault/storage/local.py`
**Action**:
- `LocalStorage(root_path)`: maps remote paths to FS paths; streaming read/write; atomic upload (write tmp + rename).
**Verify**: Round-trip 100MB; nested dirs; move across dirs.
**Done**: Local connector works; streaming; atomic writes.

### Task 10.3 — SFTP Connector
**Files**: `packages/core/cryptavault/storage/sftp.py`
**Action**:
- `SftpStorage(host, port, username, key_path_or_password)` via Paramiko.
- Streaming upload/download via `SFTPClient.putfo/getfo`; connection pooling; reconnect on failure.
**Verify**: Round-trip vs `atmoz/sftp` docker; key + password auth.
**Done**: Round-trips via SFTP; streaming; failures retried.

### Task 10.4 — FTP Connector
**Files**: `packages/core/cryptavault/storage/ftp.py`
**Action**:
- `FtpStorage(host, port, username, password)` via stdlib `ftplib`; PASV; FTP-S if supported.
- Streaming via `storbinary`/`retrbinary`.
**Verify**: Round-trip vs `vsftpd` docker.
**Done**: FTP round-trips; PASV used.

### Task 10.5 — Google Drive Connector
**Files**: `packages/core/cryptavault/storage/cloud/gdrive.py`
**Action**:
- `GoogleDriveStorage`: OAuth via `google-auth` + `google-api-python-client`; scope `drive.file`.
- Resumable upload for ≥100MB; streaming download via `get_media`.
- Map remote paths → Drive file IDs; cache locally.
**Verify**: OAuth dance; round-trip 50MB; resumable interrupted → resumes.
**Done**: OAuth works; 50MB round-trip; resumable upload.

### Task 10.6 — OneDrive Connector
**Files**: `packages/core/cryptavault/storage/cloud/onedrive.py`
**Action**:
- `OneDriveStorage`: OAuth via MSAL; Graph `/me/drive/items`.
- Chunked upload via `createUploadSession`; download via `/content`.
**Verify**: OAuth dance; round-trip 50MB; resumable.
**Done**: OAuth works; 50MB round-trip; chunked upload.

### Task 10.7 — Dropbox Connector + URI Auto-Detection
**Files**: `packages/core/cryptavault/storage/cloud/dropbox.py`, `packages/core/cryptavault/storage/registry.py`, `docs/storage_uris.md`
**Action**:
- `DropboxStorage`: OAuth2 via `dropbox` SDK; scope `files.content.readwrite`.
- Chunked upload via `upload_session/start→append→finish` for ≥150MB; streaming download via `download_iter`.
- `resolve_storage(uri) -> StorageConnector` parses `local://`, `sftp://`, `ftp://`, `gdrive://`, `onedrive://`, `dropbox://`.
**Verify**: Dropbox round-trip 50MB; URI auto-detection for each scheme.
**Done**: Dropbox works; URI resolution unified; documented.

## Phase Gate Criteria (Storage Gate)
- [ ] ABC + mock enable pipeline tests without network
- [ ] Local connector with atomic writes
- [ ] SFTP + FTP round-trip 100MB
- [ ] GDrive + OneDrive + Dropbox round-trip 50MB with OAuth
- [ ] URI auto-detection resolves all 6 schemes

## Risks
- R3 (OAuth approval) — should be completed by Week 12 since started in P0.