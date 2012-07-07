import os 
from sqlite3 import dbapi2 as sqlite3
import time
from time import sleep
from datetime import datetime
import subprocess
try:
		from thread import get_ident
except ImportError:
		from dummy_thread import get_ident

def convertToSeconds(frequency):    
		multiplier = {'s':1, 'm':60, 'h':3600, 'd':86400}
		no = int(frequency[:-1])
		return no*multiplier[frequency[-1:]]

class RequestQueue(object): 

		#_create = (
				#'CREATE TABLE IF NOT EXISTS queue ' 
				#'('
				#' 	id INTEGER PRIMARY KEY AUTOINCREMENT,'
				#'  request_id integer,'
				#'  status integer'
				#')'
				#)
		_count = 'SELECT COUNT(*) FROM queue'
		_iterate = 'SELECT id, request_id, frequency, queued_at, status  FROM queue'
		_append = 'INSERT INTO queue (request_id, frequency, queued_at, status) VALUES (?, ?, ?, ?)'
		_write_lock = 'BEGIN IMMEDIATE'
		_popleft_get = (
				'SELECT * FROM queue '
				'ORDER BY id LIMIT 1'
				)
		_popleft_del = 'DELETE FROM queue WHERE id = ?'
		_peek = (
				'SELECT request_id, frequency, queued_at, status FROM queue '
				'ORDER BY id LIMIT 1'
				)
		_peek_cust = (
				'SELECT request_id, frequency, queued_at, status FROM queue '
				'Where id = ?'
				)

		def __init__(self, path):
				self.path = os.path.abspath(path)
				self._connection_cache = {}
				#with self._get_conn() as conn:
						#conn.execute(self._create)

		def __len__(self):
				with self._get_conn() as conn:
						l = conn.execute(self._count).next()[0]
				return l

		def __iter__(self):
				with self._get_conn() as conn:
						for id, obj_buffer, frequency, queued_at, status in conn.execute(self._iterate):
								yield (obj_buffer)

		def _get_conn(self):
				id = get_ident()
				if id not in self._connection_cache:
						self._connection_cache[id] = sqlite3.Connection(self.path, 
								timeout=60)
				return self._connection_cache[id]

		def append(self, obj, frequency, queued_at, status):
				with self._get_conn() as conn:
						conn.execute(self._append, (obj, frequency, queued_at, status)) 

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
										obj_buffer = [dict((cursor.description[idx][0], value) for idx, value in enumerate(row)) for row in cursor.fetchall()]
										keep_pooling = False
								except StopIteration:
										conn.commit() # unlock the database
										if not sleep_wait:
												keep_pooling = False
												continue
										tries += 1
										sleep(wait)
										wait = min(max_wait, tries/10 + wait)
						if obj_buffer:
								conn.execute(self._popleft_del, (obj_buffer[0]['id'],))
								return obj_buffer
				return None
		
		def execute(self, cmd=_peek_cust, cmd_args=(), return_list = False, sleep_wait=True):
				keep_pooling = True
				wait = 0.1
				max_wait = 2
				tries = 0
				with self._get_conn() as conn:
						obj_buffer = None
						while keep_pooling:
								conn.execute(self._write_lock)
								cursor = conn.execute(cmd, cmd_args)
								try:
										if(return_list):
												obj_buffer = cursor.fetchall()
										else:
												obj_buffer = [dict((cursor.description[idx][0], value) for idx, value in enumerate(row)) for row in cursor.fetchall()]
										keep_pooling = False
								except StopIteration:
										conn.commit() # unlock the database
										if not sleep_wait:
												keep_pooling = False
												continue
										tries += 1
										sleep(wait)
										wait = min(max_wait, tries/10 + wait)
						if obj_buffer:
								return obj_buffer
				return None
		def peek(self):  
				with self._get_conn() as conn:
						cursor = conn.execute(self._peek)
						try:
								obj_buffer = [dict((cursor.description[idx][0], value) for idx, value in enumerate(row)) for row in cursor.fetchall()]
								return obj_buffer
						except StopIteration:
								return None
		def add_unfinished(self):
				remaining=self.execute('select * from requests where status = ?', ('0',))
				if not remaining:
						return
				existing = self.execute('select request_id from queue')
				if existing: 
						existing = [r['request_id'] for r in existing]
				else:
						existing = []
				for request in remaining:
						if request['request_id'] not in existing:
								self.append(request['request_id'], request['frequency'], time.time(), request['status'])
								q.execute('update requests set status = ? where request_id = ?', (1, request['request_id'],))
								q.execute('update requests  set started_at = ? where request_id=?', (time.time(), request['request_id']))
		def service_queue(self):
				q.add_unfinished()
				req=self.popleft()
				if(not req):
						return
				else:
						req=req[0]
				if(req['queued_at'] > time.time()):
						self.append(req['request_id'], req['frequency'], req['queued_at'], req['status'])	
						return
				script=self.execute('select script from requests where request_id = ?', (str(req['request_id']),))
				with open('scripts/'+str(script[0]['script']), 'r') as f:
						cmd=f.readline()
				url=self.execute('select url from requests where request_id = ?', (str(req['request_id']),))
				print cmd, url[0]['url']
				subprocess.call([cmd, "'"+url[0]['url']+"'"], shell=True)
				if( not req['frequency'] == 0):
						req['queued_at']=req['queued_at']+convertToSeconds(req['frequency'])
						self.append(req['request_id'], req['frequency'], req['queued_at'], req['status'])	
						return
				else:
						q.execute('update requests set status = ? where request_id = ?', (2, req['request_id'],))
						q.execute('update requests set done_at = ? where request_id = ?', (time.time(), req['request_id']) )
				

if __name__=='__main__':
		q= RequestQueue('data/archive.db')
		#q.append(2,'1d', int(time.time()), 0)
		#while(q.execute('select count(*) from queue', return_list=True)[0][0]>0):
		while(1):
				q.service_queue()
				sleep(2)

