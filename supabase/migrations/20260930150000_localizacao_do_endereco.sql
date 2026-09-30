alter table public.address
  add column if not exists lat double precision,
  add column if not exists lon double precision,
  add column if not exists ibge_code bigint;

alter table public.address
  drop constraint if exists address_lat_check,
  drop constraint if exists address_lon_check;

alter table public.address
  add constraint address_lat_check check (lat is null or lat between -90 and 90),
  add constraint address_lon_check check (lon is null or lon between -180 and 180);
