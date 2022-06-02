#!venv/bin/python3
import logging
import referendum_db as db
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified
from aiogram.utils.markdown import escape_md
from contextlib import suppress
from config import TOKEN, FILE_LOG, LEVEL

def check_input(func, args):
	if func == 'create':
		if len(args) < 4:
			return "usage: /create max_players|Num_1,...,Num_k|title|button_1|...|button_k"
		
		if args[0].isnumeric():
			max_num = args[0]
		else:
			return "max_players is a number"
		
		factors = args[1].split(",")
		for f in factors:
			if f.isnumeric() == False:
				return "Num_1,...,Num_k should be a list of numbers separated by commas"
		if len(factors) != len(args[3:]):
			return "number of buttons not equals to number of factors"

	elif func == 'update':
		if len(args) < 3:
			return "usage: /update msg_id|max_players|title"

		if args[0].isnumeric() == False:
			return "msg_id should be a number"

		if args[1].isnumeric() == False:
			return "max_players should be a number"

	elif func == 'open_close':
		if args.isnumeric() == False:
			return "msg_id should be a number"

	return ''

def get_username(user):
	if(user.last_name):
		return f"{user.first_name} {user.last_name}"
	elif(user.username):
		return user.username
	else:
		return user.first_name

def get_next_candidate(referendum, buttons):
	next_candidate = ''
	btn_id = 1

	if len(buttons):
		for button_id in buttons:
			if len(referendum[button_id]['bench']):
				min_factor = buttons[button_id]['button_factor']
				btn_id = button_id
				break

		for button_id in buttons:
			factor = buttons[button_id]['button_factor']
			if len(referendum[button_id]['bench']) and min_factor > factor:
				min_factor = factor
				btn_id = button_id

		if referendum[btn_id]['bench']:
			next_candidate = referendum[btn_id]['bench'][0]['user_name']

	return next_candidate

