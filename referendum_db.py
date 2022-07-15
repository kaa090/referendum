import sqlite3
import datetime
import logging
from config import FILE_DB

def db_connect():
	try:
		con = sqlite3.connect(FILE_DB)
		return con
	except sqlite3.Error as e:
		logging.critical(e)

def create_tables():	
	con = db_connect()
	cur = con.cursor()

	cur.execute('''CREATE TABLE IF NOT EXISTS referendums(
						chat_id integer, 
						msg_id integer, 
						status integer,
						title text,
						max_num integer,
						game_cost integer,
						user_id integer,
						user_name text,
						datum text,
						PRIMARY KEY(chat_id, msg_id))''')

	cur.execute('''CREATE TABLE IF NOT EXISTS rfr_buttons(
						chat_id integer, 
						msg_id integer,
						button_id integer,
						button_factor integer,
						button_text text,					
						PRIMARY KEY(chat_id, msg_id, button_id))''')

	cur.execute('''CREATE TABLE IF NOT EXISTS rfr_log(
						chat_id integer, 
						msg_id integer, 
						button_id integer, 
						user_id integer,
						user_name text, 
						datum text,
						button_status integer, 
						PRIMARY KEY(chat_id, msg_id, button_id, user_id, user_name, datum))''')

	cur.execute('''CREATE TABLE IF NOT EXISTS regular_players(
						chat_id integer, 
						user_id integer,
						user_name text, 
						player_type integer,
						PRIMARY KEY(chat_id, user_id))''')

	con.commit()
	con.close()

def exec_sql(sql, vals):
	con = db_connect()	
	cur = con.cursor()

	try:
		rows = cur.executemany(sql, vals).fetchall()		
		con.commit()
		con.close()
		return rows
	except sqlite3.Error as e:
		logging.warning(e)

def create_referendum_db(chat_id, msg_id, user_id, user_name, args):
	max_num = args[0]
	game_cost = args[1]
	factors = args[2].split(",")
	title = args[3]
	args = args[4:]
	
	sql = '''INSERT INTO referendums
				(chat_id, msg_id, status, title, max_num, game_cost, user_id, user_name, datum) 
				VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'''
	row = [(chat_id, msg_id, 1, title, max_num, game_cost, user_id, user_name, datetime.datetime.now())]
	exec_sql(sql, row)

	rows = []
	for button_id in range(1, len(args) + 1):
		rows.append((chat_id, msg_id, button_id, int(factors[button_id - 1]), args[button_id - 1]))

	sql = '''INSERT INTO rfr_buttons
				(chat_id, msg_id, button_id, button_factor, button_text)
				VALUES(?, ?, ?, ?, ?)'''
	exec_sql(sql, rows)

def get_referendums_by_user_id_db(chat_id, user_id):
	referendums = []
	
	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''SELECT * FROM referendums
				WHERE referendums.chat_id = {} and
						referendums.status = {} and
						referendums.user_id = {}
			'''.format(chat_id, 1, user_id)

	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:
		referendum = {}
		
		referendum['msg_id'] = row['msg_id']
		referendum['status'] = row['status']
		referendum['title'] = row['title']
		referendum['max_num'] = row['max_num']
		referendum['game_cost'] = row['game_cost']
		referendum['user_id'] = row['user_id']

		referendums.append(referendum)

	return referendums

def get_referendum_db(chat_id, msg_id):
	referendum_params = {}

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''SELECT * FROM referendums
				WHERE referendums.chat_id = {} and
						referendums.msg_id = {}
			'''.format(chat_id, msg_id)

	row = cur.execute(sql).fetchone()

	if row:
		referendum_params['status'] = row['status']
		referendum_params['title'] = row['title']
		referendum_params['max_num'] = row['max_num']
		referendum_params['game_cost'] = row['game_cost']
		referendum_params['user_id'] = row['user_id']

	return referendum_params

def update_referendum_db(chat_id, msg_id, title, max_num, game_cost):
	if title:
		sql = '''UPDATE referendums
					SET title = ?
					WHERE chat_id = ? and
							msg_id = ?'''
		row = [(title, chat_id, msg_id)]
		exec_sql(sql, row)

	if max_num:
		sql = '''UPDATE referendums
					SET max_num = ?
					WHERE chat_id = ? and
							msg_id = ?'''
		row = [(max_num, chat_id, msg_id)]
		exec_sql(sql, row)

	if game_cost:
		sql = '''UPDATE referendums
					SET game_cost = ?
					WHERE chat_id = ? and
							msg_id = ?'''
		row = [(game_cost, chat_id, msg_id)]
		exec_sql(sql, row)

