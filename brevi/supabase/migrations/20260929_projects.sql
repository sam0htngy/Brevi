create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  title text not null,
  created_at timestamptz not null default now()
);
