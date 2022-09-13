import sqlite3
import datetime
import logging
import config

def db_connect():
	try:
		con = sqlite3.connect(config.FILE_DB)
		return con
	except sqlite3.Error as e:
		logging.critical(e)

def create_tables():
	con = db_connect()
	cur = con.cursor()

	cur.execute('''
		CREATE table if not exists referendums(
			chat_id integer,
			msg_id integer,
			title text,
			rfr_type integer,
			status integer,
			game_cost integer,
			max_players integer,
			user_id integer,
			user_name text,
			datum text,
			primary key(chat_id, msg_id))
	''')

	cur.execute('''
		CREATE table if not exists rfr_buttons(
			chat_id integer,
			msg_id integer,
			button_id integer,
			button_text text,
			primary key(chat_id, msg_id, button_id))
	''')

	cur.execute('''
		CREATE table if not exists rfr_log(
			chat_id integer,
			msg_id integer,
			button_id integer,
			user_id integer,
			user_name text,
			datum text,
			button_status integer,
			primary key(chat_id, msg_id, button_id, user_id, user_name, datum))
	''')

	cur.execute('''
		CREATE table if not exists regular_players(
			chat_id integer,
			user_id integer,
			user_name text,
			player_type integer,
			primary key(chat_id, user_id))
	''')

	cur.execute('''
		CREATE table if not exists timers(
			chat_id integer,
			msg_id integer,
			datum text,
			period integer,
			status integer,
			primary key(chat_id, msg_id))
	''')

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

def create_referendum_db(chat_id, msg_id, user_id, user_name, rfr_type, args):
	game_cost = args[0]
	max_players = args[1]
	title = args[2]
	buttons = args[3:]

	sql = '''
		INSERT into referendums(chat_id, msg_id, title, rfr_type, status, game_cost, max_players, user_id, user_name, datum)
			values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	'''
	row = [(chat_id, msg_id, title, rfr_type, 1, game_cost, max_players, user_id, user_name, datetime.datetime.now())]
	exec_sql(sql, row)

	sql = '''
		INSERT into rfr_buttons(chat_id, msg_id, button_id, button_text)
			values(?, ?, ?, ?)
	'''
	rows = []
	for button_id in range(1, len(buttons) + 1):
		rows.append((chat_id, msg_id, button_id, buttons[button_id - 1]))
	exec_sql(sql, rows)

def get_referendums_by_user_id_db(chat_id, user_id, status = -1):
	referendums = []

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	if status == -1:
		sql = '''
			SELECT *
				from referendums
				where
					referendums.chat_id = {} and
					referendums.user_id = {}
		'''.format(chat_id, user_id)
	else:
		sql = '''
			SELECT *
				from referendums
				where
					referendums.chat_id = {} and
					referendums.status = {} and
					referendums.user_id = {}
		'''.format(chat_id, status, user_id)

	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:
		referendum = {}

		referendum['msg_id'] = row['msg_id']
		referendum['title'] = row['title']
		referendum['rfr_type'] = row['rfr_type']
		referendum['status'] = row['status']
		referendum['game_cost'] = row['game_cost']
		referendum['max_players'] = row['max_players']
		referendum['user_id'] = row['user_id']
		referendum['user_name'] = row['user_name']
		referendum['datum'] = row['datum']

		referendums.append(referendum)

	return referendums

