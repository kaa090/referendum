#!venv/bin/python3
import logging
import referendum_db as db
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified
from aiogram.utils.markdown import escape_md
from contextlib import suppress
from config import TOKEN, FILE_LOG, LEVEL

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
		self.dp.register_message_handler(self.cmd_create, commands = "create")
		self.dp.register_message_handler(self.cmd_close, commands = "close")
		self.dp.register_message_handler(self.cmd_update, commands = "update")
		self.callback_numbers = CallbackData("prefix", "button")
		self.dp.register_callback_query_handler(self.process_callback, self.callback_numbers.filter())
		
		executor.start_polling(self.dp, skip_updates=True)

	async def cmd_create(self, message: types.Message):
		db.create_referendum_db(chat_id=message.chat.id, 
								msg_id=message.message_id, 
								user_id=message.from_user.id, 
								user_name=get_username(message.from_user), 
								args=message.get_args())

		logging.info(f"chatID={message.chat.id}({message.chat.title}), msgID={message.message_id}, vote created by {message.from_user.first_name}")

		msg = await self.update_message(message.chat, message.message_id)
		keyboard = self.get_keyboard(message.chat.id, message.message_id)
		
		await message.answer(msg, reply_markup = keyboard, parse_mode="MarkdownV2")

	async def cmd_update(self, message: types.Message):
		pass
		# db.create_referendum_db(chat_id=message.chat.id, 
		# 						msg_id=message.message_id, 
		# 						user_id=message.from_user.id, 
		# 						user_name=get_username(message.from_user), 
		# 						args=message.get_args())

		# logging.info(f"chatID={message.chat.id}({message.chat.title}), msgID={message.message_id}, vote created by {message.from_user.first_name}")

		# msg = await self.update_message(message.chat, message.message_id)
		# keyboard = self.get_keyboard(message.chat.id, message.message_id)
		
		# await message.answer(msg, reply_markup = keyboard, parse_mode="MarkdownV2")

	async def cmd_close(self, message: types.Message):
		msg_id = int(message.get_args())
		msg = await self.update_message(message.chat, msg_id)
		await self.bot.edit_message_text(msg, chat_id = message.chat.id, message_id = msg_id + 1)
		logging.info(f"chatID={message.chat.id}({message.chat.title}), msgID={msg_id}, vote closed by {message.from_user.first_name}")

	async def process_callback(self, cbq: types.CallbackQuery, callback_data: dict):
		action = db.set_vote_db(chat_id=cbq.message.chat.id,
					msg_id=cbq.message.message_id - 1,
					user_id=cbq.from_user.id,
					user_name=get_username(cbq.from_user),
					button_id=int(callback_data['button']))
		
		logging.info(f"chatID={cbq.message.chat.id}({cbq.message.chat.title}), msgID={cbq.message.message_id - 1}, user {cbq.from_user.first_name} {action} for {int(callback_data['button'])}")
		
		msg = await self.update_message(cbq.message.chat, cbq.message.message_id - 1)
		keyboard = self.get_keyboard(cbq.message.chat.id, cbq.message.message_id - 1)
		
		with suppress(MessageNotModified):
			await cbq.message.edit_text(msg, reply_markup = keyboard, parse_mode="MarkdownV2")
		await cbq.answer()
	
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
