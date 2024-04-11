import os
import re
import json
import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

with open('env.json', 'r') as d:
    env = json.load(d)
BOT_TOKEN = env['BOT-TOKEN']
ADMINS = env['ADMINS'].split(',')
BASE_URL = env['BASE_URL']

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

logging.basicConfig(level=logging.INFO)

with open("translations.json", "r", encoding='utf-8') as f:
    translations = json.load(f)
LANGUAGES = list(translations.keys())

class RegistrationForm(StatesGroup):
    name = State()
    phone_number = State()
    email = State()
    password1 = State()
    password2 = State()

class LoginForm(StatesGroup):
    email = State()
    password = State()

async def ask_language(message: types.Message):
    inline_kb = InlineKeyboardMarkup(row_width=3)
    inline_kb.add(
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data='lang_uz'),
        InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru'),
        InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')
    )

    await message.answer(
        ("Salom {first_name}.\nBu Donation bot.\nBotdan foydalanish tilini tanlang.\n\n"
         "Привет, {first_name}.\nЭто бот для пожертвований.\nВыберите язык для использования бота.\n\n"
         "Hello {first_name}.\nThis is a Donation bot.\nChoose the language to use the bot.").format(
            first_name=message.from_user.first_name
        ), reply_markup=inline_kb
    )

async def choice_Sign(user_id: int):
    url = f'{BASE_URL}/user/is_authenticated/{user_id}'
    response = requests.get(url)
    if response.status_code == 200 and response == True:
        await bot.send_message("Qanday xizmatdan foydalanasiz")
    else:
        await bot.send_message(
            user_id,
            "Please select an option:",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton("📝 Register")],
                    [types.KeyboardButton("Login")]
                ],
                resize_keyboard=True
            )
        )

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    logging.info(f'Command from user id: {message.from_user.id}: {message.text}')
    current_user = message.from_user.id
    url = f'{BASE_URL}/user/get_tg_user/{current_user}'
    response = requests.get(url)
    if response.status_code == 200:
        if response.json().get('is_auth') == True:
            pass
        else:
            await choice_Sign(message)
    else:
        await ask_language(message)

@dp.callback_query_handler(lambda query: query.data.startswith('lang_'))
async def select_language(query: types.CallbackQuery):
    tg_user_id = query.from_user.id
    lang = query.data.split('_')[1]
    data = {
        "tg_user_id": tg_user_id,
        "lang_code": lang,
        "is_auth": False,
    }
    headers = {'Content-Type': 'application/json'}
    url = f'{BASE_URL}/user/createTgUser/'
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        logging.info("User created successfully:", response.json())
        await choice_Sign(query.message.from_user.id)
    else:
        logging.info("Error creating user:")

#### REGISTER ####

@dp.message_handler(lambda message: message.text == "📝 Register")
async def start_registration(message: types.Message):
    await bot.send_message(message.from_user.id, "Please enter your name:")
    await RegistrationForm.name.set()

