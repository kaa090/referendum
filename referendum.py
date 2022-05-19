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
FILE_DB = "referendums.db"

class MyBot:
	def __init__(self):
		logging.basicConfig(level = logging.DEBUG, 
							format = "[%(asctime)s] [%(levelname)-8s] [%(funcName)s]: %(message)s",
							handlers = [logging.FileHandler(FILE_LOG), logging.StreamHandler()])

		self.referendums = {}
		self.bot = Bot(token = TOKEN)
		self.dp = Dispatcher(self.bot)
		self.dp.register_message_handler(self.cmd_create, commands = "create")
		self.callback_numbers = CallbackData("prefix", "button")
		self.dp.register_callback_query_handler(self.process_callback, self.callback_numbers.filter())
		
		executor.start_polling(self.dp, skip_updates=True)

	async def cmd_create(self, message: types.Message):
		args = message.get_args().split("|")
		self.first_voters_count = int(args[0])

		self.args = []
		for arg in args[1:]:
			self.args.append(escape_md(arg))

		self.chat_members = await message.chat.get_member_count()
		self.init_referendum()
		msg = self.update_message(0, '')
		keyboard = self.get_keyboard()
		
		logging.info(self.args)
		logging.info(f"[chatID={message.chat.id}, msgID={message.message_id}] vote created: {self.referendums}")
		
		await message.answer(msg, reply_markup = keyboard, parse_mode="MarkdownV2")

	async def process_callback(self, cbq: types.CallbackQuery, callback_data: dict):
		msg = self.update_message(int(callback_data["button"]), cbq.from_user)
		keyboard = self.get_keyboard()
		
		logging.info(f"[chatID={cbq.message.chat.id}, msgID={cbq.message.message_id}] {cbq.from_user} pressed button {callback_data['button']}")
		
		with suppress(MessageNotModified):
			await cbq.message.edit_text(msg, reply_markup = keyboard, parse_mode="MarkdownV2")
		await cbq.answer()
	
	def get_keyboard(self):
		buttons = []

		for i in range(1, len(self.args)):
			button_text = self.args[i]
			if len(self.referendums[i]):
				button_text += f" - {len(self.referendums[i])}"
			buttons.append(types.InlineKeyboardButton(text = button_text, callback_data = self.callback_numbers.new(button = i)))

		keyboard = types.InlineKeyboardMarkup(row_width = 1)
		keyboard.add(*buttons)

		return keyboard

	def init_referendum(self):
		for i in range(1, len(self.args)):
			self.referendums[i] = []
	
	def update_message(self, button: int, user):
		flag = True
		votes = 0
		votes_total = 0
		votes_percent = 0
		votes_percent_by_chat = 0

		logging.debug(f"start: {self.referendums}")

		if button:
			mention = f"[{escape_md(user.first_name)}](tg://user?id={user.id})"
			
			for i in range(1, len(self.args)):
				if user in self.referendums[i]:
					self.referendums[i].remove(user)
					if i == button:
						flag = False
			if flag:
				self.referendums[button].append(user)

		msg = f"*{self.args[0]}*\n\n"

		for i in range(1, len(self.args)):
			votes_total += len(self.referendums[i])

		for i in range(1, len(self.args)):
			votes = len(self.referendums[i])
			if(votes_total):
				votes_percent = int(100 * round(votes/votes_total, 2))
			
			msg += f"{self.args[i]} \\- {len(self.referendums[i])} \\({votes_percent}%\\)\n"
					
			# userlist = []
			# current_user = 0
			# for usr in self.referendums[i]:
			# 	if(i == 1):
			# 		if(current_user < self.first_voters_count):
			# 			mark = ''
			# 		else:
			# 			mark = '~'
			# 	else:
			# 		mark = ''
			# 	userlist.append(f"{mark}[{escape_md(usr.first_name)}](tg://user?id={usr.id}){mark}")
			# 	current_user += 1

			userlist = []
			current_user = 0
			for usr in self.referendums[i]:
				if(i == 1):
					if(current_user == 0):
						mark1 = '\\['
						if(len(self.referendums[i]) == 1):
							mark2 = '\\]'
						else:
							mark2 = ''
					elif(current_user <= self.first_voters_count - 1):
						mark1 = ''
						mark2 = '\\]'
					else:
						mark1 = ''
						mark2 = ''
				else:
					mark1 = ''
					mark2 = ''

				userlist.append(f"{mark1}[{escape_md(usr.first_name)}](tg://user?id={usr.id}){mark2}")
				current_user += 1
			
			if(userlist):
				msg += ", ".join(userlist) + '\n\n'
			else:
				msg += '\n'			
		
		if(self.chat_members - 1):
			votes_percent_by_chat = int(100 * round(votes_total/(self.chat_members-1), 2))
		msg += f"👥 {votes_total} of {self.chat_members - 1} \\({votes_percent_by_chat}%\\) people voted so far\\."
		
		logging.debug(f"msg={msg}")
		logging.debug(f"end: {self.referendums}")
		return msg

if __name__ == "__main__":
	kaa = MyBot()