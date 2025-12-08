#!venv/bin/python

import logging
import datetime as dt
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified
from aiogram.utils.markdown import escape_md
from contextlib import suppress
import pymorphy2
import referendum_db as db
import config
import bot_token

def get_morph(my_word):
	morph = pymorphy2.MorphAnalyzer()

	plur = morph.parse(my_word)[0].inflect({'plur'})
	if plur:
		return plur.word
	else:
		return my_word

def check_input(cmd, args, chat_id = 0, msg_id = 0, user_id = 0):
	if cmd == config.RFR_GAME_CMD:
		if len(args) != 9:
			return "usage: /game game_cost|max_players|last_games|title|button_1_text|...|button_5_text"

		if args[0].isnumeric() == False:
			return "game_cost должно быть числом"

		if args[1].isnumeric() == False:
			return "max_players должно быть числом"

		if args[2].isnumeric() == False:
			return "last_games должно быть числом"

	elif cmd == config.RFR_GAME2_CMD:
		if len(args) != 10:
			return "usage: /game2 game_cost|max_players|last_games|title|button_1_text|...|button_6_text"

		if args[0].isnumeric() == False:
			return "game_cost должно быть числом"

		if args[1].isnumeric() == False:
			return "max_players должно быть числом"

		if args[2].isnumeric() == False:
			return "last_games должно быть числом"

	elif cmd == 'update':
		if len(args) < 2:
			return "usage: /update msg_id|game_cost|max_players|last_games|title|button_1_text|...|button_N_text"

		if len(args) >= 1 and args[0].isnumeric() == False:
			return "msg_id должно быть числом"
		else:
			msg_id = int(args[0])
			if db.check_msg_id(chat_id, msg_id) == False:
				return f"msg_id = {msg_id} не существует в chat_id = {chat_id}"
			if db.check_user_id(chat_id, msg_id, user_id) == False:
				return "Чужой опрос!"
		if len(args) >= 2 and args[1].isnumeric() == False:
			return "game_cost должно быть числом"
		if len(args) >= 3 and args[2].isnumeric() == False:
			return "max_players должно быть числом"
		if len(args) >= 4 and args[3].isnumeric() == False:
			return "last_games должно быть числом"

	elif cmd in ('open', 'close', 'log'):
		if args and args.isnumeric() == False or args == '' and msg_id == 0 or args == '' and cmd == 'open':
			return "msg_id должно быть числом"

		if args:
			msg_id = int(args)

		if db.check_msg_id(chat_id, msg_id) == False:
			return f"msg_id = {msg_id} не существует в chat_id = {chat_id}"
		if db.check_user_id(chat_id, msg_id, user_id) == False:
			return "Чужой опрос!"

	elif cmd == 'statall':
		if len(args) == 1 and args[0].isnumeric() == True or len(args) == 2 and args[0].isnumeric() == True and args[1].isnumeric() == True:
			pass
		else:
			return "usage: /statall last_games|msg_id*"

	elif cmd == 'statuser':
		if len(args) < 2 or len(args) > 3:
			return "usage: /statuser user_id|last_games|msg_id*"

		for arg in args:
			if arg.isnumeric() == False:
				return "user_id, last_games, msg_id* должны быть числами"

	elif cmd in ('get', 'get_reg'):
		if args and args.isnumeric() == False:
			return "1 - открытый, 0 - закрытый, пусто - все"

	elif cmd == 'set_reg':
		if len(args) not in (2, 3):
			return "usage: /set_reg user_id|player_type"

		if args[0].isnumeric() == False or args[1].isnumeric() == False:
			return "user_id и player_type должно быть числом"

	elif cmd == 'del_reg':
		users_id = args

		if len(users_id) == 0:
			return "usage: /del_reg user_id_1|user_id_2|...|user_id_N"

		for uid in users_id:
			if uid.isnumeric() == False:
				return "user_id должно быть числом"

	elif cmd == 'vote':
		if len(args) != 3:
			return "usage: /vote msg_id|user_id|button_id"

		for arg in args:
			if arg.isnumeric() == False:
				return "msg_id, user_id, button_id должны быть числами"

	elif cmd == 'add_btn':
		if len(args) != 2:
			return "usage: /add_btn msg_id|button_text"

		if args[0].isnumeric():
			msg_id = int(args[0])
			if db.check_msg_id(chat_id, msg_id) == False:
				return f"msg_id = {msg_id} не существует в chat_id = {chat_id}"
			if db.check_user_id(chat_id, msg_id, user_id) == False:
				return "Чужой опрос!"
		else:
			return "msg_id должно быть числом"

	elif cmd == 'cron':
		if len(args) < 4:
			return f"usage: /cron yyyy-mm-dd hh-mm|vote type|<params>"

		try:
			dt_format = '%Y-%m-%d %H:%M'
			dt_timer = dt.datetime.strptime(args[0], dt_format)
		except Exception as e:
			return e

		if args[1] not in (config.RFR_GAME_CMD, config.RFR_SINGLE_CMD, config.RFR_MULTI_CMD, config.RFR_GAME2_CMD):
			return f"vote type = {{{config.RFR_GAME_CMD}, {config.RFR_SINGLE_CMD}, {config.RFR_MULTI_CMD}, {config.RFR_GAME2_CMD}}}"

	elif cmd == 'get_silent':
		if args:
			if args.isnumeric() == False:
				return "msg_id должно быть числом"

			msg_id = int(args)
			if db.check_msg_id(chat_id, msg_id) == False:
				return f"msg_id = {msg_id} не существует в chat_id = {chat_id}"
			if db.check_user_id(chat_id, msg_id, user_id) == False:
				return "Чужой опрос!"
		else:
			if msg_id == 0:
				return "usage: /get_silent msg_id"

	elif cmd == 'notify':
		if len(args) == 1 and msg_id == 0:
				return "usage: /notify msg_id*|text"
		elif len(args) > 1:
			if args[0].isnumeric() == False:
				return "msg_id должно быть числом"
			else:
				msg_id = int(args[0])
				if db.check_msg_id(chat_id, msg_id) == False:
					return f"msg_id = {msg_id} не существует в chat_id = {chat_id}"
				if db.check_user_id(chat_id, msg_id, user_id) == False:
					return "Чужой опрос!"

	elif cmd == 'notifyq':
		if len(args) == 1 and msg_id == 0:
				return "usage: /notifyq msg_id*|text"
		elif len(args) > 1:
			if args[0].isnumeric() == False:
				return "msg_id должно быть числом"
			else:
				msg_id = int(args[0])
				if db.check_msg_id(chat_id, msg_id) == False:
					return f"msg_id = {msg_id} не существует в chat_id = {chat_id}"
				if db.check_user_id(chat_id, msg_id, user_id) == False:
					return "Чужой опрос!"

	return ''

