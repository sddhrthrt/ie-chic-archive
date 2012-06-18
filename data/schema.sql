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

drop table if exists request;
create table request (
  request_id integer primary key autoincrement,
  request_by integer not null,
  url string not null,
  script integer not null,
  description string,
  queued_at	string not null,
  started_at	string not null,
  done_at	string not null,
  frequency	string not null,
  status	string not null	
);

drop table if exists scripts;
create table scripts (
  script_id integer primary key autoincrement,
  script_name string not null,
  script_text string not null,
  script_desc string
);



