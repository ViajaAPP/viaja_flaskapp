alter table public.chat
  alter column tour_instance_id drop not null,
  add column if not exists event_id bigint references public.event (id) on update cascade on delete cascade;

create unique index if not exists chat_event_id_key on public.chat (event_id);

alter table public.chat
  add constraint chat_de_passeio_ou_de_evento check (num_nonnulls(tour_instance_id, event_id) = 1);