def get_referendum_db(chat_id, msg_id):
	referendum = {}

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''
		SELECT *
			from referendums
			where
				referendums.chat_id = {} and
				referendums.msg_id = {}
	'''.format(chat_id, msg_id)

	row = cur.execute(sql).fetchone()
	con.close()

	if row:
		referendum['title'] = row['title']
		referendum['rfr_type'] = row['rfr_type']
		referendum['status'] = row['status']
		referendum['game_cost'] = row['game_cost']
		referendum['max_players'] = row['max_players']
		referendum['user_id'] = row['user_id']

	return referendum

def update_referendum_db(chat_id, args):
	msg_id = int(args[0])

	if len(args) >= 2:
		game_cost = int(args[1])

		sql = '''
			UPDATE referendums
				set game_cost = ?
				where
					chat_id = ? and
					msg_id = ?
		'''
		row = [(game_cost, chat_id, msg_id)]
		exec_sql(sql, row)

	if len(args) >= 3:
		max_players = int(args[2])

		sql = '''
			UPDATE referendums
				set max_players = ?
				where
					chat_id = ? and
					msg_id = ?
		'''
		row = [(max_players, chat_id, msg_id)]
		exec_sql(sql, row)

	if len(args) >= 4:
		title = args[3]

		sql = '''
			UPDATE referendums
				set title = ?
				where
					chat_id = ? and
					msg_id = ?
		'''
		row = [(title, chat_id, msg_id)]
		exec_sql(sql, row)

	if len(args) >= 5:
		buttons = args[4:]
		button_id = 1

		for button in buttons:
			sql = '''
				UPDATE rfr_buttons
					set button_text = ?
					where
						chat_id = ? and
						msg_id = ? and
						button_id = ?
			'''
			row = [(button, chat_id, msg_id, button_id)]
			exec_sql(sql, row)

			button_id += 1

def set_referendum_status_db(chat_id, msg_id, status):
	sql = '''
		UPDATE referendums
			SET status = ?
			WHERE
				chat_id = ? and
				msg_id = ?
	'''
	row = [(status, chat_id, msg_id)]
	exec_sql(sql, row)

def get_last_button_add(chat_id, msg_id, user_id, button_id):
	last_button_add = {}

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''
		SELECT user_id, user_name, button_status, max(datum) as datum
			from rfr_log
			where
				chat_id = {} and
				msg_id = {} and
				button_id = {} and
				user_id = {} and
				button_status = 1
			group by user_id, user_name

	'''.format(chat_id, msg_id, config.BUTTON_ID_ADD, user_id)

	row = cur.execute(sql).fetchone()
	con.close()

	if row:
		last_button_add['user_id'] = row['user_id']
		last_button_add['user_name'] = row['user_name']
		last_button_add['button_status'] = row['button_status']
		last_button_add['datum'] = row['datum']

	return last_button_add

