drop policy if exists "Enable read access for all users" on public."user";
drop policy if exists "Enable read access for all users" on public.address;
drop policy if exists "Enable read access for all users" on public.tour;
drop policy if exists "Enable insert for authenticated users only" on public.tour;

do $$
declare
  tabela record;
begin
  for tabela in select tablename from pg_tables where schemaname = 'public' loop
    execute format('alter table public.%I enable row level security', tabela.tablename);
  end loop;
end $$;

revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke execute on all functions in schema public from anon, authenticated, public;
grant execute on all functions in schema public to service_role;

alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
alter default privileges in schema public revoke execute on functions from anon, authenticated, public;
