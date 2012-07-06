drop table if exists user;
create table user (
  user_id integer primary key autoincrement,
  username string not null,
  email string not null,
  pw_hash string not null
);

drop table if exists follower;
create table follower (
  who_id integer,
  whom_id integer
);

drop table if exists requests;
create table requests (
  request_id integer primary key autoincrement,
  request_by integer not null,
  url string not null,
  script string not null,
  description string,
  queued_at	datetime default current_timestamp,
  started_at datetime,
  done_at	datetime,
  frequency	string,
  status integer not null	
);

drop table if exists scripts;
create table scripts (
  script_id integer primary key autoincrement,
  script_name string not null,
  script_text string not null,
  script_desc string
);

drop table if exists queue;
create table queue (
  id integer primary key autoincrement,
  request_id integer,
  frequency string,
  queued_at datetime,
  status integer not null
);