def set_vote_db(chat_id, msg_id, user_id, user_name, button_id):
	action = ''
	button_old = 0
	datum = datetime.datetime.now()
	referendum = get_referendum_db(chat_id, msg_id)
	votes = get_votes_db(chat_id, msg_id)

	if referendum['rfr_type'] in (config.RFR_GAME, config.RFR_GAME2):
		if button_id == config.BUTTON_ID_ADD:
			sql = '''
				INSERT into rfr_log(chat_id, msg_id, button_id, user_id, user_name, datum, button_status)
					values(?, ?, ?, ?, ?, ?, ?)
			'''
			row = [(chat_id, msg_id, button_id, user_id, user_name, datum, 1)]
			exec_sql(sql, row)

			action = 'added friend'
		elif button_id == config.BUTTON_ID_DEL:
			friends = get_friends_db(chat_id, msg_id)

			if user_id in friends:
				sql = '''
					INSERT into rfr_log(chat_id, msg_id, button_id, user_id, user_name, datum, button_status)
						values(?, ?, ?, ?, ?, ?, ?)
				'''
				row = [(chat_id, msg_id, button_id, user_id, user_name, datum, 0)]
				exec_sql(sql, row)

				last_button_add = get_last_button_add(chat_id, msg_id, user_id, config.BUTTON_ID_ADD)
				if last_button_add:
					sql = '''
						UPDATE rfr_log
							SET button_status = ?
							WHERE
								chat_id = ? and
								msg_id = ? and
								button_id = ? and
								user_id = ? and
								user_name = ? and
								datum = ?
					'''
					row = [(0, chat_id, msg_id, config.BUTTON_ID_ADD, user_id, user_name, last_button_add['datum'])]
					exec_sql(sql, row)

				action = 'removed friend'
			else:
				action = 'tried to remove 0 friends'
		elif button_id == config.BUTTON_ID_OPT:
			sql = '''
				INSERT into rfr_log(chat_id, msg_id, button_id, user_id, user_name, datum, button_status)
					values(?, ?, ?, ?, ?, ?, ?)
			'''

			for usr in votes[button_id]['players']:
				if usr['user_id'] == user_id:
					row = [(chat_id, msg_id, button_id, user_id, user_name, datum, 0)]
					action = 'unvoted'
				else:
					action = ''
			if action == '':
				row = [(chat_id, msg_id, button_id, user_id, user_name, datum, 1)]
				action = 'voted'

			exec_sql(sql, row)

		else:
			for btn_id in (config.BUTTON_ID_YES, 2, 3):
				for usr in votes[btn_id]['players'] + votes[btn_id]['queue']:
					if usr['user_id'] == user_id:
						sql = '''
							INSERT into rfr_log(chat_id, msg_id, button_id, user_id, user_name, datum, button_status)
								values(?, ?, ?, ?, ?, ?, ?)
						'''
						row = [(chat_id, msg_id, btn_id, user_id, user_name, datum, 0)]
						exec_sql(sql, row)

						button_old = btn_id
						action = 'unvoted'

			if button_old != button_id:
				sql = '''
					INSERT into rfr_log(chat_id, msg_id, button_id, user_id, user_name, datum, button_status)
						values(?, ?, ?, ?, ?, ?, ?)
				'''
				row = [(chat_id, msg_id, button_id, user_id, user_name, datum, 1)]
				exec_sql(sql, row)

				if action:
					action = 'revoted'
				else:
					action = 'voted'
	elif referendum['rfr_type'] == config.RFR_SINGLE:
		for btn_id in votes:
			for usr in votes[btn_id]['players'] + votes[btn_id]['queue']:
				if usr['user_id'] == user_id:
					sql = '''
						INSERT into rfr_log(chat_id, msg_id, button_id, user_id, user_name, datum, button_status)
							values(?, ?, ?, ?, ?, ?, ?)
					'''
					row = [(chat_id, msg_id, btn_id, user_id, user_name, datum, 0)]
					exec_sql(sql, row)

					button_old = btn_id
					action = 'unvoted'

		if button_old != button_id:
			sql = '''
				INSERT into rfr_log(chat_id, msg_id, button_id, user_id, user_name, datum, button_status)
					values(?, ?, ?, ?, ?, ?, ?)
			'''
			row = [(chat_id, msg_id, button_id, user_id, user_name, datum, 1)]
			exec_sql(sql, row)

			if action:
				action = 'revoted'
			else:
				action = 'voted'
	elif referendum['rfr_type'] == config.RFR_MULTI:
		for btn_id in votes:
			for usr in votes[btn_id]['players'] + votes[btn_id]['queue']:
				if usr['user_id'] == user_id and btn_id == button_id:
					sql = '''
						INSERT into rfr_log(chat_id, msg_id, button_id, user_id, user_name, datum, button_status)
							values(?, ?, ?, ?, ?, ?, ?)
					'''
					row = [(chat_id, msg_id, btn_id, user_id, user_name, datum, 0)]
					exec_sql(sql, row)

					button_old = btn_id
					action = 'unvoted'

		if action == '':
			sql = '''
				INSERT into rfr_log(chat_id, msg_id, button_id, user_id, user_name, datum, button_status)
					values(?, ?, ?, ?, ?, ?, ?)
			'''
			row = [(chat_id, msg_id, button_id, user_id, user_name, datum, 1)]
			exec_sql(sql, row)

			action = 'voted'

	return action

