#!venv/bin/python3
import logging
import datetime
import math
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified
from aiogram.utils.markdown import escape_md
from contextlib import suppress
from config import TOKEN

FILE_LOG = "referendums.log"
FILE_DB = 'mydatabase.db'
TAB_REFERENDUMS = 'referendums'
TAB_BUTTONS = 'buttons'
TAB_LOG = 'log'

def db_connect():
	try:
		con = sqlite3.connect(FILE_DB)
		return con
	except sqlite3.Error as e:
		logging.critical(e)

def drop_tables():
	con = db_connect()
	cur = con.cursor()
	cur.execute('DROP TABLE IF EXISTS referendums')
	cur.execute('DROP TABLE IF EXISTS buttons')
	cur.execute('DROP TABLE IF EXISTS log')
	con.commit()
	con.close()

def create_tables():	
	con = db_connect()
	cur = con.cursor()

	cur.execute('''CREATE TABLE IF NOT EXISTS referendums(
						chat_id integer, 
						msg_id integer, 
						title text,
						max_num integer, 
						user_id integer,
						user_name text,
						datum text,
						PRIMARY KEY(chat_id, msg_id))''')

	cur.execute('''CREATE TABLE IF NOT EXISTS buttons(
						chat_id integer, 
						msg_id integer,
						button integer,
						btn_text text,
						PRIMARY KEY(chat_id, msg_id, button))''')

	cur.execute('''CREATE TABLE IF NOT EXISTS log(
						chat_id integer, 
						msg_id integer, 
						button integer, 
						user_id integer,
						user_name text, 
						datum text,
						btn_status integer, 
						PRIMARY KEY(chat_id, msg_id, button, user_id, user_name, datum))''')
	con.commit()
	con.close()

def select_all(tab):
	con = db_connect()
	cur = con.cursor()
	
	rows = []
	for row in cur.execute(f'SELECT * FROM {tab}'):
		rows.append(row)
	con.close()
	return rows

def print_tabs():
	print(TAB_REFERENDUMS)
	rows = select_all(TAB_REFERENDUMS)
	for row in rows:
		print(row)
	
	print(TAB_BUTTONS)
	rows = select_all(TAB_BUTTONS)
	for row in rows:
		print(row)

	print(TAB_LOG)
	rows = select_all(TAB_LOG)
	for row in rows:
		print(row)

def exec_sql(sql, vals):
	con = db_connect()	
	cur = con.cursor()

	try:
		rows = cur.executemany(sql, vals).fetchall()		
		con.commit()
		con.close()
	except sqlite3.Error as e:
		logging.warning(e)

	return rows

def create_referendum_db(chat_id, msg_id, user_id, user_name, args):
	args = args.split("|")
	row = [(chat_id, msg_id, args[1], args[0], user_id, user_name, datetime.datetime.now())]

	sql = f'''INSERT INTO {TAB_REFERENDUMS}
				(chat_id, msg_id, title, max_num, user_id, user_name, datum) 
				VALUES(?, ?, ?, ?, ?, ?, ?)'''
	exec_sql(sql, row)

	
	args = args[1:]
	rows = []
	for bttn in range(1, len(args)):
		rows.append((chat_id, msg_id, bttn, args[bttn]))

	sql = f'''INSERT INTO {TAB_BUTTONS}
				(chat_id, msg_id, button, btn_text)
				VALUES(?, ?, ?, ?)'''

	exec_sql(sql, rows)

def get_referendum_db(chat_id, msg_id):
	referendum_params = {}

	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = f'''SELECT * FROM {TAB_REFERENDUMS}
				WHERE {TAB_REFERENDUMS}.chat_id = {chat_id} and
						{TAB_REFERENDUMS}.msg_id = {msg_id}'''
	
	row = cur.execute(sql).fetchone()
	referendum_params['title'] = row['title']
	referendum_params['max_num'] = row['max_num']
	
	return referendum_params

def set_vote_db(chat_id, msg_id, user_id, user_name, button):
	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = f'''SELECT MAX(datum), btn_status FROM {TAB_LOG}
				WHERE {TAB_LOG}.chat_id = {chat_id} and
						{TAB_LOG}.msg_id = {msg_id} and
						{TAB_LOG}.button = {button} and
						{TAB_LOG}.user_id = {user_id}'''
	
	btn_status = cur.execute(sql).fetchone()['btn_status']
	if(btn_status):
		btn_status = 0
	else:
		btn_status = 1

	row = [(chat_id, msg_id, button, user_id, user_name, datetime.datetime.now(), btn_status)]

	sql = f'''INSERT INTO {TAB_LOG}
				(chat_id, msg_id, button, user_id, user_name, datum, btn_status) 
				VALUES(?, ?, ?, ?, ?, ?, ?)'''
	exec_sql(sql, row)

def get_buttons_db(chat_id, msg_id):
	buttons = {}
	
	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = f'''SELECT button, btn_text
				FROM {TAB_BUTTONS}
				WHERE chat_id = {chat_id} and
						msg_id = {msg_id}'''
		
	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:		
		buttons[row['button']] = row['btn_text']
	
	return buttons

