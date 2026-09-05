# OAuth & Cloud Provider Registration Guide

This document specifies the setup, required scopes, redirect URIs, and credential storage policies for all third-party identity and cloud storage providers supported by CryptaVault.

---

## 1. Security & Zero-Knowledge Credential Policies
1. **Never Commit Secrets**: Client secrets and API keys must never be committed to git.
2. **Storage Location**:
   - Production identity provider credentials (Google, GitHub, Microsoft, Apple) are configured directly in the **Supabase Dashboard** under `Authentication -> Providers`.
   - Local development credentials are kept in untracked `.env.local` or injected via environment variables.
   - Storage provider access tokens (GDrive, OneDrive, Dropbox) are stored encrypted client-side or managed via user-consented OAuth tokens.
3. **Data Minimization**: Cloud storage providers are treated as untrusted blind bit-stores. They only receive encrypted chunks and ciphertext manifests. Plaintext or encryption keys are never sent to third-party APIs.

---

## 2. Authentication Providers (Supabase Auth Integration)

### 2.1 Google Identity & Google Drive
- **Google Cloud Console**: `https://console.cloud.google.com/apis/credentials`
- **Application Type**: Web Application
- **Scopes**:
  - `openid`
  - `https://www.googleapis.com/auth/userinfo.email`
  - `https://www.googleapis.com/auth/userinfo.profile`
  - `https://www.googleapis.com/auth/drive.file` (per-file storage connector access)
- **Authorized JavaScript Origins**:
  - `http://localhost:3000` (Web Client)
  - `http://localhost:3001` (Admin Console)
  - `https://<supabase-project-id>.supabase.co`
- **Authorized Redirect URIs**:
  - `https://<supabase-project-id>.supabase.co/auth/v1/callback`
  - `http://localhost:3000/auth/callback`
  - `http://localhost:8000/api/auth/google/callback`

### 2.2 Microsoft Entra ID (OneDrive + OIDC)
- **Azure Portal / Microsoft Entra**: `https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade`
- **Supported Account Types**: Accounts in any organizational directory and personal Microsoft accounts (e.g. Skype, Xbox, Outlook.com).
- **Scopes (Delegated)**:
  - `openid`
  - `profile`
  - `email`
  - `Files.ReadWrite` (OneDrive storage access)
  - `offline_access`
- **Platform**: Web + Single Page Application (SPA)
- **Redirect URIs**:
  - `https://<supabase-project-id>.supabase.co/auth/v1/callback`
  - `http://localhost:3000/auth/callback`

### 2.3 GitHub OAuth App
- **GitHub Developer Settings**: `https://github.com/settings/developers`
- **Application Name**: CryptaVault
- **Homepage URL**: `http://localhost:3000`
- **Authorization Callback URL**:
  - `https://<supabase-project-id>.supabase.co/auth/v1/callback`
- **Scopes**:
  - `user:email`

### 2.4 Apple (Sign in with Apple) [Optional / Production]
- **Apple Developer Portal**: `https://developer.apple.com/account/resources/identifiers/list`
- **Primary App ID & Service ID**: `io.cryptavault.service`
- **Return URLs**:
  - `https://<supabase-project-id>.supabase.co/auth/v1/callback`

---

## 3. Storage Provider Integrations

### 3.1 Dropbox
- **Dropbox App Console**: `https://www.dropbox.com/developers/apps`
- **Access Type**: Scoped Access -> App folder (`Apps/CryptaVault`) or Full Dropbox
- **Permissions**:
  - `files.content.write`
  - `files.content.read`
  - `account_info.read`
- **Redirect URIs**:
  - `http://localhost:3000/auth/dropbox/callback`
  - `http://localhost:8000/api/storage/dropbox/callback`

---

## 4. Local Development Mocking
For offline automated integration tests and developer workflows without live provider credentials:
- Set `MOCK_OAUTH_PROVIDERS=true` in `packages/api/.env`.
- Mock tokens will be accepted by test endpoints and validated against seeded mock profile records in the local test suite.
