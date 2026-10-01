alter table public."user"
  add column if not exists bio text check (bio is null or char_length(bio) <= 300);