class MyBot:
	def __init__(self):
		logging.basicConfig(level = LEVEL,
							format = "[%(asctime)s] [%(levelname)-8s] [%(funcName)s]: %(message)s",
							handlers = [logging.FileHandler(FILE_LOG), logging.StreamHandler()])

		db.create_tables()

		self.bot = Bot(token = TOKEN)
		self.dp = Dispatcher(self.bot)
		self.dp.register_message_handler(self.cmd_get, commands = "get")
		self.dp.register_message_handler(self.cmd_create, commands = "create")
		self.dp.register_message_handler(self.cmd_open, commands = "open")
		self.dp.register_message_handler(self.cmd_close, commands = "close")
		self.dp.register_message_handler(self.cmd_update, commands = "update")
		self.callback_numbers = CallbackData("prefix", "button")
		self.dp.register_callback_query_handler(self.process_callback, self.callback_numbers.filter())

		executor.start_polling(self.dp, skip_updates = True)

	async def cmd_get(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		msg = []

		referendums = db.get_referendums_by_user_id_db(chat_id, message.from_user.id)

		for r in referendums:
			msg.append(f"{{msg_id = {r['msg_id']}, title = {r['title']}}}")
		
		if msg:			
			await self.bot.send_message(chat_id, '\n'.join(msg))
		
		await self.bot.delete_message(chat_id, msg_id)
		logging.info(f"chatID={chat_id}({message.chat.title}), user {message.from_user.first_name} got his votes: {'; '.join(msg)}")

	async def cmd_create(self, message: types.Message):
		chat_id = message.chat.id
		msg_id = message.message_id
		args = message.get_args().split("|")

		msg_log = check_input('create', args)

		if msg_log == '':
			db.create_referendum_db(chat_id = chat_id,
									msg_id = msg_id,
									user_id = message.from_user.id,
									user_name = get_username(message.from_user),
									args = args)

			msg = await self.update_message(message.chat, msg_id)
			keyboard = self.get_keyboard(chat_id, msg_id)
			await message.answer(msg, reply_markup = keyboard, parse_mode = "MarkdownV2")

			msg_log = f"vote created by {message.from_user.first_name}"
		
		await self.bot.delete_message(chat_id, msg_id)
		logging.info(f"chatID={chat_id}({message.chat.title}), msgID={msg_id}, {msg_log}")

	async def cmd_update(self, message: types.Message):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		args = message.get_args().split("|")

		msg_log = check_input('update', args)

		if msg_log == '':		
			msg_id = int(args[0])

			if db.check_msg_id(chat_id, msg_id):
				if db.check_user_id(chat_id, msg_id, message.from_user.id):
					db.update_referendum_db(chat_id = chat_id, msg_id = msg_id, max_num = args[1], title = args[2])

					msg = await self.update_message(message.chat, msg_id)
					keyboard = self.get_keyboard(chat_id, msg_id)
					await self.bot.edit_message_text(msg, chat_id = chat_id, message_id = msg_id + 1, reply_markup = keyboard, parse_mode = "MarkdownV2")

					msg_log = f"msgID={msg_id}, vote edited by {message.from_user.first_name}"
				else:
					msg_log = f"msgID={msg_id}, user {message.from_user.first_name} unsuccesefully tried to edit foreign vote"
			else:
				msg_log = f"user {message.from_user.first_name} mistaked with msg_id"
		
		await self.bot.delete_message(chat_id, msg_id_del)
		logging.info(f"chatID={chat_id}({message.chat.title}), {msg_log}")

	async def cmd_open(self, message: types.Message):
		await self.cmd_open_close(message, 1)

	async def cmd_close(self, message: types.Message):
		await self.cmd_open_close(message, 0)

	async def cmd_open_close(self, message: types.Message, status):
		chat_id = message.chat.id
		msg_id_del = message.message_id
		args = message.get_args()

		msg_log = check_input('open_close', args)

		if msg_log == '':
			msg_id = int(args)
			
			if db.check_msg_id(chat_id, msg_id):
				if db.check_user_id(chat_id, msg_id, message.from_user.id):
					db.set_referendum_status_db(chat_id, msg_id, status)

					msg = await self.update_message(message.chat, msg_id)

					if status:
						keyboard = self.get_keyboard(chat_id, msg_id)
						action = 'reopened'
					else:
						keyboard = None
						action = 'closed'

					await self.bot.edit_message_text(msg, chat_id = chat_id, message_id = msg_id + 1, reply_markup = keyboard, parse_mode = "MarkdownV2")

					msg_log = f"msgID={msg_id}, vote {action} by {message.from_user.first_name}"
				else:
					msg_log = f"msgID={msg_id}, user {message.from_user.first_name} unsuccesefully tried to close foreign vote"
			else:
				msg_log = f"user {message.from_user.first_name} mistaked with msg_id"
		else:
			msg_log = f"user {message.from_user.first_name} mistaked with msg_id"

		await self.bot.delete_message(chat_id, msg_id_del)
		logging.info(f"chatID={chat_id}({message.chat.title}), {msg_log}")

	async def process_callback(self, cbq: types.CallbackQuery, callback_data: dict):
		chat_id = cbq.message.chat.id
		msg_id = cbq.message.message_id - 1

		action = db.set_vote_db(chat_id = chat_id,
					msg_id = msg_id,
					user_id = cbq.from_user.id,
					user_name = get_username(cbq.from_user),
					button_id = int(callback_data['button']))

		msg = await self.update_message(cbq.message.chat, msg_id)
		keyboard = self.get_keyboard(chat_id, msg_id)
		
		with suppress(MessageNotModified):
			await cbq.message.edit_text(msg, reply_markup = keyboard, parse_mode = "MarkdownV2")
		await cbq.answer()

		logging.info(f"chatID={chat_id}({cbq.message.chat.title}), msgID={msg_id}, user {cbq.from_user.first_name} {action} for {int(callback_data['button'])}")

	def get_keyboard(self, chat_id, msg_id):
		buttons = db.get_buttons_db(chat_id, msg_id)
		referendum = db.get_votes_db(chat_id, msg_id)
		keyboard_btns = []

		for button_id in buttons:
			button_text = buttons[button_id]['button_text']
			button_votes = len(referendum[button_id]['roster']) + len(referendum[button_id]['bench'])

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
		votes_yes = 0
		votes_total = 0
		votes_percent = 0
		votes_percent_by_chat = 0

		referendum_params = db.get_referendum_db(chat_id, msg_id)
		buttons = db.get_buttons_db(chat_id, msg_id)
		referendum = db.get_votes_db(chat_id, msg_id)
		
		msg = f"*{escape_md(referendum_params['title'])}*\n\n"

		for button_id in buttons:
			button_votes = len(referendum[button_id]['roster']) + len(referendum[button_id]['bench'])
			votes_yes += buttons[button_id]['button_factor'] * button_votes
			votes_total += button_votes

		for button_id in buttons:
			button_votes = len(referendum[button_id]['roster']) + len(referendum[button_id]['bench'])

			if(votes_total):
				votes_percent = int(100 * round(button_votes/votes_total, 2))

			msg += f"{escape_md(buttons[button_id]['button_text'])} \\- {button_votes} \\({votes_percent}%\\)\n"

			userlist = []
			for usr in referendum[button_id]['roster']:
				userlist.append(f"[{escape_md(usr['user_name'])}](tg://user?id={usr['user_id']})")

			if(userlist):
				msg += ", ".join(userlist) + '\n\n'
			else:
				msg += '\n'

			if len(referendum[button_id]['bench']):
				userlist = []
				for usr in referendum[button_id]['bench']:
					userlist.append(f"[{escape_md(usr['user_name'])}](tg://user?id={usr['user_id']})")

				if(userlist):
					msg += f"\\[{', '.join(userlist)}\\]\n\n"
				else:
					msg += '\n'

		if(chat_members - 1):
			votes_percent_by_chat = int(100 * round(votes_total/(chat_members-1), 2))
		msg += f"👥👥👥👥\n"
		msg += f"{votes_total} of {chat_members - 1} \\({votes_percent_by_chat}%\\) people voted so far\n"

		diff = referendum_params['max_num'] - votes_yes
		next_candidate = get_next_candidate(referendum, buttons)

		msg += f"*Total confirmed: {votes_yes}*\n"
		if(diff >= 0):
			msg += f"*Free slots left: {diff}*"
		else:
			msg += f"*Extra people: {abs(diff)}*\n"
			msg += f"*Next candidate: {escape_md(next_candidate)}*"

		return msg

if __name__ == "__main__":
	kaa = MyBot()
