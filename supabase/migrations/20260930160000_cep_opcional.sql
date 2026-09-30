alter table public.address
  alter column cep drop not null;

alter table public.address
  drop constraint if exists address_cep_check;

alter table public.address
  add constraint address_cep_check check (cep is null or cep ~ '^[0-9]{8}$');
