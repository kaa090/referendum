#!venv/bin/python
import logging
import datetime
import math
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified
from aiogram.utils.markdown import escape_md
from contextlib import suppress
from config import TOKEN

class MyBot111:
	def __init__(self):
		self.referendums = {}

		logging.basicConfig(level = logging.INFO)
		self.bot = Bot(token = TOKEN)
		self.dp = Dispatcher(self.bot)
		self.dp.register_message_handler(self.cmd_create, commands = "create")
		self.callback_numbers = CallbackData("prefix", "button")
		self.dp.register_callback_query_handler(self.process_callback, self.callback_numbers.filter())
		
		executor.start_polling(self.dp, skip_updates=True)

	async def cmd_create(self, message: types.Message):
		self.args = message.get_args().split("|")
		self.init_referendum()
		print(f"chatID={message.chat.id}, {datetime.datetime.now()}. {message.from_user} poll created")
		msg = self.update_message(0, '')
		keyboard = self.get_keyboard()
		
		await message.answer(msg, reply_markup = keyboard, parse_mode="MarkdownV2")

	async def process_callback(self, cbq: types.CallbackQuery, callback_data: dict):
		msg = self.update_message(int(callback_data["button"]), cbq.from_user)
		keyboard = self.get_keyboard()
		print(f"chatID={cbq.message.chat.id}, {datetime.datetime.now()}. {cbq.from_user} pressed button {callback_data['button']}")
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
		votes_share = 0
		votes_total = 0
		votes_symbol = '✅'
		votes_no_symbol = '❌'
		votes_total_symbol = '👥'

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
				votes_share = round(votes/votes_total, 2)
			votes_percent = 100 * votes_share
			votes_print = math.ceil(10 * votes_share)
			
			msg += f"{self.args[i]} \\- {len(self.referendums[i])}\n"
		
			if self.referendums[i]:
				msg += votes_symbol * int(votes_print) + str(int(votes_percent)) + "%\n"
			else:
				msg += f"{votes_no_symbol}0%\n"

			userlist = []
			for user in self.referendums[i]:
				userlist.append(f"[{escape_md(user.first_name)}](tg://user?id={user.id})")
				
			if(userlist):
				msg += ", ".join(userlist) + '\n\n'
			else:
				msg += '\n'			
		
		msg += f"{votes_total_symbol} {votes_total} people voted so far\\."

		return msg

if __name__ == "__main__":
	kaa = MyBot111()