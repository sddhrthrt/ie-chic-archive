# -*- coding: utf-8 -*-
"""
    Flaskr
    ~~~~~~

    A microblog example application written as Flask tutorial with
    Flask and sqlite3.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
from sqlite3 import dbapi2 as sqlite3
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash

# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    """Creates the database tables."""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.before_request
def before_request():
    """Make sure we are connected to the database each request."""
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()


@app.route('/')
def show_entries():
    cur = g.db.execute('select tags from entries order by id desc')
    taglist=[]
    for row in cur:
    	for tag in row[0].split(','):
			print tag
			if tag not in taglist:
				taglist+=[tag]
	print taglist
    cur = g.db.execute('select id, quote, author, tags, sender from entries order by id desc')
    entries = [dict(id=row[0], quote=row[1], author=row[2], tags=row[3].split(','), sender=row[4], alltags=taglist) for row in cur.fetchall()]
    return render_template('show_entries.html', entries=entries)

def getQuotes(tag):
	cur = g.db.execute('select id, quote, author, tags, sender from entries order by id desc')
	entries = [dict(id=row[0], quote=row[1], author=row[2], tags=row[3].split(','), sender=row[4]) for row in cur.fetchall() if not row[3].find(tag)==-1]

@app.route('/add', methods=['GET', 'POST'])
def add_entry():
	
    if not session.get('logged_in'):
        abort(401)
    if(len(request.form['quote'])==0):
    	flash("Entry failed")
	return redirect(url_for('show_entries'))
    if(len(request.form['author'])==0):
	    g.db.execute('insert into entries (quote, author, tags, sender) values (?, ?, ?, ?)',
                 [request.form['quote'], "Anon.", request.form['tags'], USERNAME])
    else:
	    g.db.execute('insert into entries (quote, author, tags, sender) values (?, ?, ?, ?)',
                 [request.form['quote'], request.form['author'], request.form['tags'], USERNAME])
    g.db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['Email'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['Password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


if __name__ == '__main__':
    app.run(host='0.0.0.0')