def get_username(user):
	if(user.last_name):
		return f"{user.first_name} {user.last_name}"
	elif(user.username):
		return user.username
	else:
		return user.first_name

def get_next_player(votes, buttons, friends, friends_needed):
	next_player = ''
	button_id = config.BUTTON_ID_YES
	exit = 0
	counter = friends_needed

	if len(buttons):
		if votes[button_id]['queue']:
			next_player = f"{votes[button_id]['queue'][0]['user_name']}"
		else:
			if friends_needed >= 0:
				for uid in friends:
					for f in range(friends[uid]['friends']):
						next_player = f"участник от {friends[uid]['user_name']}"
						if counter == 0:
							exit = 1
							break
						else:
							counter -= 1
					if exit:
						break

		return next_player

def is_one_referendum_active(chat_id, user_id):
	referendums = db.get_referendums_by_user_id_db(chat_id = chat_id, user_id = user_id, status = 1)

	if len(referendums) == 1:
		return referendums[0]['msg_id']
	else:
		return 0

def read_file(file_name, chat_id = 0, msg_id = 0):
	msg = ''

	fd = open(file_name, encoding = 'utf-8', mode = "r")

	if file_name == config.FILE_LOG:
		pattern1 = f"chat_id={chat_id}"
		pattern2 = f"msg_id={msg_id}"

		for file_line in fd:
			if pattern1 in file_line and pattern2 in file_line:
				msg += file_line
	else:
		for file_line in fd:
			msg += file_line

	fd.close()
	return msg

def sort_buttons(buttons, votes, rfr_type):
	buttons_sorted = []

	for button_id in buttons:
		button_votes = len(votes[button_id]['players']) + len(votes[button_id]['queue'])
		buttons_sorted.append({'button_id':button_id, 'votes': button_votes})
	if rfr_type in (config.RFR_SINGLE, config.RFR_MULTI):
		buttons_sorted = sorted(buttons_sorted, key = lambda x: x['votes'], reverse = True)

	return buttons_sorted

