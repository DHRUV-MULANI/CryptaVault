-- 0001_init.sql: Initial CryptaVault Zero-Knowledge Database Schema

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- 1. Profiles Table (extends auth.users)
create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    display_name text,
    role text not null default 'user' check (role in ('user', 'admin', 'auditor')),
    quota_bytes bigint not null default 5368709120, -- 5 GB default
    suspended boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Auto-sync profile creation from auth.users
create or replace function public.handle_new_user()
returns trigger as $$
begin
    insert into public.profiles (id, display_name, role)
    values (new.id, coalesce(new.raw_user_meta_data->>'full_name', new.email), 'user');
    return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- 2. Key Manifests Table (Encrypted Client-Side with Argon2id Master Key)
create table if not exists public.key_manifests (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    encrypted_manifest bytea not null,
    manifest_nonce bytea not null,
    version integer not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint unique_user_manifest unique (user_id)
);

-- 3. Share Tokens Table
create table if not exists public.share_tokens (
    token_id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    file_ref text not null,
    wrapped_key bytea not null,
    password_hash text,
    max_uses integer default 1,
    current_uses integer not null default 0,
    expires_at timestamptz not null,
    created_at timestamptz not null default now()
);

-- 4. Audit Log Table (Append-Only Hash-Chained Tamper-Evident Ledger)
create table if not exists public.audit_log (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete set null,
    operation text not null,
    target text not null,
    metadata jsonb not null default '{}'::jsonb,
    prev_hash text not null,
    entry_hash text not null,
    signature text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_audit_log_user_id on public.audit_log(user_id);
create index if not exists idx_audit_log_created_at on public.audit_log(created_at);

-- 5. Benchmark Results Table
create table if not exists public.benchmark_results (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    algorithm text not null,
    metric text not null,
    value double precision not null,
    created_at timestamptz not null default now()
);

-- 6. Feature Flags Table
create table if not exists public.feature_flags (
    flag text primary key,
    enabled boolean not null default false,
    description text,
    updated_at timestamptz not null default now()
);

-- 7. Sessions Table
create table if not exists public.sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    client_type text not null check (client_type in ('web', 'cli', 'admin')),
    ip_address inet,
    user_agent text,
    revoked boolean not null default false,
    created_at timestamptz not null default now(),
    last_active timestamptz not null default now()
);

create index if not exists idx_sessions_user_id on public.sessions(user_id);
