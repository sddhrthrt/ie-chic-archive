import os, sqlite3
from time import sleep
try:
    from thread import get_ident
except ImportError:
    from dummy_thread import get_ident


class SqliteQueue(object):

    _create = (
            'CREATE TABLE IF NOT EXISTS queue ' 
            '('
            '  id INTEGER PRIMARY KEY AUTOINCREMENT,'
            '  item string,'
	    '  status integer'
            ')'
            )
    _count = 'SELECT COUNT(*) FROM queue'
    _iterate = 'SELECT id, item, status FROM queue'
    _append = 'INSERT INTO queue (item, status) VALUES (?, ?)'
    _write_lock = 'BEGIN IMMEDIATE'
    _popleft_get = (
            'SELECT id, item, status FROM queue '
            'ORDER BY id LIMIT 1'
            )
    _popleft_del = 'DELETE FROM queue WHERE id = ?'
    _peek = (
            'SELECT item, status FROM queue '
            'ORDER BY id LIMIT 1'
            )

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self._connection_cache = {}
        with self._get_conn() as conn:
            conn.execute(self._create)

    def __len__(self):
        with self._get_conn() as conn:
            l = conn.execute(self._count).next()[0]
        return l

    def __iter__(self):
        with self._get_conn() as conn:
            for id, obj_buffer, status in conn.execute(self._iterate):
                yield (obj_buffer)

    def _get_conn(self):
        id = get_ident()
        if id not in self._connection_cache:
            self._connection_cache[id] = sqlite3.Connection(self.path, 
                    timeout=60)
        return self._connection_cache[id]

    def append(self, obj, status):
        with self._get_conn() as conn:
            conn.execute(self._append, (obj, status)) 

    def popleft(self, sleep_wait=True):
        keep_pooling = True
        wait = 0.1
        max_wait = 2
        tries = 0
        with self._get_conn() as conn:
            id = None
            while keep_pooling:
                conn.execute(self._write_lock)
                cursor = conn.execute(self._popleft_get)
                try:
                    id, obj_buffer, obj_buffer_status = cursor.next()
                    keep_pooling = False
                except StopIteration:
                    conn.commit() # unlock the database
                    if not sleep_wait:
                        keep_pooling = False
                        continue
                    tries += 1
                    sleep(wait)
                    wait = min(max_wait, tries/10 + wait)
            if id:
                conn.execute(self._popleft_del, (id,))
                return obj_buffer
        return None

    def peek(self):
        with self._get_conn() as conn:
            cursor = conn.execute(self._peek)
            try:
                return cursor.next()[0]
            except StopIteration:
                return None

if __name__=='__main__':
	q= SqliteQueue('data/testqueue.db') 
	q.append("First Task", 1)
	q.append("Second Task", 0)

