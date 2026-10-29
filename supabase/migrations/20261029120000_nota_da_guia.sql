alter table public.tour_review
  add column if not exists guide_rating smallint check (guide_rating is null or guide_rating between 1 and 5);
