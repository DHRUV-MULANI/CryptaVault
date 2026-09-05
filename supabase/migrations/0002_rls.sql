-- 0002_rls.sql: Row Level Security Policies for CryptaVault
-- Enforces strict client-side zero-knowledge boundaries and role-based access control.

-- Enable RLS across all application tables
alter table public.profiles enable row level security;
alter table public.key_manifests enable row level security;
alter table public.share_tokens enable row level security;
alter table public.audit_log enable row level security;
alter table public.benchmark_results enable row level security;
alter table public.feature_flags enable row level security;
alter table public.sessions enable row level security;

-- Role evaluation helpers (Security Definer to query profiles safely)
create or replace function public.is_admin()
returns boolean as $$
begin
    return exists (
        select 1 from public.profiles
        where id = auth.uid() and role = 'admin'
    );
end;
$$ language plpgsql security definer;

create or replace function public.is_auditor()
returns boolean as $$
begin
    return exists (
        select 1 from public.profiles
        where id = auth.uid() and role in ('admin', 'auditor')
    );
end;
$$ language plpgsql security definer;

-- ====================================================================
-- 1. Profiles Table RLS Policies
-- ====================================================================
create policy "profiles_select_own_or_admin"
    on public.profiles for select
    using (auth.uid() = id or public.is_admin());

create policy "profiles_update_own_or_admin"
    on public.profiles for update
    using (auth.uid() = id or public.is_admin())
    with check (
        (auth.uid() = id and role = (select role from public.profiles where id = auth.uid()))
        or public.is_admin()
    );

-- ====================================================================
-- 2. Key Manifests Table RLS Policies (ZERO-KNOWLEDGE INVARIANT)
-- Strict user isolation: No admin bypass allowed for cryptographic manifests!
-- ====================================================================
create policy "key_manifests_select_owner_only"
    on public.key_manifests for select
    using (auth.uid() = user_id);

create policy "key_manifests_insert_owner_only"
    on public.key_manifests for insert
    with check (auth.uid() = user_id);

create policy "key_manifests_update_owner_only"
    on public.key_manifests for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "key_manifests_delete_owner_only"
    on public.key_manifests for delete
    using (auth.uid() = user_id);

-- ====================================================================
-- 3. Share Tokens Table RLS Policies
-- ====================================================================
create policy "share_tokens_owner_crud"
    on public.share_tokens for all
    using (auth.uid() = owner_id)
    with check (auth.uid() = owner_id);

create policy "share_tokens_recipient_read"
    on public.share_tokens for select
    using (
        expires_at > now()
        and current_uses < max_uses
    );

create policy "share_tokens_claim_increment"
    on public.share_tokens for update
    using (
        expires_at > now()
        and current_uses < max_uses
    )
    with check (
        current_uses <= max_uses
    );

-- ====================================================================
-- 4. Audit Log Table RLS Policies (Append-Only Tamper Evident)
-- ====================================================================
create policy "audit_log_insert_authenticated"
    on public.audit_log for insert
    with check (auth.uid() is not null or auth.role() = 'service_role');

create policy "audit_log_select_own_or_auditor"
    on public.audit_log for select
    using (auth.uid() = user_id or public.is_auditor());

-- Note: No UPDATE or DELETE policies created for audit_log to guarantee immutability.

-- ====================================================================
-- 5. Benchmark Results Table RLS Policies
-- ====================================================================
create policy "benchmark_select_own_or_admin"
    on public.benchmark_results for select
    using (auth.uid() = user_id or public.is_admin());

create policy "benchmark_insert_own"
    on public.benchmark_results for insert
    with check (auth.uid() = user_id);

-- ====================================================================
-- 6. Feature Flags Table RLS Policies
-- ====================================================================
create policy "feature_flags_select_all"
    on public.feature_flags for select
    using (true);

create policy "feature_flags_admin_manage"
    on public.feature_flags for all
    using (public.is_admin())
    with check (public.is_admin());

-- ====================================================================
-- 7. Sessions Table RLS Policies
-- ====================================================================
create policy "sessions_select_own_or_admin"
    on public.sessions for select
    using (auth.uid() = user_id or public.is_admin());

create policy "sessions_update_own_or_admin"
    on public.sessions for update
    using (auth.uid() = user_id or public.is_admin())
    with check (auth.uid() = user_id or public.is_admin());

create policy "sessions_delete_own_or_admin"
    on public.sessions for delete
    using (auth.uid() = user_id or public.is_admin());
