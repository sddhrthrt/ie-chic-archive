create table queue (
  id integer primary key autoincrement,
  request_id integer,
  frequency string,
  status integer not null
);