def get_votes_db(chat_id, msg_id):
	referendum_log = []

	referendum = get_referendum_db(chat_id, msg_id)
	buttons = get_buttons_db(chat_id, msg_id)

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''
		SELECT rfr_buttons.button_id, user_id, user_name, max(datum) as datum, button_status
			from rfr_buttons
			left outer join rfr_log
			on
				rfr_buttons.chat_id = rfr_log.chat_id and
				rfr_buttons.msg_id = rfr_log.msg_id and
				rfr_buttons.button_id = rfr_log.button_id
			where
				rfr_buttons.chat_id = {} and
				rfr_buttons.msg_id = {}
			group by
				rfr_buttons.button_id, user_id, user_name
			order by
				rfr_buttons.button_id, datum
	'''.format(chat_id, msg_id)
	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:
		if(row['button_status']):
			referendum_log.append({'button_id': row['button_id'], 'user_id': row['user_id'], 'user_name': row['user_name'], 'datum': row['datum']})

	referendum_log = sorted(referendum_log, key = lambda x: x['datum'])
	players_queue = get_players_queue(referendum_log, buttons, referendum['rfr_type'], referendum['max_players'])

	return players_queue

def get_buttons_db(chat_id, msg_id):
	buttons = {}

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''
		SELECT button_id, button_text
			from rfr_buttons
			where
				chat_id = {} and
				msg_id = {}
	'''.format(chat_id, msg_id)
	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:
		buttons[row['button_id']] = {'button_text': row['button_text']}

	return buttons

def drop_tables():
	con = db_connect()
	cur = con.cursor()

	cur.execute('drop table if exists referendums')
	cur.execute('drop table if exists rfr_buttons')
	cur.execute('drop table if exists rfr_log')
	cur.execute('drop table if exists regular_players')

	con.commit()
	con.close()

def extend_table():
	con = db_connect()
	cur = con.cursor()

	cur.execute('drop table if exists _referendums_old')
	cur.execute('ALTER table referendums rename to _referendums_old')
	cur.execute('''
		CREATE table referendums(
			chat_id integer,
			msg_id integer,
			title text,
			rfr_type integer default 0,
			status integer,
			game_cost integer default 0,
			max_players integer,
			user_id integer,
			user_name text,
			datum text,
			primary key(chat_id, msg_id))''')

	cur.execute('''
		INSERT into referendums(
					chat_id, msg_id, title, status, game_cost, max_players, user_id, user_name, datum)
			select chat_id, msg_id, title, status, game_cost, max_players, user_id, user_name, datum
			from _referendums_old
	''')
	cur.execute('drop table _referendums_old')

	con.commit()
	con.close()

def drop_table_column():
	con = db_connect()
	cur = con.cursor()

	cur.execute('drop table if exists _rfr_buttons_old')
	cur.execute('ALTER table rfr_buttons rename to _rfr_buttons_old')
	cur.execute('''
		CREATE table rfr_buttons(
			chat_id integer,
			msg_id integer,
			button_id integer,
			button_text text,
			primary key(chat_id, msg_id, button_id))
	''')

	cur.execute('''
		INSERT into rfr_buttons(
					chat_id, msg_id, button_id, button_text)
			select chat_id, msg_id, button_id, button_text
			from _rfr_buttons_old''')
	cur.execute('drop table _rfr_buttons_old')

	con.commit()
	con.close()

def select_all(tab):
	con = db_connect()
	cur = con.cursor()

	rows = []
	for row in cur.execute(f'select * from {tab}'):
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

def is_free_slots(players_queue, buttons, max_num):
	busy_slots = 0

	for button in buttons:
		if button == 1:
			busy_slots += len(players_queue[button]['players'])

	if busy_slots + 1 <= max_num:
		return True
	else:
		return False

