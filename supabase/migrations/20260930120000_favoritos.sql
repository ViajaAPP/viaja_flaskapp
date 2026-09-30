create table if not exists public.favorite_tour (
  user_id bigint not null references public."user" (user_id) on update cascade on delete cascade,
  tour_id bigint not null references public.tour (id) on update cascade on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, tour_id)
);

create index if not exists favorite_tour_tour_id_idx on public.favorite_tour (tour_id);

alter table public.favorite_tour enable row level security;