@dp.message_handler(state=RegistrationForm.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    # keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    # keyboard.add(KeyboardButton(text="Share contact", request_contact=True))
    # , reply_markup = keyboard
    await message.answer("Please share your phone number with us.")
    await RegistrationForm.phone_number.set()

@dp.message_handler(state=RegistrationForm.phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.contact:
            phone_number = message.contact.phone_number
        else:
            phone_number = message.text

        data['phone_number'] = phone_number

    logging.info("Phone number received: %s", phone_number)

    await message.answer("Please enter your email.")
    await RegistrationForm.email.set()


@dp.message_handler(state=RegistrationForm.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()

    # Email validation using a regular expression
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        await message.answer("Please enter a valid email address.")
        await RegistrationForm.email.set()
        return

    async with state.proxy() as data:
        data['email'] = email

    logging.info("Email received: %s", email)

    await message.answer("Please enter your password.")
    await RegistrationForm.password1.set()

@dp.message_handler(state=RegistrationForm.password1)
async def process_password1(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['password1'] = message.text

    await message.answer("Please confirm your password.")
    await RegistrationForm.password2.set()

@dp.message_handler(state=RegistrationForm.password2)
async def process_password2(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['password2'] = message.text

        if data['password1'] != data['password2']:
            await message.answer("Passwords do not match. Please try again.")
            await RegistrationForm.password1.set()
            return
        
        url = f'{BASE_URL}/user/createUser/'
        user = {
            "name": data['name'],
            "phone_number": data['phone_number'],
            "email": data['email'],
            "password": data['password1'],
            "user_id": message.from_user.id,
            "balance": 0
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=user, headers=headers)
        if response.status_code == 201:
            await bot.send_message(message.from_user.id, f'Your account has been created.')
            authenticate = requests.get(f'{BASE_URL}/user/authenticate/{message.from_user.id}')
            if authenticate.status_code == 200:
                await bot.send_message(message.from_user.id, f'Your account has been authenticated.')
            else:
                await bot.send_message(message.from_user.id, f'Please try again.')

    await message.answer("Registration successful!")
    await state.finish()

#### LOGIN ####
@dp.message_handler(lambda message: message.text == "Login")
async def start_login(message: types.Message):
    await bot.send_message(message.from_user.id, "Please enter your email:")
    await LoginForm.email.set()
    return

@dp.message_handler(state=LoginForm.email)
async def process_login_email(message: types.Message, state: FSMContext):
    email = message.text.strip()

    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        await message.answer("Please enter a valid email address.")
        return

    url = f'{BASE_URL}/user/checkEmail/'
    params = {"email": email}
    respone = requests.get(url, params=params)
    if respone.status_code == 404:
        await message.answer("Bunday email topilmadi. Qaytadan harakat qilib ko'ring:")
        await LoginForm.email.set()
        return

    async with state.proxy() as data:
        data['email'] = email

    logging.info("Email received for login: %s", email)

    await message.answer("Please enter your password.")
    await LoginForm.password.set()
    return

@dp.message_handler(state=LoginForm.password)
async def process_login_password(message: types.Message, state: FSMContext):
    password = message.text.strip()

    # Retrieve email from the FSM context
    async with state.proxy() as data:
        email = data.get('email')

    url = f'{BASE_URL}/user/checkPassword/'
    payload = {'email': email, 'password': password}
    response = requests.get(url, json=payload)

    if response.status_code == 200 and response.json():
        await message.answer("You have successfully logged in.")
        await state.finish()
        await send_main_menu()
        return
    else:
        await message.answer("Incorrect password. Please try again.")
        await LoginForm.password.set()

#### MAIN PAGE ####

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton("Shop"),
            KeyboardButton("Top up balance"),
        ],
        [
            KeyboardButton("Orders history"),
            KeyboardButton("Payments history"),
        ],
        [
            KeyboardButton("Profile"),
            KeyboardButton("Settings"),
        ]
    ],
    resize_keyboard=True
)

async def send_main_menu(user_id: int):
    await bot.send_message(user_id, "Please select an option:", reply_markup=main_menu_keyboard)

@dp.message_handler(lambda message: message.text == "Shop")
async def shop_function(message: types.Message):
    await message.answer("Shop function is not implemented yet.")

@dp.message_handler(lambda message: message.text == "Top up balance")
async def top_up_balance_function(message: types.Message):
    await message.answer("Top up balance function is not implemented yet.")

@dp.message_handler(lambda message: message.text == "Orders history")
async def orders_history_function(message: types.Message):
    await message.answer("Orders history function is not implemented yet.")

@dp.message_handler(lambda message: message.text == "Payments history")
async def payments_history_function(message: types.Message):
    await message.answer("Payments history function is not implemented yet.")

@dp.message_handler(lambda message: message.text == "Profile")
async def profile_function(message: types.Message):
    await message.answer("Profile function is not implemented yet.")

@dp.message_handler(lambda message: message.text == "Settings")
async def settings_function(message: types.Message):
    await message.answer("Settings function is not implemented yet.")


async def shutdown(dp):
    await dp.bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)