def get_players_queue(referendum_log, buttons, rfr_type, max_num):
	players_queue = {}

	for button in buttons:
		players_queue[button] = {'players': [], 'queue': []}

	for r in referendum_log:
		button_id = r['button_id']

		if rfr_type in (config.RFR_GAME, config.RFR_GAME2) and button_id == 1 and max_num > 0:
			if is_free_slots(players_queue, buttons, max_num):
				players_queue[r['button_id']]['players'].append(r)
			else:
				players_queue[r['button_id']]['queue'].append(r)
		elif rfr_type in (config.RFR_GAME, config.RFR_GAME2) and button_id in (4, 5):
			pass
		else:
			players_queue[r['button_id']]['players'].append(r)

	return players_queue

def check_user_id(chat_id, msg_id, user_id):
	referendum = get_referendum_db(chat_id, msg_id)

	if user_id == referendum['user_id']:
		return True
	else:
		return False

def check_msg_id(chat_id, msg_id):
	referendum = get_referendum_db(chat_id, msg_id)

	if referendum:
		return True
	else:
		return False

def get_regular_players_db(chat_id , player_type = -1):
	players = []

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	if player_type == -1:
		sql = '''
			SELECT *
				from regular_players
				where chat_id = {}
		'''.format(chat_id)
	else:
		sql = '''
			SELECT *
				from regular_players
				where chat_id = {} and
					player_type = {}
		'''.format(chat_id, player_type)

	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:
		players.append({'chat_id': row['chat_id'], 'user_id': row['user_id'], 'user_name': row['user_name'], 'player_type': row['player_type']})

	return players

def is_regular_players_used_db(chat_id):
	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''
		SELECT *
			from regular_players
			where
				chat_id = {} and
				player_type = 1
	'''.format(chat_id)

	row = cur.execute(sql).fetchone()

	if row:
		return True
	else:
		return False

def get_regular_player_db(chat_id, user_id):
	player = {}

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''
		SELECT *
			from regular_players
			where
				chat_id = {} and
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
	sql = '''
		INSERT or replace
			into regular_players(chat_id, user_id, user_name, player_type)
			values(?, ?, ?, ?)
	'''
	row = [(chat_id, user_id, user_name, player_type)]

	exec_sql(sql, row)

def is_regular_player(chat_id, user_id):
	player = get_regular_player_db(chat_id, user_id)

	if player:
		return player['player_type']
	else:
		return 0

def get_friends_db(chat_id, msg_id):
	friends = {}

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''
		SELECT user_id, user_name, sum(button_status) as friends, min(datum) as datum
			from rfr_log
			where
				chat_id = {} and
				msg_id = {} and
				button_id = 4 and
				button_status = 1
			group by user_id, user_name
			order by datum
	'''.format(chat_id, msg_id)
	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:
		if row['friends'] > 0:
			friends[row['user_id']] = {'user_name': row['user_name'], 'friends': row['friends'], 'datum': row['datum']}

	return friends

def add_button(chat_id, msg_id, button_text):
	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''
		SELECT max(button_id) as button_id
			from rfr_buttons
			where
				chat_id = {} and
				msg_id = {}
	'''.format(chat_id, msg_id)

	row = cur.execute(sql).fetchone()
	con.close()

	if row:
		button_id = row['button_id'] + 1

		sql = '''
			INSERT into rfr_buttons(chat_id, msg_id, button_id, button_text)
				values(?, ?, ?, ?)
		'''
		row = [(chat_id, msg_id, button_id, button_text)]
		exec_sql(sql, row)

def get_silent_members_db(chat_id, msg_id):
	chat_members = []
	active_members = []
	silent_members = []

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = '''
		SELECT user_id, user_name
			from regular_players
			where chat_id = {}
	'''.format(chat_id)
	rows = cur.execute(sql).fetchall()
	for row in rows:
		chat_members.append({'user_id': row['user_id'], 'user_name': row['user_name']})

	sql = '''
		SELECT user_id, user_name
			from rfr_buttons
			where
				chat_id = {} and
				msg_id = {}
			group by
				user_id, user_name
	'''.format(chat_id, msg_id)
	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:
		active_members.append({'user_id': row['user_id'], 'user_name': row['user_name']})

	silent_members = [p for p in chat_members if p not in active_members]

	return silent_members