def get_votes_db(chat_id, msg_id):
	con = db_connect()
	con.row_factory = sqlite3.Row
	cur = con.cursor()

	sql = f'''SELECT {TAB_BUTTONS}.button, user_name, MAX(datum), btn_status
				FROM {TAB_BUTTONS} LEFT OUTER JOIN {TAB_LOG}
				ON {TAB_BUTTONS}.chat_id = {TAB_LOG}.chat_id  and
					{TAB_BUTTONS}.msg_id = {TAB_LOG}.msg_id  and
					{TAB_BUTTONS}.button = {TAB_LOG}.button
				WHERE {TAB_BUTTONS}.chat_id = {chat_id} and
						{TAB_BUTTONS}.msg_id = {msg_id}
				GROUP BY {TAB_BUTTONS}.button, user_name
				ORDER BY {TAB_BUTTONS}.button, datum'''

	referendum = {}
		
	rows = cur.execute(sql).fetchall()
	con.close()

	for row in rows:
		referendum[row['button']] = []
	for row in rows:
		if(row['btn_status']):
			referendum[row['button']].append({'user_id': row['user_id'], 'user_name': row['user_name']})
	
	return referendum

class MyBot:
	def __init__(self):
		logging.basicConfig(level = logging.INFO, 
							format = "[%(asctime)s] [%(levelname)-8s] [%(funcName)s]: %(message)s",
							handlers = [logging.FileHandler(FILE_LOG), logging.StreamHandler()])

		# drop_tables()
		create_tables()

		self.bot = Bot(token = TOKEN)
		self.dp = Dispatcher(self.bot)
		self.dp.register_message_handler(self.cmd_create, commands = "create")
		self.callback_numbers = CallbackData("prefix", "button")
		self.dp.register_callback_query_handler(self.process_callback, self.callback_numbers.filter())
		
		executor.start_polling(self.dp, skip_updates=True)

	async def cmd_create(self, message: types.Message):
		create_referendum_db(chat_id=message.chat.id, 
								msg_id=message.message_id, 
								user_id=message.from_user.id, 
								user_name=message.from_user.first_name, 
								args=message.get_args())	

		logging.info(f"chatID={message.chat.id}, msgID={message.message_id}, vote created by {message.from_user.first_name}")

		msg = self.update_message(message.chat.id, message.message_id, 0, '')
		keyboard = self.get_keyboard(message.chat.id, message.message_id)
		
		await message.answer(msg, reply_markup = keyboard, parse_mode="MarkdownV2")

	async def process_callback(self, cbq: types.CallbackQuery, callback_data: dict):
		set_vote_db(chat_id=cbq.message.chat.id,
					msg_id=cbq.message.message_id,
					user_id=cbq.from_user.id,
					user_name=cbq.from_user.first_name,
					button=int(callback_data['button']))
		logging.info(f"chatID={cbq.message.chat.id}, msgID={cbq.message.message_id}, user {cbq.message.from_user.first_name} voted for {int(callback_data['button'])}")
		msg = self.update_message(message.chat.id, message.message_id, int(callback_data['button']), cbq.from_user)
		keyboard = self.get_keyboard(message.chat.id, message.message_id)
		
		with suppress(MessageNotModified):
			await cbq.message.edit_text(msg, reply_markup = keyboard, parse_mode="MarkdownV2")
		await cbq.answer()
	
	def get_keyboard(self, chat_id, msg_id):
		buttons_db = get_buttons_db(chat_id, msg_id)
		referendum_db = get_votes_db(chat_id, msg_id)
		keyboard_btns = []

		for button in buttons_db:
			button_text = buttons_db[button]
			if len(referendum_db[button]):
				button_text += f" - {len(referendum_db[button])}"
			keyboard_btns.append(types.InlineKeyboardButton(text = button_text, callback_data = self.callback_numbers.new(button = button)))

		keyboard = types.InlineKeyboardMarkup(row_width = 1)
		keyboard.add(*keyboard_btns)

		return keyboard
	
	def update_message(self, chat_id, msg_id, user):
		flag = True
		votes = 0
		votes_total = 0
		votes_percent = 0
		votes_percent_by_chat = 0

		referendum_params = get_referendum_db(chat_id, msg_id)
		buttons_db = get_buttons_db(chat_id, msg_id)
		referendum_db = get_votes_db(chat_id, msg_id)

		msg = f"*{escape_md(referendum_params['title'])}*\n\n"

		for button in buttons_db:
			votes_total += len(referendum_db[button])
		
		for button in buttons_db:		
			votes = len(referendum_db[button])
			if(votes_total):
				votes_percent = int(100 * round(votes/votes_total, 2))
			
			msg += f"{escape_md(buttons_db[button])} \\- {len(referendum_db[button])} \\({votes_percent}%\\)\n"
					
			userlist = []
			current_user = 0
			for usr in referendum_db[button]:
				if(button == 1):
					if(current_user == 0):
						mark1 = '\\['
						if(len(referendum_db[button]) == 1):
							mark2 = '\\]'
						else:
							mark2 = ''
					elif(current_user <= referendum_params['max_num'] - 1):
						mark1 = ''
						mark2 = '\\]'
					else:
						mark1 = ''
						mark2 = ''
				else:
					mark1 = ''
					mark2 = ''

				userlist.append(f"{mark1}[{escape_md(usr['user_name'])}](tg://user?id={usr['user_id']}){mark2}")
				current_user += 1
			
			if(userlist):
				msg += ", ".join(userlist) + '\n\n'
			else:
				msg += '\n'			
		
		chat_members = await message.chat.get_member_count()
		if(chat_members - 1):
			votes_percent_by_chat = int(100 * round(votes_total/(chat_members-1), 2))
		msg += f"👥 {votes_total} of {chat_members - 1} \\({votes_percent_by_chat}%\\) people voted so far\\."

		return msg

if __name__ == "__main__":
	kaa = MyBot()