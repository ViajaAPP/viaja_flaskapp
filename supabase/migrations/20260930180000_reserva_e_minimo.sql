alter type public.request_status add value if not exists 'EXPIRED';
alter type public.request_status add value if not exists 'CANCELLED';

alter table public.tour
  add column if not exists instant_booking boolean not null default false,
  add column if not exists min_participants integer not null default 1;

alter table public.tour
  drop constraint if exists tour_min_participants_check;

alter table public.tour
  add constraint tour_min_participants_check check (min_participants >= 1);
