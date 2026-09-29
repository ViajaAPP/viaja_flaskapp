alter table public.tour
  add column if not exists published boolean not null default true;

alter table public.tour_instance
  add column if not exists registration text not null default 'OPEN';

alter table public.tour_instance
  drop constraint if exists tour_instance_registration_check;

alter table public.tour_instance
  add constraint tour_instance_registration_check
  check (registration in ('OPEN', 'FULL', 'CLOSED'));

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'tour_request' and column_name = 'last_update'
  ) then
    alter table public.tour_request rename column last_update to last_updated;
  end if;
end $$;

alter table public.tour_request
  add column if not exists last_updated timestamptz;

do $$
declare
  role_type regtype;
begin
  select atttypid::regtype into role_type
  from pg_attribute
  where attrelid = 'public."user"'::regclass and attname = 'role';

  if exists (select 1 from pg_type where oid = role_type and typtype = 'e') then
    execute format('alter type %s add value if not exists %L', role_type, 'ADMIN');
  end if;
end $$;
