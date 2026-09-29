insert into public."user" (user_id, username, first_name, last_name, email, password, phone, role, photo, cnpj) values
  (1, 'guia', 'Gabi', 'Guia', 'guia@viaja.local', '$2b$12$aD0mNS8fD7uup764CN37ZOkFj3vp.lihqNSFU4OiuRdLb3d7TLfja', '11999990001', 'GUIDE', 'https://i.pravatar.cc/150?img=47', '12345678000190'),
  (2, 'viajante', 'Tito', 'Viajante', 'viajante@viaja.local', '$2b$12$aD0mNS8fD7uup764CN37ZOkFj3vp.lihqNSFU4OiuRdLb3d7TLfja', '11999990002', 'TOURIST', 'https://i.pravatar.cc/150?img=12', null),
  (3, 'admin', 'Ana', 'Admin', 'admin@viaja.local', '$2b$12$aD0mNS8fD7uup764CN37ZOkFj3vp.lihqNSFU4OiuRdLb3d7TLfja', '11999990003', 'ADMIN', '', null);

insert into public.address (id, cep, uf, city, neighborhood, street, number) values
  (1, '11250000', 'SP', 'Bertioga', 'Centro', 'Rua das Flores', '10');

insert into public.tour (id, created_by_id, title, description, price, estimated_duration_minutes, meeting_point, photo, address_id, published) values
  (1, 1, 'Trilha da Cachoeira', 'Caminhada leve até a cachoeira, com parada para banho no poço.', 80, 180, 'Praça da Matriz', 'https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800', 1, true);

insert into public.tour_instance (id, tour_id, start_time, max_capacity, status) values
  (1, 1, now() + interval '7 days', 8, 'SCHEDULED');

select setval(pg_get_serial_sequence('public."user"', 'user_id'), (select max(user_id) from public."user"));
select setval(pg_get_serial_sequence('public.address', 'id'), (select max(id) from public.address));
select setval(pg_get_serial_sequence('public.tour', 'id'), (select max(id) from public.tour));
select setval(pg_get_serial_sequence('public.tour_instance', 'id'), (select max(id) from public.tour_instance));