def set_referendum_status_db(chat_id, msg_id, status):
	sql = '''UPDATE referendums
				SET status = ?
				WHERE chat_id = ? and
						msg_id = ?'''
	row = [(status, chat_id, msg_id)]

	exec_sql(sql, row)

def set_vote_db(chat_id, msg_id, user_id, user_name, button_id):
	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	action = ''
	button_old = 0	
	datum = datetime.datetime.now()
	referendum = get_votes_db(chat_id, msg_id)
	
	for btn_id in referendum:
		for usr in referendum[btn_id]['roster'] + referendum[btn_id]['bench']:
			if(usr['user_id'] == user_id):
				sql = '''INSERT INTO rfr_log
							(chat_id, msg_id, button_id, user_id, user_name, datum, button_status) 
							VALUES(?, ?, ?, ?, ?, ?, ?)'''
				row = [(chat_id, msg_id, btn_id, user_id, user_name, datum, 0)]
				exec_sql(sql, row)

				button_old = btn_id
				action = 'unvoted'

	if(button_old != button_id):
		sql = '''INSERT INTO rfr_log
					(chat_id, msg_id, button_id, user_id, user_name, datum, button_status) 
					VALUES(?, ?, ?, ?, ?, ?, ?)'''
		row = [(chat_id, msg_id, button_id, user_id, user_name, datum, 1)]
		exec_sql(sql, row)
		
		if action:
			action = 'revoted'
		else:
			action = 'voted'

	return action
	

def get_votes_db(chat_id, msg_id):
	referendum = []

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''SELECT rfr_buttons.button_id, user_id, user_name, MAX(datum) as datum, button_status
				FROM rfr_buttons 
				LEFT OUTER JOIN rfr_log
				ON rfr_buttons.chat_id = rfr_log.chat_id and
					rfr_buttons.msg_id = rfr_log.msg_id and
					rfr_buttons.button_id = rfr_log.button_id
				WHERE rfr_buttons.chat_id = {} and
						rfr_buttons.msg_id = {}
				GROUP BY rfr_buttons.button_id, user_id, user_name
				ORDER BY rfr_buttons.button_id, datum
			'''.format(chat_id, msg_id)
	rows = cur.execute(sql).fetchall()
	con.close()


	for row in rows:
		if(row['button_status']):
			referendum.append({'button_id': row['button_id'], 'user_id': row['user_id'], 'user_name': row['user_name'], 'datum': row['datum']})
	
	referendum = sorted(referendum, key = lambda x: x['datum'])

	referendum_params = get_referendum_db(chat_id, msg_id)
	buttons = get_buttons_db(chat_id, msg_id)
	referendum = get_roster_bench(referendum, buttons, referendum_params['max_num'])

	return referendum

def get_buttons_db(chat_id, msg_id):
	buttons = {}
	
	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''SELECT button_id, button_factor, button_text
				FROM rfr_buttons
				WHERE chat_id = {} and
						msg_id = {}
			'''.format(chat_id, msg_id)		
	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:		
		buttons[row['button_id']] = {'button_factor': row['button_factor'], 'button_text': row['button_text']}
	
	return buttons

def drop_tables():
	con = db_connect()
	cur = con.cursor()

	cur.execute('DROP TABLE IF EXISTS referendums')
	cur.execute('DROP TABLE IF EXISTS rfr_buttons')
	cur.execute('DROP TABLE IF EXISTS rfr_log')
	cur.execute('DROP TABLE IF EXISTS regular_players')
	
	con.commit()
	con.close()

def extend_table():
	con = db_connect()
	cur = con.cursor()

	cur.execute('DROP TABLE IF EXISTS _referendums_old')
	cur.execute('ALTER TABLE referendums RENAME TO _referendums_old')
	cur.execute('''CREATE TABLE referendums(
						chat_id integer, 
						msg_id integer, 
						status integer,
						title text,
						max_num integer,
						game_cost integer DEFAULT 0,
						user_id integer,
						user_name text,
						datum text,
						PRIMARY KEY(chat_id, msg_id))''')

	cur.execute('''INSERT INTO referendums (chat_id, msg_id, status, title, max_num, user_id, user_name, datum)
					SELECT chat_id, msg_id, status, title, max_num, user_id, user_name, datum
						FROM _referendums_old''')
	cur.execute('DROP TABLE _referendums_old')

	con.commit()
	con.close()

