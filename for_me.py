import logging
import sys
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton

# Replace 'YOUR_BOT_TOKEN' with your actual bot token obtained from BotFather
BOT_TOKEN = '7028991315:AAG6uc--rKkrmsoO3Irx02SVM-V7JdLgSik'

dp = Dispatcher()

# Language selection keyboard
language_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("🇺🇿 Uzbek"), KeyboardButton("🇷🇺 Russian"), KeyboardButton("🇬🇧 English")]
    ],
    resize_keyboard=True
)

# Action selection keyboard
action_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📝 Register"), KeyboardButton("🔑 Login")],
        [KeyboardButton("❌ Cancel")]
    ],
    resize_keyboard=True
)

@dp.message_handler(commands=['start'])
async def command_start_handler(message: types.Message) -> None:
    await message.answer("Welcome! Please select your preferred language:", reply_markup=language_keyboard)

@dp.message_handler(lambda message: message.text in ["🇺🇿 Uzbek", "🇷🇺 Russian", "🇬🇧 English"])
async def language_selected_handler(message: types.Message) -> None:
    await message.answer("Great! Now choose an action:", reply_markup=action_keyboard)

@dp.message_handler(lambda message: message.text in ["📝 Register", "🔑 Login"])
async def action_selected_handler(message: types.Message) -> None:
    # Handle registration or login logic here
    await message.answer(f"You selected: {message.text}")

@dp.message_handler(lambda message: message.text == "❌ Cancel")
async def cancel_handler(message: types.Message) -> None:
    await message.answer("Operation canceled. Feel free to start again!")

async def main() -> None:
    bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
