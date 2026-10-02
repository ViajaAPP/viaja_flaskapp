insert into public."user" (user_id, username, first_name, last_name, email, password, phone, role, photo, cnpj) values
  (1, 'guia', 'Fabi', 'Guia', 'guia@viaja.local', '$2b$12$aD0mNS8fD7uup764CN37ZOkFj3vp.lihqNSFU4OiuRdLb3d7TLfja', '11999990001', 'GUIDE', 'https://i.pravatar.cc/150?img=47', '12345678000190'),
  (2, 'viajante', 'Tito', 'Viajante', 'viajante@viaja.local', '$2b$12$aD0mNS8fD7uup764CN37ZOkFj3vp.lihqNSFU4OiuRdLb3d7TLfja', '11999990002', 'TOURIST', 'https://i.pravatar.cc/150?img=12', null),
  (3, 'admin', 'Ana', 'Admin', 'admin@viaja.local', '$2b$12$aD0mNS8fD7uup764CN37ZOkFj3vp.lihqNSFU4OiuRdLb3d7TLfja', '11999990003', 'ADMIN', '', null),
  (4, 'produtor', 'Lia', 'Produtora', 'produtor@viaja.local', '$2b$12$aD0mNS8fD7uup764CN37ZOkFj3vp.lihqNSFU4OiuRdLb3d7TLfja', '11999990004', 'EVENT_PROMOTER', 'https://i.pravatar.cc/150?img=32', null);

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

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11250597', 'SP', 'Bertioga', 'Jardim Vicente de Carvalho', 'Rua Manoel Gajo', 's/n')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Vila de Itatinga: bondinho centenário na Serra do Mar', 'Você atravessa o Rio Itapanhaú de barco e segue 7,5 km num bondinho histórico pela mata até a vila inglesa de 1910, construída para a usina hidrelétrica. Lá dentro dá para ver o antigo cinema, o campo do clube e a Igreja de Nossa Senhora da Conceição. A vila fica numa área de preservação, então a visita só acontece com monitor credenciado e reserva feita até quarta-feira.', 150, 'Portinho de Itatinga', 240, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/9/99/Constru%C3%A7%C3%A3o_da_Usina_de_Itatinga.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Vila de Itatinga: bondinho centenário na Serra do Mar')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 10, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-17 07:30:00-03'::timestamptz), ('2026-11-07 07:30:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11256230', 'SP', 'Bertioga', 'Rio da Praia', 'Rua Pastor Djalma da Silva Coimbra', '1277')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Trilha d''Água: barco no Itapanhaú e ruínas da usina', 'Começa com uma travessia curta de barco pelo Rio Itapanhaú e segue por uns 6 km de caminhada, em que a mata vai de mangue a restinga e floresta de encosta. No caminho aparecem a linha do bondinho de Itatinga, a ponte de ferro do Rio Guaxanduva e ruínas de barragem, até uma piscina natural. Só pode ser feita com monitor credenciado.', 180, 'Base de saída da travessia no Rio da Praia', 210, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/e/ed/Bertioga_trip_set_%28November_2022%29_224.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Trilha d''Água: barco no Itapanhaú e ruínas da usina')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 15, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-18 08:00:00-03'::timestamptz), ('2026-11-08 08:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11267555', 'SP', 'Bertioga', 'Costa do Sol', 'Avenida Pontal de Guaratuba', 's/n')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Cachoeira do Guaratuba e Poço do Limão', 'São uns 8 km, ida e volta, pela planície do Parque Estadual Restinga de Bertioga, onde a restinga vai virando floresta fechada. A primeira parada é para mergulhar no Poço do Limão, e depois vem a Cachoeira do Guaratuba. A trilha é de nível médio e exige monitor credenciado e agendamento.', 200, 'Entrada do Loteamento Costa do Sol', 360, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/0/05/Parque_Estadual_Restinga_de_Bertioga_%28PERB%29.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Cachoeira do Guaratuba e Poço do Limão')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 15, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-24 07:00:00-03'::timestamptz), ('2026-11-14 07:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11252312', 'SP', 'Bertioga', 'São João', 'Rodovia Dr. Manoel Hipólito do Rego', 'km 226')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Cachoeira da Torre 47', 'A trilha cruza a ponte sobre o Rio Jaguareguava e entra na Serra do Mar até a torre de transmissão 47, a que leva a energia de Itatinga até o Porto de Santos. Ao lado dela fica a cachoeira, com piscina natural para descansar. São cerca de 8 km ida e volta, sempre com monitor credenciado.', 200, 'Km 226 da Rodovia Dr. Manoel Hipólito do Rego', 300, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/0/01/Parque_Estadual_Restinga_de_Bertioga_-_Trilha_dos_Pinto.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Cachoeira da Torre 47')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 12, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-25 07:30:00-03'::timestamptz), ('2026-11-15 07:30:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11252080', 'SP', 'Bertioga', 'São João', 'Rua Mario Bottosi', '104')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Canoa no Rio Jaguareguava', 'Você rema de canoa canadense ou caiaque por águas calmas e cristalinas, entre trechos de mangue e prainhas que aparecem na maré baixa, com parada para banho de rio. Tem catamarã adaptado para quem tem mobilidade reduzida. O passeio é agendado e acompanhado por monitor ambiental.', 90, 'Jaguareguava Ecoturismo', 120, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/b/b7/Bertioga_%28March_2023%29_071.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Canoa no Rio Jaguareguava')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 12, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-17 09:00:00-03'::timestamptz), ('2026-11-01 09:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11262006', 'SP', 'Bertioga', 'Riviera de São Lourenço', 'Passeio da Riviera', '140')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Restinga e praia do Itaguaré', 'Uma caminhada plana pela restinga do parque até o canal do Itaguaré, onde o rio encontra o mar. No caminho dá para ver aves, inclusive as migratórias, e no fim tem banho de rio e de mar. Dá para ir sozinho, mas com guia você entende muito mais da vegetação e dos bichos que aparecem.', 120, 'Fim da praia da Riviera, no início da trilha', 120, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/4/43/Floresta_de_Restinga_-_Bertioga.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Restinga e praia do Itaguaré')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 15, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-18 08:30:00-03'::timestamptz), ('2026-11-21 08:30:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11250045', 'SP', 'Bertioga', 'Centro', 'Avenida Vicente de Carvalho', '32')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Escuna pelo Canal de Bertioga', 'A escuna sai do canal e passa pelos fortes São João e São Luiz, pela Prainha Branca, pela Praia Preta e pelas ilhas do Guará e Rasa. No meio do caminho tem uma parada de uns 20 minutos para mergulho. É um passeio leve, bom para ir com a família.', 60, 'Píer Licurgo Mazzoni, perto da balsa', 120, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/1/16/SP_Bertioga_-_Canal_de_Bertioga.JPG', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Escuna pelo Canal de Bertioga')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 20, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-17 10:00:00-03'::timestamptz), ('2026-11-07 10:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11010260', 'SP', 'Santos', 'Valongo', 'Largo Marquês de Monte Alegre', '2')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Centro Histórico de Santos de bonde e a pé', 'O passeio começa na Estação do Valongo e segue de bonde histórico pelas igrejas do Valongo, do Carmo e do Rosário, pela Casa da Frontaria Azulejada e pelo Museu do Café, com trechos a pé pelas ruas do porto antigo. O guia vai contando quase 500 anos de história do café e do porto.', 50, 'Estação do Valongo, na bilheteria do bonde', 180, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/0/0b/Valongo_Station.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Centro Histórico de Santos de bonde e a pé')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 20, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-24 09:30:00-03'::timestamptz), ('2026-11-14 09:30:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11013220', 'SP', 'Santos', 'Centro', 'Praça Correa de Melo', '33')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Monte Serrat de funicular', 'O funicular alemão de 1927 sobe 147 metros em uns 4 minutos. Lá em cima ficam o antigo cassino, o Santuário de Nossa Senhora do Monte Serrat e uma vista de Santos e do porto inteiro. Quem quiser pode descer pela escadaria de 402 degraus.', 44, 'Estação de embarque do funicular', 90, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/5/5e/Bonde_Funicular_do_Monte_Serrat_-_Esta%C3%A7%C3%A3o_de_Embarque_-_panoramio.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Monte Serrat de funicular')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 20, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-24 14:00:00-03'::timestamptz), ('2026-11-14 14:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11030400', 'SP', 'Santos', 'Ponta da Praia', 'Avenida Almirante Saldanha da Gama', 's/n')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Escuna pela Baía de Santos', 'A escuna sai da Ponta da Praia e passa pela Fortaleza da Barra Grande, pela Ilha das Palmas e pelo canal do porto, com parada de uns 30 minutos para banho no Sangava. Na volta, a vista é da orla e dos navios nos terminais.', 60, 'Ponte Edgard Perdigão, na Ponta da Praia', 90, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/0/08/Santos_Ponta_da_Praia.JPG', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Escuna pela Baía de Santos')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 20, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-25 10:00:00-03'::timestamptz), ('2026-11-15 10:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11325000', 'SP', 'São Vicente', 'Japuí', 'Avenida Tupiniquins', '1009')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Trilha e Praia de Itaquitanduva', 'São uns 4 km de Mata Atlântica no Parque Estadual Xixová-Japuí, com árvores centenárias e mirantes, até duas faixas de areia separadas por costão, numa das praias mais selvagens da Baixada. A trilha exige monitor e agendamento, e o parque recebe no máximo 40 pessoas por dia.', 90, 'Centro de Visitantes do Parque Estadual Xixová-Japuí', 240, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/9/9a/Vista_da_praia_de_Itaquitanduva.JPG', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Trilha e Praia de Itaquitanduva')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 15, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-31 08:00:00-03'::timestamptz), ('2026-11-21 08:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11321000', 'SP', 'São Vicente', 'Itararé', 'Avenida Ayrton Senna da Silva', '500')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Teleférico do Voturuá e Mirante da Ilha Porchat', 'O teleférico sobe 11 minutos por cima da mata, da Praia do Itararé até o Morro do Voturuá, de onde dá para ver a Baixada inteira. Depois o grupo vai até o monumento de Oscar Niemeyer no alto da Ilha Porchat, a 76 metros do mar. O guia vai ligando as duas vistas com a história da cidade.', 80, 'Base do teleférico, na Praia do Itararé', 150, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/4/49/S%C3%A3o_Vicente_Chairlift_2019_002.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Teleférico do Voturuá e Mirante da Ilha Porchat')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 20, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-31 15:00:00-03'::timestamptz), ('2026-11-22 15:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11310090', 'SP', 'São Vicente', 'Centro', 'Praça Vinte e Dois de Janeiro', 's/n')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Marco zero do Brasil: Centro Histórico de São Vicente', 'A caminhada passa pela Praça 22 de Janeiro, marco da fundação da cidade em 1532, pela Biquinha de Anchieta, de 1553, e pela Casa Martim Afonso. O passeio termina na Ponte Pênsil, de 1914, na hora do pôr do sol.', 50, 'Biquinha de Anchieta, na Praça 22 de Janeiro', 120, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/6/6d/Biquinha_SV.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Marco zero do Brasil: Centro Histórico de São Vicente')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 20, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-11-01 16:00:00-03'::timestamptz), ('2026-11-22 16:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11712010', 'SP', 'Praia Grande', 'Melvi', 'Avenida Wilson de Oliveira', '2074')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Cachoeira do Laranjal', 'São uns 3 km de mata fechada no Parque Estadual da Serra do Mar até quatro poços de água cristalina para mergulhar, com vista da orla lá embaixo. A trilha exige monitor ambiental e agendamento, e funciona de quarta a domingo.', 80, 'Base Guariúma do Núcleo Itutinga-Pilões', 180, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/1/14/A_Serra_do_Mar_e_a_Baixada_Santista.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Cachoeira do Laranjal')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 15, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-24 09:00:00-03'::timestamptz), ('2026-11-28 09:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11726010', 'SP', 'Praia Grande', 'Sítio do Campo', 'Rua Paulo Sérgio Garcia', '18531')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Café da manhã e canoa no Portinho', 'Você rema em águas calmas do estuário, de colete e remo fornecidos, com o mangue e as aves em volta. Depois dá para emendar com o café da manhã do Portinho Marina. Nos fins de semana lota, então vale reservar antes.', 40, 'Portinho Marina', 90, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/2/22/Praia_Grande-_Portinho-SP_-Brasil_-_panoramio.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Café da manhã e canoa no Portinho')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 12, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-25 08:00:00-03'::timestamptz), ('2026-11-29 08:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11746018', 'SP', 'Itanhaém', 'Praia dos Sonhos', 'Avenida Presidente Kennedy', '125')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Barco pelo Rio Itanhaém até o encontro dos rios', 'O barco sai da Boca da Barra e sobe o rio entre manguezais até o encontro das águas escuras do Rio Preto com as claras do Rio Branco. No caminho é comum ver colhereiro, guará-vermelho e biguatinga.', 45, 'Embarque na margem do rio, na Praia dos Sonhos', 150, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/f/f0/Vista_do_rio_itanhem.JPG', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Barco pelo Rio Itanhaém até o encontro dos rios')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 20, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-10-31 09:30:00-03'::timestamptz), ('2026-11-28 09:30:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11740040', 'SP', 'Itanhaém', 'Centro', 'Praça Carlos Botelho', 's/n')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Centro histórico de Itanhaém: Convento e Matriz', 'O roteiro passa pelo Convento de Nossa Senhora da Conceição, com paredes de pedra unidas com óleo de baleia, pela Igreja Matriz de Sant''Anna, que guarda telas de Benedito Calixto, e pela Casa de Câmara e Cadeia. Tudo seguindo os passos do padre José de Anchieta.', 50, 'Convento de Nossa Senhora da Conceição', 90, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/1/1d/Igreja_e_Convento_de_Nossa_Senhora_da_Concei%C3%A7%C3%A3o%2C_Itanha%C3%A9m_01.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Centro histórico de Itanhaém: Convento e Matriz')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 20, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-11-01 10:00:00-03'::timestamptz), ('2026-11-29 10:00:00-03'::timestamptz)) as datas(inicio);