class MyBot:
	def __init__(self):
		logging.basicConfig(level = config.LEVEL,
							format = "[%(asctime)s] [%(levelname)-8s] [%(funcName)s]: %(message)s",
							handlers = [logging.FileHandler(config.FILE_LOG), logging.StreamHandler()])

		db.create_tables()

		self.bot = Bot(token = bot_token.TOKEN)
		self.dp = Dispatcher(self.bot)

		self.dp.register_message_handler(self.cmd_start, commands = "start")
		self.dp.register_message_handler(self.cmd_help, commands = "help")
		self.dp.register_message_handler(self.cmd_game, commands = "game")
		self.dp.register_message_handler(self.cmd_single, commands = "single")
		self.dp.register_message_handler(self.cmd_multi, commands = "multi")
		self.dp.register_message_handler(self.cmd_game2, commands = "game2")
		self.dp.register_message_handler(self.cmd_get, commands = "get")
		self.dp.register_message_handler(self.cmd_close, commands = "close")
		self.dp.register_message_handler(self.cmd_close_all, commands = "closeall")
		self.dp.register_message_handler(self.cmd_open, commands = "open")
		self.dp.register_message_handler(self.cmd_update, commands = "update")
		self.dp.register_message_handler(self.cmd_add_btn, commands = "add_btn")
		self.dp.register_message_handler(self.cmd_log, commands = "log")
		self.dp.register_message_handler(self.cmd_cron, commands = "cron")
		self.dp.register_message_handler(self.cmd_get_stat, commands = "statall")
		self.dp.register_message_handler(self.cmd_get_stat_user, commands = "statuser")
		self.dp.register_message_handler(self.cmd_get_stat_over, commands = "statover")
		self.dp.register_message_handler(self.cmd_get_regular_players, commands = "get_reg")
		self.dp.register_message_handler(self.cmd_set_regular_player, commands = "set_reg")
		self.dp.register_message_handler(self.cmd_del_regular_player, commands = "del_reg")
		self.dp.register_message_handler(self.cmd_ban, commands = "ban")
		self.dp.register_message_handler(self.cmd_unban, commands = "unban")
		self.dp.register_message_handler(self.cmd_get_silent, commands = "get_silent")
		self.dp.register_message_handler(self.cmd_notify, commands = "notify")
		self.dp.register_message_handler(self.cmd_notifyq, commands = "notifyq")
		self.dp.register_message_handler(self.cmd_extend_table, commands = "exttab")
		self.dp.register_message_handler(self.cmd_vote, commands = "vote")
		self.dp.register_message_handler(self.cmd_getu, commands = "getu")

		self.callback_numbers = CallbackData("prefix", "button")
		self.dp.register_callback_query_handler(self.process_callback, self.callback_numbers.filter())

		executor.start_polling(self.dp, skip_updates = True)

	async def cmd_start(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id

		await self.bot.send_message(user_id, f"Привет! Твой telegram ID = {user_id}")
		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_help(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id

		msg = read_file(config.FILE_HELP)

		await self.bot.send_message(user_id, msg)
		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_game(self, message: types.Message):
		await self.cmd_create(message, rfr_type = config.RFR_GAME)
	async def cmd_single(self, message: types.Message):
		await self.cmd_create(message, rfr_type = config.RFR_SINGLE)
	async def cmd_multi(self, message: types.Message):
		await self.cmd_create(message, rfr_type = config.RFR_MULTI)
	async def cmd_game2(self, message: types.Message):
		await self.cmd_create(message, rfr_type = config.RFR_GAME2)

	async def cmd_create(self, message: types.Message, rfr_type):
		chat_id = message.chat.id
		msg_id = message.message_id
		game_cost = 0
		max_players = 0
		last_games = 0
		args = message.get_args().split("|")

		if rfr_type == config.RFR_SINGLE or rfr_type == config.RFR_MULTI:
			args = [game_cost] + [max_players] + [last_games] + args

		if rfr_type == config.RFR_GAME:
			check_type = config.RFR_GAME_CMD
		elif rfr_type == config.RFR_GAME2:
			check_type = config.RFR_GAME2_CMD
		else:
			check_type = ''

		msg_err = check_input(check_type, args)

		if msg_err == '':
			db.create_referendum_db(chat_id = chat_id,
									msg_id = msg_id,
									user_id = message.from_user.id,
									user_name = get_username(message.from_user),
									rfr_type = rfr_type,
									args = args)

			referendum = db.get_referendum_db(chat_id, msg_id)
			last_games = referendum['last_games']

			msg = await self.update_message(message.chat, msg_id)
			keyboard = self.get_keyboard(chat_id, msg_id)
			await message.answer(msg, reply_markup = keyboard, parse_mode = "MarkdownV2")

			try:
				await self.bot.pin_chat_message(chat_id, msg_id + 1)
				await self.bot.delete_message(chat_id, msg_id + 2)
			except:
				msg_err = f"chat_id={chat_id}({message.chat.title}), msg_id={msg_id}, недостаточно прав для управления закреплёнными сообщениями"
				await self.bot.send_message(message.from_user.id, msg_err)
				logging.error(msg_err)

			logging.info(f"chat_id={chat_id}({message.chat.title}), msg_id={msg_id}, vote created by {get_username(message.from_user)}")
		else:
			await self.bot.send_message(message.from_user.id, msg_err)

		await self.bot.delete_message(chat_id, msg_id)

		if rfr_type in (config.RFR_GAME, config.RFR_GAME2) and last_games != 0:
			stat = db.get_players_stats(chat_id, last_games, msg_id)

			msg_stat = []
			if stat:
				msg_stat.append(f"Статистика за {last_games} опросов:\n")

				num = 1
				for s in stat:
					msg_stat.append(f"{num}. {s['user_name']} - {s['games']}")
					num += 1
			else:
				msg_stat.append(f"Статистика за {last_games} опросов отсутствует")

			await self.bot.send_message(chat_id, '\n'.join(msg_stat[-4096:]), parse_mode='HTML')

	async def cmd_get(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		user_id = message.from_user.id
		args = message.get_args()
		msg = []
		status = -1

		msg_err = check_input(cmd = 'get', args = args)

		if msg_err == '':
			if args:
				status = int(args)

			referendums = db.get_referendums_by_user_id_db(chat_id, user_id, status)

			msg.append(f"{chat_id}({message.chat.title})")

			for r in referendums:
				msg.append(f"{{msg_id = {r['msg_id']}, title={r['title']}, status={r['status']}, type={r['rfr_type']}, cost={r['game_cost']}, max={r['max_players']}, last_games={r['last_games']}, datum={r['datum']}}}")

			if msg:
				msg = '\n'.join(msg)
			else:
				msg = f"В группе \"{message.chat.title}\" нет опросов"

			await self.bot.send_message(user_id, msg[-4096:])
		else:
			await self.bot.send_message(user_id, msg_err)

		await self.bot.delete_message(chat_id, msg_id)

	async def cmd_close(self, message: types.Message):
		await self.cmd_open_close(message = message, status = 0)

	async def cmd_open(self, message: types.Message):
		await self.cmd_open_close(message = message, status = 1)

	async def cmd_close_all(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id      
		rfr_closed = []
		msg = []

		referendums = db.get_referendums_by_user_id_db(chat_id, user_id, 1)

		for r in referendums:
			msg_id_rfr = r['msg_id']
			rfr_closed.append(f"{r['msg_id']} - {r['title']}")
			db.set_referendum_status_db(chat_id, msg_id_rfr, 0)

			msg_rfr = await self.update_message(message.chat, msg_id_rfr)
			keyboard = None

			await self.bot.edit_message_text(msg_rfr, chat_id = chat_id, message_id = msg_id_rfr + 1, reply_markup = keyboard, parse_mode = "MarkdownV2")
			await self.bot.unpin_chat_message(chat_id, msg_id_rfr + 1)
			logging.info(f"chat_id={chat_id}({message.chat.title}), msg_id={msg_id_rfr}, vote closed by {get_username(message.from_user)}")

		msg.append(f"<b>Группа:</b> \"{message.chat.title}\"\n")
		if rfr_closed:
			msg.append(f"Закрыты опросы:\n")
			msg.append('\n'.join(rfr_closed))
		else:
			msg.append(f"Нет опросов для закрытия")

		await self.bot.send_message(message.from_user.id, '\n'.join(msg[-4096:]), parse_mode='HTML')
		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_open_close(self, message: types.Message, status):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id

		args = message.get_args()
		msg_id = is_one_referendum_active(chat_id, user_id)

		if status == 1:
			check_type = 'open'
		else:
			check_type = 'close'
		msg_err = check_input(check_type, args, chat_id, msg_id, user_id)

		if msg_err == '':
			if args:
				msg_id = int(args)

			db.set_referendum_status_db(chat_id, msg_id, status)
			msg = await self.update_message(message.chat, msg_id)

			if status:
				keyboard = self.get_keyboard(chat_id, msg_id)
				action = 'reopened'
			else:
				keyboard = None
				action = 'closed'

			await self.bot.edit_message_text(msg, chat_id = chat_id, message_id = msg_id + 1, reply_markup = keyboard, parse_mode = "MarkdownV2")

			if status:
				try:
					await self.bot.pin_chat_message(chat_id, msg_id + 1)
					await self.bot.delete_message(chat_id, msg_id_del + 1)
				except:
					msg_err = f"chat_id={chat_id}({message.chat.title}), msg_id={msg_id}, недостаточно прав для управления закреплёнными сообщениями"
					logging.error(msg_err)
			else:
				await self.bot.unpin_chat_message(chat_id, msg_id + 1)

			logging.info(f"chat_id={chat_id}({message.chat.title}), msg_id={msg_id}, vote {action} by {get_username(message.from_user)}")

		if msg_err:
			await self.bot.send_message(message.from_user.id, msg_err)

		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_update(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id
		args = message.get_args().split("|")

		msg_err = check_input(cmd = 'update', args = args, chat_id = chat_id, msg_id = 0, user_id = user_id)

		if msg_err == '':
			msg_id = int(args[0])

			msg_changed = db.update_referendum_db(chat_id = chat_id, args = args)

			if msg_changed:
				msg = await self.update_message(message.chat, msg_id)
				keyboard = self.get_keyboard(chat_id, msg_id)
				await self.bot.edit_message_text(msg, chat_id = chat_id, message_id = msg_id + 1, reply_markup = keyboard, parse_mode = "MarkdownV2")

			logging.info(f"chat_id={chat_id}({message.chat.title}), msg_id={msg_id}, vote edited by {get_username(message.from_user)}")
		else:
			await self.bot.send_message(user_id, msg_err)

		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_add_btn(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id
		args = message.get_args().split("|")

		msg_err = check_input(cmd = 'add_btn', args = args, chat_id = chat_id, msg_id = 0, user_id = user_id)

		if msg_err == '':
			msg_id = int(args[0])
			button_text = args[1]
			referendum = db.get_referendum_db(chat_id, msg_id)

			if referendum['rfr_type'] in (config.RFR_SINGLE, config.RFR_MULTI):
				db.add_button(chat_id, msg_id, button_text)

				msg = await self.update_message(message.chat, msg_id)
				keyboard = self.get_keyboard(chat_id, msg_id)
				await self.bot.edit_message_text(msg, chat_id = chat_id, message_id = msg_id + 1, reply_markup = keyboard, parse_mode = "MarkdownV2")

				logging.info(f"chat_id={chat_id}({message.chat.title}), user {get_username(message.from_user)} added button {button_text}")
			else:
				await self.bot.send_message(message.from_user.id, f"Невозможно добавить кнопку, тип опроса GAME")
		else:
			await self.bot.send_message(message.from_user.id, msg_err)

		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_log(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id

		args = message.get_args()
		msg_id = is_one_referendum_active(chat_id, user_id)
		msg_err = check_input('log', args, chat_id, msg_id, user_id)

		if msg_err == '':
			if args:
				msg_id = int(args)
			msg = read_file(config.FILE_LOG, chat_id, msg_id)

			if not msg:
				msg = 'no logs'
			await self.bot.send_message(user_id, msg[-4096:])

		if msg_err:
			await self.bot.send_message(user_id, msg_err)

		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_cron(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		user_id = message.from_user.id
		rfr_type = 0

		args = message.get_args().split("|")
		msg_err = check_input('cron', args)

		if msg_err == '':
			date_time = args[0]
			rfr_cmd = args[1]
			args = args[2:]

			msg_err = check_input(rfr_cmd, args)

			if msg_err == '':
				if rfr_cmd == config.RFR_GAME_CMD:
					rfr_type = config.RFR_GAME
				elif rfr_cmd == config.RFR_SINGLE_CMD:
					rfr_type = config.RFR_SINGLE
				elif rfr_cmd == config.RFR_MULTI_CMD:
					rfr_type = config.RFR_MULTI
				elif rfr_cmd == config.RFR_GAME2_CMD:
					rfr_type = config.RFR_GAME2

				await self.bot.send_message(user_id, f"chat_id={chat_id}({message.chat.title}), msg_id={msg_id}, scheduled at {date_time}")
				db.create_referendum_db(chat_id = chat_id,
										msg_id = msg_id,
										user_id = message.from_user.id,
										user_name = get_username(message.from_user),
										rfr_type = rfr_type,
										args = args)

				msg = await self.update_message(message.chat, msg_id)
				keyboard = self.get_keyboard(chat_id, msg_id)
				await message.answer(msg, reply_markup = keyboard, parse_mode = "MarkdownV2")

				# db.set_referendum_status_db(chat_id, msg_id, 0)
			else:
				await self.bot.send_message(user_id, msg_err)

		else:
			await self.bot.send_message(user_id, msg_err)

		await self.bot.delete_message(chat_id, msg_id)

	async def cmd_get_stat_over(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id
		args = message.get_args().split("|")

		msg = []


		referendums = db.get_referendums_by_user_id_db(chat_id = chat_id, user_id = user_id)

		msg.append(f"<b>Группа:</b> \"{message.chat.title}\"\n")
		msg.append(f"Статистика переполнения кворума:\n")

		num = 1
		for rfr in referendums:
			votes = db.get_votes_db(chat_id, rfr['msg_id'])

			players = []
			for p in votes[config.BUTTON_ID_YES]['queue']:
				players.append(p['user_name'])

			if players:
				str_players = ", ".join(players)
				msg.append(f"{num}. {rfr['datum'][:10]} - [{str_players}]")
				num += 1

		if num == 1:
			msg.append(f"Статистика переполнения отсутствует")

		await self.bot.send_message(message.from_user.id, '\n'.join(msg[-4096:]), parse_mode='HTML')
		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_get_stat(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id
		args = message.get_args().split("|")

		msg = []
		msg_err = check_input(cmd = 'statall', args = args)

		if msg_err == '':
			last_games = int(args[0])

			if len(args) == 2:
				msg_id = args[1]
			else:
				msg_id = 0

			stat = db.get_players_stats(chat_id, last_games, msg_id)

			msg.append(f"<b>Группа:</b> \"{message.chat.title}\"\n")

			if stat:
				msg.append(f"Статистика за {last_games} опросов:\n")

				num = 1
				for s in stat:
					msg.append(f"{num}. {s['user_name']} - {s['games']}")
					num += 1
			else:
				msg.append(f"Статистика за {last_games} опросов отсутствует")

			await self.bot.send_message(message.from_user.id, '\n'.join(msg[-4096:]), parse_mode='HTML')

		else:
			await self.bot.send_message(message.from_user.id, msg_err)

		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_get_stat_user(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id
		args = message.get_args().split("|")

		msg = []
		msg_err = check_input(cmd = 'statuser', args = args)

		if msg_err == '':
			user_id_stat = int(args[0]) 
			last_games = int(args[1])

			if len(args) == 3:
				msg_id = args[2]
			else:
				msg_id = 0

			stat = db.get_players_stats(chat_id, last_games, msg_id)
			player_stat = next((item for item in stat if item.get('user_id') == user_id_stat), None)

			msg.append(f"<b>Группа:</b> \"{message.chat.title}\"\n")

			if player_stat:
				msg.append(f"Статистика за {last_games} опросов:\n")
				msg.append(f"{player_stat['user_name']}(user_id = {user_id_stat}) - {player_stat['games']}")
				msg.append('\n'.join(player_stat['datums']))
			else:
				msg.append(f"Статистика по user_id = {user_id_stat} за {last_games} опросов отсутствует")

			await self.bot.send_message(message.from_user.id, '\n'.join(msg[-4096:]), parse_mode='HTML')

		else:
			await self.bot.send_message(message.from_user.id, msg_err)

		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_get_regular_players(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		user_id = message.from_user.id
		args = message.get_args()

		msg = []
		player_type = -1
		msg_err = check_input(cmd = 'get_reg', args = args)

		if msg_err == '':
			if args:
				player_type = int(args)

			players = db.get_regular_players_db(chat_id, player_type)

			msg.append(f"{{{chat_id}({message.chat.title})}}")
			for p in players:
				msg.append(f"{{player_type = {p['player_type']}, user_id = {p['user_id']} ({p['user_name']})}}")

			if msg:
				await self.bot.send_message(message.from_user.id, '\n'.join(msg[-4096:]))
			else:
				await self.bot.send_message(message.from_user.id, f"В группе \"{message.chat.title}\" нет регулярных игроков")

		if msg_err:
			await self.bot.send_message(user_id, msg_err)

		await self.bot.delete_message(chat_id, msg_id)

	async def cmd_set_regular_player(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		args = message.get_args().split("|")

		user_name = ''

		msg_err = check_input(cmd = 'set_reg', args = args)

		if msg_err == '':
			user_id = args[0]
			player_type = args[1]

			player = db.get_regular_player_db(chat_id, user_id)

			if player:
				user_name = player['user_name']
			elif len(args) == 3:
				user_name = args[2]

			db.set_regular_player_db(chat_id = chat_id, user_id = user_id, user_name = user_name, player_type = player_type)

			logging.info(f"chat_id={chat_id}({message.chat.title}), user {get_username(message.from_user)} set regular player {user_name}({user_id})")

		else:
			await self.bot.send_message(message.from_user.id, msg_err)

		await self.bot.delete_message(chat_id, msg_id)

	async def cmd_getu(self, message: types.Message):
		user_id = 651786590
		try:
			chat = await self.bot.get_chat(chat_id = user_id)
			if chat.username:
				msg = f"username = {chat.username}"
			else:
				msg = "No username"
		except Exception as e:
			msg = f"Error getting chat info for user ID {user_id}: {e}"

		await self.bot.send_message(message.from_user.id, msg)
		await self.bot.delete_message(chat_id, msg_id)

	async def cmd_vote(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		user_id = message.from_user.id
		args = message.get_args().split("|")
		deleted_players = []

		member = await self.bot.get_chat_member(chat_id, user_id)

		if member['status'] in ('administrator', 'creator'):
			msg_err = check_input(cmd = 'vote', args = args)

			if msg_err == '':
				msg_id_rfr = int(args[0])
				user_id_vote = int(args[1])
				button_id = int(args[2])

				user_name = user_id_vote
				player = db.get_regular_player_db(chat_id, user_id_vote)
				if player:
					user_name = player['user_name']

				action = db.set_vote_db(chat_id = chat_id,
									msg_id = msg_id_rfr,
									user_id = user_id_vote,
									user_name = user_name,
									button_id = button_id)

				referendum = db.get_referendum_db(chat_id, msg_id_rfr)
				msg_rfr = await self.update_message(message.chat, msg_id_rfr)
				if referendum['status']:
					keyboard = self.get_keyboard(chat_id, msg_id_rfr)
				else:
					keyboard = None
				await self.bot.edit_message_text(msg_rfr, chat_id = chat_id, message_id = msg_id_rfr + 1, reply_markup = keyboard, parse_mode = "MarkdownV2")

				msg = f"chat_id={chat_id}({message.chat.title}), user {get_username(message.from_user)} {action} for player {user_name}, button {button_id}"
				logging.info(msg)
				await self.bot.send_message(user_id, msg)

			else:
				await self.bot.send_message(user_id, msg_err)
		else:
			await self.bot.send_message(user_id, "Менять голос может только администратор")

		await self.bot.delete_message(chat_id, msg_id)

	async def cmd_ban(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		user_id = message.from_user.id
		args = message.get_args()

		member = await self.bot.get_chat_member(chat_id, user_id)

		if member['status'] in ('administrator', 'creator'):
			user_name = ''

			if args:
				user_id_ban = int(args)

				player = db.get_regular_player_db(chat_id, user_id_ban)

				if player:
					user_name = player['user_name']

				db.set_regular_player_db(chat_id = chat_id, user_id = user_id_ban, user_name = user_name, player_type = config.PLAYER_TYPE_BANNED)

				await self.send_message_if_banned(message.chat.title, user_id, user_id_ban, user_name, msg_type = "ban")

				logging.info(f"chat_id={chat_id}({message.chat.title}), user {get_username(message.from_user)} banned player {user_name}({user_id_ban})")
		else:
			await self.bot.send_message(user_id, f"Банить может только администратор")

		await self.bot.delete_message(chat_id, msg_id)

	async def cmd_unban(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		user_id = message.from_user.id
		args = message.get_args()

		member = await self.bot.get_chat_member(chat_id, user_id)

		if member['status'] in ('administrator', 'creator'):

			user_name = ''

			if args:
				user_id_ban = int(args)

				player = db.get_regular_player_db(chat_id, user_id_ban)

				if player:
					user_name = player['user_name']

				db.set_regular_player_db(chat_id = chat_id, user_id = user_id_ban, user_name = user_name, player_type = config.PLAYER_TYPE_USUAL)

				await self.send_message_if_banned(message.chat.title, user_id, user_id_ban, user_name, msg_type = "unban")

				logging.info(f"chat_id={chat_id}({message.chat.title}), user {get_username(message.from_user)} unbanned player {user_name}({user_id_ban})")
		else:
			await self.bot.send_message(user_id, f"Разбанить может только администратор")

		await self.bot.delete_message(chat_id, msg_id)

	async def cmd_del_regular_player(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		user_id = message.from_user.id
		args = message.get_args().split("|")
		deleted_players = []

		member = await self.bot.get_chat_member(chat_id, user_id)

		if member['status'] in ('administrator', 'creator'):
			msg_err = check_input(cmd = 'del_reg', args = args)

			if msg_err == '':
				users_id_del = args
				for uid in users_id_del:
					player = db.get_regular_player_db(chat_id, uid)
					deleted_players.append(f"{player['user_name']}({uid})")
					db.del_regular_player_db(chat_id = chat_id, user_id = uid)

				msg = ", ".join(deleted_players)
				msg = f"chat_id={chat_id}({message.chat.title}), user {get_username(message.from_user)} delete regular players: {msg}"
				logging.info(msg)
				await self.bot.send_message(user_id, msg)

			else:
				await self.bot.send_message(user_id, msg_err)
		else:
			await self.bot.send_message(user_id, "Удалять может только администратор")

		await self.bot.delete_message(chat_id, msg_id)

	async def cmd_get_silent(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id
		args = message.get_args()

		msg = []
		msg_id = is_one_referendum_active(chat_id, user_id)
		msg_err = check_input(cmd = 'get_silent', args = args, chat_id = chat_id, msg_id = msg_id, user_id = user_id)

		if msg_err == '':
			if args:
				msg_id = int(args)

			silent_members = db.get_silent_members_db(chat_id, msg_id)

			for p in silent_members:
				try:
					member = await self.bot.get_chat_member(chat_id, p['user_id'])
				except:
					continue
				msg.append(f"{{{chat_id}({message.chat.title}), user_id = {p['user_id']} ({escape_md(get_username(member['user']))})}}")

			if msg:
				await self.bot.send_message(message.from_user.id, '\n'.join(msg))
			else:
				await self.bot.send_message(message.from_user.id, f"В группе \"{message.chat.title}\" нет молчунов")
		else:
			await self.bot.send_message(user_id, msg_err)

		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_notify(self, message: types.Message):
		await self.notify(message, notify_type = "silent")
	async def cmd_notifyq(self, message: types.Message):
		await self.notify(message, notify_type = "button_?")

	async def notify(self, message: types.Message, notify_type):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		user_id = message.from_user.id
		args = message.get_args().split("|")

		msg = ""
		userlist = []
		users = []

		msg_id = is_one_referendum_active(chat_id, user_id)
		msg_err = check_input(cmd = 'notify', args = args, chat_id = chat_id, msg_id = msg_id, user_id = user_id)

		if msg_err == '':
			if len(args) == 2:
				msg_id = int(args[0])
				text = str(args[1])
			else:
				text = str(args[0])

			if notify_type == "silent":
				users = db.get_silent_members_db(chat_id, msg_id)
			elif notify_type == "button_?":
				users = db.get_undefined_members(chat_id, msg_id)

			for p in users:
				try:
					user = await self.bot.get_chat_member(chat_id, p['user_id'])
				except:
					continue
				userlist.append(f"[{escape_md(get_username(user['user']))}](tg://user?id={p['user_id']})")

			if userlist:
				referendum = db.get_referendum_db(chat_id, msg_id)
				msg += "*Опрос:* " + escape_md(referendum['title']) + '\n' + '\n'
				msg += ", ".join(userlist) + '\n'
				msg += escape_md(text) + '\n'
				await message.answer(msg, parse_mode = "MarkdownV2")
		else:
			await self.bot.send_message(user_id, msg_err)

		await self.bot.delete_message(chat_id, msg_id_del)

	async def cmd_extend_table(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id

		db.extend_table()
		# db.drop_table_column()

		await self.bot.delete_message(chat_id, msg_id)
		logging.info(f"DB tables changed by user {get_username(message.from_user)}")

	async def send_message_if_lineup_changed(self, chat_id, chat_title, msg_id, referendum, votes_old):
		max_players = 0
		players_old = 0
		players_new = 0
		players_friends = 0
		user_id_msg = 0

		max_players = referendum['max_players']
		players_old = len(votes_old[config.BUTTON_ID_YES]['players'])

		if referendum['rfr_type'] in (config.RFR_GAME, config.RFR_GAME2) and max_players > 0:
			friends = db.get_friends_db(chat_id, msg_id)

			for uid in friends:
				players_friends += friends[uid]['friends']

			if players_old + players_friends >= max_players:
				votes_new = db.get_votes_db(chat_id, msg_id)
				players_new = len(votes_new[config.BUTTON_ID_YES]['players'])

				if( players_old == max_players and
					players_new == max_players ):

					for new_player in votes_new[config.BUTTON_ID_YES]['players']:
						if new_player not in votes_old[config.BUTTON_ID_YES]['players']:
							user_id_msg = new_player['user_id']
							msg = f"В кворуме освободилось место, и Вы его заняли! Не забудьте приехать на игру!"

				elif players_old > players_new:
					friends_needed = max_players - players_new
					counter = friends_needed

					for uid in friends:
						if counter == 1:
							user_id_msg = uid
							msg = f"В кворуме освободилось место, и участник от Вас его занял! Не забудьте ему напомнить приехать на игру!"
							break
						else:
							counter -= 1

				elif players_old < players_new:
					friend_out = max_players - players_old
					counter = 1

					for uid in friends:
						if counter == friend_out:
							user_id_msg = uid
							msg = f"Место вашего друга в кворуме занял постоянный участник, не забудьте ему об этом напомнить."
							break
						else:
							counter += 1

				if user_id_msg:
					msg = f"<b>Группа:</b> \"{chat_title}\"\n<b>Тема опроса:</b> \"{referendum['title']}\"\n{msg}"
					await self.bot.send_message(user_id_msg, msg, parse_mode='HTML')

	async def send_message_if_voted(self, chat_id, chat_title, msg_id, referendum, user_name, button_id):
		user_id_msg = 575441834

		if user_id_msg == referendum['user_id']:
			buttons = db.get_buttons_db(chat_id, msg_id)

			msg = f"Участник {user_name} нажал кнопку {buttons[button_id]['button_text']}"
			msg = f"<b>Группа:</b> \"{chat_title}\"\n<b>Тема опроса:</b> \"{referendum['title']}\"\n{msg}"
			await self.bot.send_message(user_id_msg, msg, parse_mode='HTML')

	async def send_message_if_banned(self, chat_title, user_id, user_id_ban, user_name, msg_type):
		if msg_type == "ban":
			msg     = f"Вы запретили {user_name} нажимать кнопки, user_id = {user_id_ban}"
			msg_ban = f"Установлено ограничение на нажатие кнопок в группе."
		elif msg_type == "unban":
			msg     = f"Вы разрешили {user_name} нажимать кнопки, user_id = {user_id_ban}"
			msg_ban = f"Ограничение на нажатие кнопок в группе снято."

		if msg_type in ("ban", "unban"):
			msg     = f"<b>Группа:</b> \"{chat_title}\"\n{msg}"
			msg_ban = f"<b>Группа:</b> \"{chat_title}\"\n{msg_ban}"
			await self.bot.send_message(user_id,     msg,     parse_mode='HTML')
			await self.bot.send_message(user_id_ban, msg_ban, parse_mode='HTML')

	async def process_callback(self, cbq: types.CallbackQuery, callback_data: dict):
		chat_id = cbq.message.chat.id
		msg_id = cbq.message.message_id - 1
		user_id = cbq.from_user.id
		user_name = get_username(cbq.from_user)
		button_id = int(callback_data['button'])
		chat_title = cbq.message.chat.title
		member = await self.bot.get_chat_member(chat_id, user_id)
		action = ''
		player_type = db.get_player_type(chat_id, user_id)

		db.set_regular_player_db(chat_id = chat_id, user_id = user_id, user_name = get_username(member['user']), player_type = player_type)

		referendum = db.get_referendum_db(chat_id, msg_id)
		votes = db.get_votes_db(chat_id, msg_id)

		if player_type != config.PLAYER_TYPE_BANNED:
			action = db.set_vote_db(chat_id = chat_id,
									msg_id = msg_id,
									user_id = user_id,
									user_name = user_name,
									button_id = button_id)

			msg = await self.update_message(cbq.message.chat, msg_id)
			keyboard = self.get_keyboard(chat_id, msg_id)

			with suppress(MessageNotModified):
				await cbq.message.edit_text(msg, reply_markup = keyboard, parse_mode = "MarkdownV2")
			await cbq.answer()

			log_msg = f"chat_id={chat_id}({chat_title}), msg_id={msg_id}, user {user_name} {action}, button {int(callback_data['button'])}"
			logging.info(log_msg)

			await self.send_message_if_voted(chat_id, chat_title, msg_id, referendum, user_name, button_id)
			await self.send_message_if_lineup_changed(chat_id, chat_title, msg_id, referendum, votes)

	def get_keyboard(self, chat_id, msg_id):
		referendum = db.get_referendum_db(chat_id, msg_id)
		buttons = db.get_buttons_db(chat_id, msg_id)
		votes = db.get_votes_db(chat_id, msg_id)

		keyboard_btns = []

		for button_id in buttons:
			button_text = buttons[button_id]['button_text']
			button_votes = len(votes[button_id]['players']) + len(votes[button_id]['queue'])

			if button_votes:
				button_text += f" - {button_votes}"
			keyboard_btns.append(types.InlineKeyboardButton(text = button_text, callback_data = self.callback_numbers.new(button = button_id)))

		keyboard = types.InlineKeyboardMarkup(row_width = 1)
		keyboard.add(*keyboard_btns)

		return keyboard

	async def update_message(self, chat, msg_id):
		chat_id = chat.id
		chat_members = await chat.get_member_count()

		button_votes = 0
		button_votes_total = 0
		button_1_votes = 0
		unique_users_votes = 0
		votes_percent = 0
		votes_percent_by_chat = 0
		regular_players = 0
		other_players = 0
		players_friends = 0
		friends_needed = 0
		entry_fee = 0
		sym = ''
		flag_regular_used = False

		referendum = db.get_referendum_db(chat_id, msg_id)
		buttons = db.get_buttons_db(chat_id, msg_id)
		votes = db.get_votes_db(chat_id, msg_id)
		friends = db.get_friends_db(chat_id, msg_id)

		buttons_sorted = sort_buttons(buttons, votes, referendum['rfr_type'])

		if referendum['rfr_type'] in (config.RFR_GAME, config.RFR_GAME2):
			flag_game_game2 = True

			if db.is_regular_players_used_db(chat_id):
				flag_regular_used = True
		else:
			flag_game_game2 = False

		for uid in friends:
			players_friends += friends[uid]['friends']

		unique_users = set()
		for button_id in votes:
			for player in votes[button_id]['players']:
				if referendum['rfr_type'] == config.RFR_GAME2 and button_id == config.BUTTON_ID_OPT:
					pass
				else:
					unique_users.add(player['user_id'])
		unique_users_votes = len(unique_users)

		for button_id in buttons:
			button_votes = len(votes[button_id]['players']) + len(votes[button_id]['queue'])

			if referendum['rfr_type'] != config.RFR_GAME2 or button_id != config.BUTTON_ID_OPT:
				button_votes_total += button_votes

			if button_id == config.BUTTON_ID_YES:
				button_1_votes = button_votes

				for usr in votes[1]['players']:
					if db.get_player_type(chat_id, usr['user_id']) == config.PLAYER_TYPE_REGULAR:
						regular_players += 1
					else:
						other_players +=1

		if flag_game_game2:
			plr_yes = button_1_votes + players_friends

			if referendum['max_players']:
				plr_max = referendum['max_players']
			else:
				plr_max = chat_members - 1
		else:
			plr_yes = unique_users_votes
			plr_max = chat_members - 1

		msg = f"*\\[{plr_yes}\\/{plr_max}\\] {escape_md(referendum['title'])}*\n\n"

		for button in buttons_sorted:
			button_id = button['button_id']

			button_votes = len(votes[button_id]['players']) + len(votes[button_id]['queue'])

			if button_votes_total:
				votes_percent = int(100 * round(button_votes/button_votes_total, 2))

			if flag_game_game2 and button_id in (config.BUTTON_ID_ADD, config.BUTTON_ID_DEL):
				continue
			else:
				if referendum['rfr_type'] == config.RFR_GAME2 and button_id == config.BUTTON_ID_OPT:
					msg += f"{escape_md(buttons[button_id]['button_text'])} \\- {button_votes}\n"
				else:
					msg += f"{escape_md(buttons[button_id]['button_text'])} \\- {button_votes} \\({votes_percent}%\\)\n"

				userlist = []
				for usr in votes[button_id]['players']:
					if flag_game_game2:
						if flag_regular_used == False or db.get_player_type(chat_id, usr['user_id']) == config.PLAYER_TYPE_REGULAR:
							sym = ''
						else:
							sym = '_'
					userlist.append(f"{sym}[{escape_md(usr['user_name'])}](tg://user?id={usr['user_id']}){sym}")

				if userlist:
					msg += ", ".join(userlist) + '\n'
				msg += '\n'

				if len(votes[button_id]['queue']):
					userlist = []
					for usr in votes[button_id]['queue']:
						if flag_game_game2:
							if flag_regular_used == False or db.get_player_type(chat_id, usr['user_id']) == config.PLAYER_TYPE_REGULAR:
								sym = ''
							else:
								sym = '_'
						userlist.append(f"{sym}[{escape_md(usr['user_name'])}](tg://user?id={usr['user_id']}){sym}")

					if userlist:
						msg += f"\\[{', '.join(userlist)}\\]\n\n"

				if flag_game_game2 and button_id == config.BUTTON_ID_YES:
					if players_friends:
						bttn4_text = buttons[config.BUTTON_ID_ADD]['button_text']
						plur = get_morph(bttn4_text)

						if plur == bttn4_text:
							msg += f"{bttn4_text}\\:\n"
						else:
							msg += f"{plur} от\\:\n"

						for user_id in friends:
							if flag_regular_used == False or db.get_player_type(chat_id, user_id) == config.PLAYER_TYPE_REGULAR:
								sym = ''
							else:
								sym = '_'
							msg += f"{sym}[{escape_md(friends[user_id]['user_name'])}](tg://user?id={user_id}){sym} \\- {friends[user_id]['friends']}\n"
						msg += '\n'

		if chat_members - 1:
			votes_percent_by_chat = int(100 * round(unique_users_votes/(chat_members-1), 2))

			msg += f"👥👥👥👥\n"
			msg += f"*Голосов: {unique_users_votes} из {chat_members - 1} \\({votes_percent_by_chat}%\\)*\n"

		if flag_game_game2:
			if flag_regular_used:
				msg += f"*Кворум: {button_1_votes + players_friends} \\(пост \\- {regular_players}, раз \\- {other_players + players_friends}\\)*\n"
			else:
				msg += f"*Кворум: {button_1_votes + players_friends}*\n"

			if referendum['max_players']:
				free_slots = referendum['max_players'] - button_1_votes - players_friends
				friends_needed = referendum['max_players'] - button_1_votes
				next_player = get_next_player(votes, buttons, friends, friends_needed)

				if free_slots >= 0:
					msg += f"*Свободных мест: {free_slots}*\n"
				else:
					msg += f"*Очередь: {abs(free_slots)}*\n"
					msg += f"*Следующий: {escape_md(next_player)}*\n"

			if referendum['game_cost']:
				if button_1_votes + players_friends > referendum['max_players'] > 0:
					entry_fee = int(round(referendum['game_cost'] / referendum['max_players'], 0))
				elif button_1_votes + players_friends:
					entry_fee = int(round(referendum['game_cost'] / (button_1_votes + players_friends), 0))
				else:
					entry_fee = referendum['game_cost']

				msg += f"*Стоимость: {entry_fee} ₽*\n"

		return msg

if __name__ == "__main__":
	kaa = MyBot()