# def drop_table_column():
# 	con = db_connect()
# 	cur = con.cursor()

# 	cur.execute('DROP TABLE IF EXISTS _referendums_old')
# 	cur.execute('ALTER TABLE referendums RENAME TO _referendums_old')
# 	cur.execute('''CREATE TABLE referendums(
# 						chat_id integer, 
# 						msg_id integer, 
# 						status integer,
# 						title text,
# 						max_num integer,
# 						game_cost integer
# 						user_id integer,
# 						user_name text,
# 						datum text,
# 						PRIMARY KEY(chat_id, msg_id))''')

# 	cur.execute('''INSERT INTO referendums (chat_id, msg_id, status, title, max_num, game_cost, user_id, user_name, datum)
# 						SELECT chat_id, msg_id, status, title, max_num, game_cost, user_id, user_name, datum
# 						FROM _referendums_old''')
# 	cur.execute('DROP TABLE _referendums_old')

# 	con.commit()
# 	con.close()

def select_all(tab):
	con = db_connect()
	cur = con.cursor()
	
	rows = []
	for row in cur.execute(f'SELECT * FROM {tab}'):
		rows.append(row)
	con.close()

	return rows

def print_tabs(*args):
	if(args):
		for arg in args:
			print(arg)
			rows = select_all(arg)
			for row in rows:
				print(row)			
	else:
		print('referendums')
		rows = select_all('referendums')
		for row in rows:
			print(row)
		
		print('rfr_buttons')
		rows = select_all('rfr_buttons')
		for row in rows:
			print(row)

		print('rfr_log')
		rows = select_all('rfr_log')
		for row in rows:
			print(row)

		print('regular_players')
		rows = select_all('regular_players')
		for row in rows:
			print(row)	

def is_free_slots(roster_bench, buttons, button_factor, max_num):
	busy_slots = 0

	for button in buttons:
		if buttons[button]['button_factor']:
			busy_slots += len(roster_bench[button]['roster']) * buttons[button]['button_factor']

	if busy_slots + button_factor <= max_num:	
		return True
	else:
		return False

def get_roster_bench(referendum, buttons, max_num):
	roster_bench = {}

	buttons_with_factor = []
	
	for button in buttons:
		roster_bench[button] = {'roster': [], 'bench': []}		
		
	for r in referendum:
		button_id = r['button_id']
		
		if buttons[button_id]['button_factor']:		
			if is_free_slots(roster_bench, buttons, buttons[button_id]['button_factor'], max_num):
				roster_bench[r['button_id']]['roster'].append(r)
			else:
				roster_bench[r['button_id']]['bench'].append(r)
		else:
			roster_bench[r['button_id']]['roster'].append(r)

	return roster_bench

def check_user_id(chat_id, msg_id, user_id):
	referendum_params = get_referendum_db(chat_id, msg_id)

	if user_id == referendum_params['user_id']:
		return True
	else:
		return False

def check_msg_id(chat_id, msg_id):	
	referendum_params = get_referendum_db(chat_id, msg_id)

	if referendum_params:
		return True
	else:
		return False

def get_regular_players_db(chat_id):
	players = []
	
	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''SELECT *
				FROM regular_players
				WHERE chat_id = {}'''.format(chat_id)
	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:
		players.append({'chat_id': row['chat_id'], 'user_id': row['user_id'], 'user_name': row['user_name'], 'player_type': row['player_type']})
	
	return players

def get_regular_player_db(chat_id, user_id):
	player = {}

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''SELECT * FROM regular_players
				WHERE chat_id = {} and
					user_id = {}
			'''.format(chat_id, user_id)

	row = cur.execute(sql).fetchone()

	if row:
		player['chat_id'] = row['chat_id']
		player['user_id'] = row['user_id']
		player['user_name'] = row['user_name']
		player['player_type'] = row['player_type']

	return player

def set_regular_player_db(chat_id, user_id, user_name, player_type):
	sql = '''INSERT OR REPLACE
				INTO regular_players
				(chat_id, user_id, user_name, player_type)
				VALUES(?, ?, ?, ?)'''
	row = [(chat_id, user_id, user_name, player_type)]

	exec_sql(sql, row)

def is_regular_player(chat_id, user_id):
	player = get_regular_player_db(chat_id, user_id)

	if player:
		return player['player_type']
	else:
		return 0