with endereco as (
  insert into public.address (cep, uf, city, neighborhood, street, number)
  values ('11746074', 'SP', 'Itanhaém', 'Praia dos Sonhos', 'Rua da Enseada', '6')
  on conflict (cep, neighborhood, street, number) do update set city = excluded.city
  returning id
), passeio as (
  insert into public.tour (created_by_id, title, description, price, meeting_point, estimated_duration_minutes, address_id, photo, published)
  select (select user_id from public."user" where email = 'guia@viaja.local'), 'Passarela e Cama de Anchieta', 'Uma passarela de madeira de 220 metros sobre as pedras e o mar leva à rocha onde, conta a tradição, Anchieta descansava. O passeio emenda com a Gruta de Nossa Senhora de Lourdes e o Morro do Paranambuco, que tem painéis de azulejo e vista para o pôr do sol.', 40, 'Entrada da passarela', 90, endereco.id, 'https://upload.wikimedia.org/wikipedia/commons/a/ae/ROGERIO_CASSIMIRO-SP_Itanhaem_passarela_e_cama_de_anchieta_%2840845861022%29.jpg', true
  from endereco
  where not exists (select 1 from public.tour where title = 'Passarela e Cama de Anchieta')
  returning id
)
insert into public.tour_instance (tour_id, start_time, max_capacity, status, registration)
select passeio.id, datas.inicio, 20, 'SCHEDULED', 'OPEN'
from passeio, (values ('2026-11-01 16:30:00-03'::timestamptz), ('2026-11-29 16:30:00-03'::timestamptz)) as datas(inicio);
