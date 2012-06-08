drop table if exists entries;
create table entries (
  id integer primary key autoincrement,
  quote string not null,
  author string not null,
  tags string not null,
  sender string not null
);
