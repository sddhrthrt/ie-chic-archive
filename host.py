# -*- coding: utf-8 -*-
"""
    MiniTwit
    ~~~~~~~~

    A microblogging application written with Flask and sqlite3.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from contextlib import closing
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash
from jinja2 import Environment
from werkzeug import check_password_hash, generate_password_hash
import os

# configuration
DATABASE = 'data/archive.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('MINITWIT_SETTINGS', silent=True)

def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    """Creates the database tables."""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()


def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value) for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv


def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = g.db.execute('select user_id from user where username = ?',
                       [username]).fetchone()
    return rv[0] if rv else None

def get_user(user_id):
    """Convenience method to look up the username for an id."""
    rv = g.db.execute('select username from user where user_id = ?',
                       [user_id]).fetchone()
    return rv[0] if rv else None
app.jinja_env.filters['get_user']=get_user

def get_status(id):
	"""Parse status codes and return verbose status. Filter for Jinja2 templates."""
	statuses={'0': "Not Started", '-1': "Processed at intervals", '1': "Processing", '2': "Complete"}
	return statuses[str(int(id))]
app.jinja_env.filters['get_status']=get_status

def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')


def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address."""
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)

def get_scripts():
	"""Gives all available scripts so new requests can be added based on these scripts"""
	p=os.path.abspath('scripts')
	s=os.listdir(p)
	default_list= ['file', 'site', 'torrent']
	for i in default_list:
		s.remove(i)
	scripts=[]
	for i in s:
		if(i[0:2]=='r_'):
			scripts+=[{'name': i, 'freq': True}]
		else:
			scripts+=[{'name': i}]
	return scripts

@app.before_request
def before_request():
    """Make sure we are connected to the database each request and look
    up the current user so that we know he's there.
    """
    g.db = connect_db()
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?',
                          [session['user_id']], one=True)


@app.teardown_request
def teardown_request(exception):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()


@app.route('/')
def timeline():
    """Shows a users timeline or if no user is logged in it will
    redirect to the public timeline.  This timeline shows the user's
    requests as well as the followed users' requests.
    """
    if not g.user:
        return redirect(url_for('public_timeline'))
    return render_template('timeline.html', requests={'requests':query_db('''
        select requests.*, user.* from requests, user
        where requests.request_by = user.user_id and (
            user.user_id = ? or
            user.user_id in (select whom_id from follower
                                    where who_id = ?))
        order by requests.queued_at desc limit ?''',
        [session['user_id'], session['user_id'], PER_PAGE]), 'scripts':get_scripts()})


@app.route('/public')
def public_timeline():
    """Displays the latest messages of all users."""
    messages=query_db('''
        select requests.*, user.*  from requests, user
        where requests.request_by= user.user_id
        order by requests.queued_at limit ?''', [PER_PAGE])
    return render_template('timeline.html', requests={'requests':messages})


@app.route('/<username>')
def user_timeline(username):
    """Display's a users requests."""
    profile_user = query_db('select * from user where username = ?', [username], one=True)
    if profile_user is None:
		abort(404)
    followed = False
    if g.user:
			followed = query_db('''select 1 from follower where
            follower.who_id = ? and follower.whom_id = ?''',
            [session['user_id'], profile_user['user_id']],
            one=True) is not None
    messages=query_db('''
            select requests.*, user.* from requests, user where
            user.user_id = requests.request_by and user.user_id = ?
            order by requests.queued_at desc limit ?''',
            [profile_user['user_id'], PER_PAGE])
    print messages
    return render_template('timeline.html', requests={'requests':messages, 'followed':followed, 'profile_user':profile_user})


@app.route('/<username>/follow')
def follow_user(username):
    """Adds the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    g.db.execute('insert into follower (who_id, whom_id) values (?, ?)',
                [session['user_id'], whom_id])
    g.db.commit()
    flash('You are now following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))


@app.route('/<username>/unfollow')
def unfollow_user(username):
    """Removes the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    g.db.execute('delete from follower where who_id=? and whom_id=?',
                [session['user_id'], whom_id])
    g.db.commit()
    flash('You are no longer following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))

@app.route('/add_<script>', methods=['POST'])
def add_request(script):
    """Registers a new request for the user."""
    if 'user_id' not in session:
        abort(401)
    if request.form['url']:
			while(1):
					try:
						if 'frequency' in request.form:
							g.db.execute('''insert into requests (request_by, url, script, description, frequency, queued_at, status) values (?, ?, ?, ?, ?, ?, ?)''', (session['user_id'], request.form['url'], script, request.form['description'], request.form['frequency'], int(time.time()),0))
						else:
							g.db.execute('''insert into requests (request_by, url, script, description, frequency, queued_at, status) values (?, ?, ?, ?, ?, ?, ?)''', (session['user_id'], request.form['url'], script, request.form['description'], 0, int(time.time()),0))
						g.db.commit()
						flash('Your request for %s...%s was recorded'%(request.form['url'][:8], request.form['url'][-8:]))
						break
					except:
							print "Add fail - DB busy. Trying again."
							pass

    return redirect(url_for('timeline'))

@app.route('/script_add', methods=['POST'])
def add_script():
	"""Registers a new script"""
	print request.form
	if 'user_id' not in session:
		abort(401)
	if request.form['code'] and request.form['name']:
		fname=str(request.form['name'])
		if 'repeat' in request.form:
			fname='r_'+fname
		fname=os.path.normpath(os.path.join(os.path.abspath('scripts'),fname))
		with open(fname, "w") as f:
			f.write(str(request.form['code']))
		flash('New script %s was added!'%request.form['name'])
	else:
		flash('Script missing name or code itself!')
	return redirect(url_for('timeline'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from user where
            username = ?''', [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id']
            return redirect(url_for('timeline'))
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                 '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            g.db.execute('''insert into user (
                username, email, pw_hash) values (?, ?, ?)''',
                [request.form['username'], request.form['email'],
                 generate_password_hash(request.form['password'])])
            g.db.commit()
            flash('You were successfully registered and were logged in')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('public_timeline'))


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['gravatar'] = gravatar_url


if __name__ == '__main__':
    app.run('0.0.0.0')
