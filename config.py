import os
import re
import json
import logging
from datetime import datetime

import requests
from aiogram import Bot, Dispatcher, types
from aiogram import executor
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

with open('env.json', 'r') as d:
    env = json.load(d)
BOT_TOKEN = env['BOT-TOKEN']
ADMINS = env['ADMINS'].split(',')[0]
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

class PaymentForm(StatesGroup):
    card = State()
    amount = State()
    screenshot = State()

class AddAppStates(StatesGroup):
    name = State()
    photo = State()

class AddProductStates(StatesGroup):
    app = State()
    name = State()
    quantity = State()
    price = State()

class SingleDataForm(StatesGroup):
    id = State()
    text = State()

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
        # await dp.bot.set_chat_data(chat=query.message.chat.id, data={'lang_code': lang})
        await choice_Sign(query.message.from_user.id)
    else:
        logging.info("Error creating user:")


async def get_translation(user_id: int, event: str):
    url = f'{BASE_URL}/user/get_tg_user/{user_id}'
    response = requests.get(url)
    if response.status_code == 200:
        lang_code = response.json()['lang_code']
        return translations[lang_code][event]
    # lang_code = await dp.bot.get_chat_data(chat=user_id)['lang_code']

async def choice_Sign(user_id: int):
    url = f'{BASE_URL}/user/is_authenticated/{user_id}'
    response = requests.get(url)
    if response.status_code == 200 and response == True:
        await bot.send_message(user_id, "Qanday xizmatdan foydalanasiz")
        await send_main_menu(user_id)
    else:
        # reg_text = await get_translation(user_id, "register")
        # login_text = await get_translation(user_id, "login")
        # select_option = await get_translation(user_id, "select_option")
        await bot.send_message(
            user_id,
            "select_option",
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
            await send_main_menu(message.from_user.id)
        else:
            await choice_Sign(message.from_user.id)
    else:
        await ask_language(message)


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
    await send_main_menu(message.from_user.id)
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
        await send_main_menu(message.from_user.id)
        return
    else:
        await message.answer("Incorrect password. Please try again.")
        await LoginForm.password.set()

#### MAIN PAGE ####
async def send_main_menu(user_id: int):
    select_option = await get_translation(user_id, event="select_option")
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
    await bot.send_message(user_id, select_option, reply_markup=main_menu_keyboard)

@dp.message_handler(lambda message: message.text == "Shop")
async def shop_function(message: types.Message):
    user_id = message.from_user.id
    url = f'{BASE_URL}/app/'
    response = requests.get(url)
    apps = response.json()
    if response.status_code == 200 and apps:
        app_buttons = []

        for app in apps:
            app_button = InlineKeyboardButton(app['name'], callback_data=f"app_{app['id']}")
            app_buttons.append(app_button)

        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        inline_keyboard.add(*app_buttons)

        await bot.send_message(user_id, "Select an app to purchase:", reply_markup=inline_keyboard)
    else:
        await bot.send_message(user_id, "Failed to fetch app data. Please try again later.")

@dp.callback_query_handler(lambda query: query.data.startswith('app_'))
async def process_buy_app(callback_query: types.CallbackQuery):
    app_id = callback_query.data.split('_')[1]
    url1 = f'{BASE_URL}/products/{app_id}'
    response = requests.get(url1)
    products = response.json()

    keyboard = InlineKeyboardMarkup(row_width=1)
    for product in products:
        button_text = f"{product['quantity']} {product['name']} - {product['price']}"
        button_data = f"buy_product_{product['id']}"
        keyboard.add(InlineKeyboardButton(button_text, callback_data=button_data))
    url2 = f'{BASE_URL}/app/{app_id}'
    response = requests.get(url2)
    app_data = response.json()
    await bot.send_photo(callback_query.message.chat.id, app_data['app_pic'], caption=app_data['name'], reply_markup=keyboard)
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await callback_query.answer()

@dp.callback_query_handler(lambda query: query.data.startswith('buy_product_'))
async def process_buy_product(callback_query: types.CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split('_')[2])
    url = f'{BASE_URL}/product/{product_id}'
    response = requests.get(url)
    product_data = response.json()

    urlApp = f"{BASE_URL}/app/{product_data['app']}"
    response = requests.get(urlApp)
    app_data = response.json()

    tg_user_id = callback_query.from_user.id
    url0 = f'{BASE_URL}/user/get_user/{tg_user_id}'
    user = requests.get(url0).json()

    if user['balance'] >= float(product_data['price']):
        order_data = {
            "user": user['id'],
            "product": product_id,
            "is_completed": False,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f%z")
        }
        order_url = f"{BASE_URL}/order/create/"
        order_response = requests.post(order_url, json=order_data)

        if order_response.status_code == 201:
            order_id = order_response.json().get('id')
            await bot.answer_callback_query(callback_query.id, text=f"Order placed successfully for product ID {product_id}")
            new_order = (f"New order from {callback_query.from_user.username if callback_query.from_user.username else callback_query.from_user.first_name}\n\n"
                         f"App: {app_data['name']}\n"
                         f"Quantity: {product_data['quantity']} {product_data['name']}\n"
                         f"Price: {product_data['price']}")
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(InlineKeyboardButton("Done", callback_data=f"confirm_order_{order_id}"))
            keyboard.add(InlineKeyboardButton("Later", callback_data="button_data"))
            await bot.send_message(ADMINS, new_order, reply_markup=keyboard)
            await callback_query.answer()
        else:
            await bot.answer_callback_query(callback_query.id, text=f"Failed to place order for product ID {product_id}. Please try again later.")
    else:
        await bot.send_message(tg_user_id, "Balansingizda pul yetarli emas. Balansingizni to'ldirib qayradan urinib ko'rin")

@dp.callback_query_handler(lambda query: query.data.startswith('confirm_order_'))
async def confirm_order(callback_query: types.CallbackQuery):
    order_id = int(callback_query.data.split('_')[2])
    url = f'{BASE_URL}/order/complete/{order_id}'
    response = requests.get(url)
    if response.status_code == 200:
        user = response.json()['user']
        order = response.json()['order']
        order_data = f"{user['name']}, sizning {order['product']} buyurtmangiz bajarildi."
        await bot.send_message(user['user_id'], order_data)
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await bot.answer_callback_query(callback_query.id, text=f"Order {order_id} confirmed!")

#### Top up balance ####
@dp.message_handler(lambda message: message.text == "Top up balance")
async def top_up_balance_function(message: types.Message):
    url = f'{BASE_URL}/cards/'
    response = requests.get(url)
    cards = response.json()
    keyboard = InlineKeyboardMarkup()
    for card in cards:
        keyboard.add(InlineKeyboardButton(f"{card['name']}", callback_data=f"select_card_{card['id']}"))

    await message.answer("Please select a card:", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('select_card_'))
async def process_card_selection(query: types.CallbackQuery, state: FSMContext):
    card_id = query.data.split('_')[2]
    async with state.proxy() as data:
        data['card'] = card_id

    url = f'{BASE_URL}/cards/{card_id}'
    response = requests.get(url)
    if response.status_code == 200:
        card = response.json()
        await query.message.answer(f"Selected card: {card['number']}")
        await query.message.answer("Please enter the price:")
        await PaymentForm.amount.set()
    else:
        logging.info("Card not found")
@dp.message_handler(state=PaymentForm.amount)
async def process_amount(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['amount'] = message.text

    await message.answer("Please send a screenshot of the transaction:")
    await PaymentForm.screenshot.set()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=PaymentForm.screenshot)
async def process_screenshot(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['screenshot'] = message.photo[-1].file_id
        card_id = data['card']
        amount = data['amount']
        screenshot = data['screenshot']
    logging.info(message)
    tg_user_id = message.from_user.id
    payload = {
        'card_id': card_id,
        'price': amount,
        'cheque_pic': screenshot
    }
    payment_url = f'{BASE_URL}/payment/create/{tg_user_id}'
    response = requests.post(payment_url, json=payload)
    payment = response.json()
    if response.status_code == 201:
        await message.answer("Payment processed successfully!")
        new_payment = (
            f"New payment from {message.from_user.username if message.from_user.username else message.from_user.first_name}\n\n"
            f"Amount: {payment['price']}\n"
            f"Datetime: {payment['datetime']}\n"
            f"Which card: {payment['card_id']}")
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(InlineKeyboardButton("Accept", callback_data=f"confirm_payment_{payment['id']}"))
        keyboard.add(InlineKeyboardButton("Later", callback_data="button_data"))
        photo = payment['cheque_pic']
        await bot.send_photo(ADMINS, photo, caption=new_payment, reply_markup=keyboard)
    else:
        await message.answer("Failed to process payment. Please try again.")

    await state.finish()
@dp.callback_query_handler(lambda query: query.data.startswith('confirm_payment_'))
async def confirm_payment(callback_query: types.CallbackQuery):
    payment_id = int(callback_query.data.split('_')[2])
    url = f'{BASE_URL}/payment/accept/{payment_id}'
    response = requests.get(url)
    if response.status_code == 200:
        user = response.json()['user']
        payment = response.json()['payment']
        payment_data = f"{user['name']}, sizning {payment['price']} so'mlik to'lovingiz qabul qilindi va sizning joriy balansingiz\n{user['balance']} so'm"
        await bot.send_message(user['user_id'], payment_data)
    await bot.answer_callback_query(callback_query.id, text=f"Order {payment['id']} confirmed!")


@dp.message_handler(lambda message: message.text == "Orders history")
async def orders_history_function(message: types.Message):
    user_id = message.from_user.id
    url = f'{BASE_URL}/order/history/{user_id}'
    response = requests.get(url)
    if response.status_code == 200:
        orders = response.json()
        if orders:
            for order in orders:
                order_info = f"Date: {order['datetime']}, Price: {order['product']}, Quantity: {order['product']}"
                await bot.send_message(user_id, order_info)
            else:
                await bot.send_message(user_id, "No order history found.")
        else:
            await bot.send_message(user_id, "Failed to fetch payment history.")


@dp.message_handler(lambda message: message.text == "Payments history")
async def payments_history_function(message: types.Message):
    user_id = message.from_user.id
    url = f'{BASE_URL}/payment/history/{user_id}'
    response = requests.get(url)
    if response.status_code == 200:
        payments = response.json()
        if payments:
            for payment in payments:
                payment_info = f"Date: {payment['datetime']}, Amount: {payment['price']}"
                await bot.send_message(user_id, payment_info)
        else:
            await bot.send_message(user_id, "No payment history found.")
    else:
        await bot.send_message(user_id, "Failed to fetch payment history.")


#### PROFILE
@dp.message_handler(lambda message: message.text == "Profile")
async def profile_function(message: types.Message):
    user_id = message.from_user.id
    url = f'{BASE_URL}/user/get_user/{user_id}'
    response = requests.get(url)
    if response.status_code == 200:
        user = response.json()
        message_text = (f"👤 *User Profile* 👤\n\n"
                        f"Name: {user['name']}\n"
                        f"Phone Number: {user['phone_number']}\n"
                        f"Email: {user['email']}\n"
                        f"Balance: {user['balance']} So'm\n\n")
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton('Edit Profile', callback_data='profile_edit'))
        keyboard.add(types.InlineKeyboardButton('Settings', callback_data='settings'))
        await message.answer(message_text, reply_markup=keyboard)
    else:
        await message.answer("Error with server!")

@dp.callback_query_handler(lambda query: query.data == 'profile_edit')
async def edit_profile(callback_query: types.CallbackQuery):
    await callback_query.answer("You selected to edit your profile.")
    # Here you can implement the logic to handle the editing of the profile


#### SETTINGS ####
async def settings_(user_id: int):

    await bot.send_message(chat_id=user_id, text='settings     nbn')

@dp.callback_query_handler(lambda query: query.data == 'settings')
async def settings(callback_query: types.CallbackQuery):
    await settings_(callback_query.from_user.id)
@dp.message_handler(lambda message: message.text == "Settings")
async def settings_function(message: types.Message):
    await settings_(message.from_user.id)

#################################################################################
#### FOR ADMIN ####
@dp.message_handler(commands=['admin'], user_id=ADMINS)
async def admin_menu(message: types.Message):
    # Create the admin menu keyboard
    keyboard = types.ReplyKeyboardMarkup(row_width=2)
    keyboard.add(types.KeyboardButton("Orders"))
    keyboard.add(types.KeyboardButton("Payments"))
    keyboard.add(types.KeyboardButton("Main Configuration"))
    # keyboard.add(types.KeyboardButton("Orders"))
    # keyboard.add(types.KeyboardButton("Other Bot Settings"))

    await message.answer("Admin Menu:", reply_markup=keyboard)

@dp.message_handler(text="Orders", user_id=ADMINS)
async def OrdersAdmin(message: types.Message):
    await message.answer("App Settings are not implemented yet.")
@dp.message_handler(text="Payments", user_id=ADMINS)
async def PaymentsAdmin(message: types.Message):
    await message.answer("Product Settings are not implemented yet.")

@dp.message_handler(text="Main Configuration", user_id=ADMINS)
async def Congigurations(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(types.InlineKeyboardButton("Edit Apps", callback_data="appSettings"))
    keyboard.add(types.InlineKeyboardButton("Edit Products", callback_data="productSettings"))
    keyboard.add(types.InlineKeyboardButton("Edit Cards", callback_data="card_settings"))

    await message.answer("Choose option:", reply_markup=keyboard)
@dp.callback_query_handler(lambda query: query.data == 'appSettings', user_id=ADMINS)
async def appSettings(query: types.CallbackQuery):
    url = f'{BASE_URL}/app/'
    response = requests.get(url)
    apps = response.json()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for app in apps:
        keyboard.add(types.InlineKeyboardButton(app["name"], callback_data=f"edit_app_{app['id']}"))
    keyboard.add(types.InlineKeyboardButton("Add new app", callback_data="add_app"))
    await query.message.answer("Choose app or add app:", reply_markup=keyboard)
    await query.answer()
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
@dp.callback_query_handler(lambda query: query.data.startswith('edit_app_'), user_id=ADMINS)
async def edit_app(query: types.CallbackQuery):
    app_id = query.data.split('_')[-1]
    url = f'{BASE_URL}/app/{app_id}'
    response = requests.get(url)
    app = response.json()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("Edit name", callback_data=f"change_app_1_{app_id}"))
    keyboard.add(types.InlineKeyboardButton("Edit photo", callback_data=f"change_app_2_{app_id}"))
    keyboard.add(types.InlineKeyboardButton("Delete app", callback_data=f"change_app_3_{app_id}"))
    await bot.send_photo(query.from_user.id, app["app_pic"], caption=app['name'], reply_markup=keyboard)
    await query.answer(f"You selected to edit app with ID {app_id}.")

@dp.callback_query_handler(lambda query: query.data.startswith('change_app_'), user_id=ADMINS)
async def change_app(query: types.CallbackQuery):
    action_code, app_id = query.data.split('_')[-2:]
    url = f'{BASE_URL}/app/{app_id}'

    if action_code == '1':
        await query.message.answer('You selected to edit the name of the app.')
        await editAppName(app_id, query.from_user.id, FSMContext)
    elif action_code == '2':
        await query.answer("You selected to edit the photo of the app.")
        # Perform actions to change the photo of the app
    elif action_code == '3':
        response = requests.delete(url)
        if response.status_code == 204:
            await query.answer("App deleted successfully.")
        else:
            await query.answer("Failed to delete app.")
    else:
        await query.answer("Invalid action.")

@dp.callback_query_handler(lambda query: query.data == 'add_app', user_id=ADMINS)
async def add_app(query: types.CallbackQuery):
    await query.message.answer("Please enter the name of the new app.")
    await AddAppStates.name.set()

@dp.message_handler(state=AddAppStates.name, user_id=ADMINS)
async def add_app_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Please send the photo of the new app.")
    await AddAppStates.photo.set()
@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddAppStates.photo, user_id=ADMINS)
async def add_app_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photo'] = message.photo[-1].file_id
    new_app_data = {
        "name": data['name'],
        "app_pic": data['photo']
    }
    url = f'{BASE_URL}/app/'
    response = requests.post(url, json=new_app_data)
    app = response.json()
    if response.status_code == 201:
        await message.answer_photo(app['app_pic'], caption="New app: app['name']")
    else:
        await message.answer("Failed to add new app.")
    await state.finish()

@dp.callback_query_handler(state=SingleDataForm.id, user_id=ADMINS)
async def editAppName(appID: int, user_id, state: FSMContext ):
    async with state.proxy() as data:
        data['id'] = appID
    await bot.send_message(user_id, "App uchun yangi nom yuboring: ")
    await SingleDataForm.text.set()
@dp.message_handler(state=SingleDataForm.text, user_id=ADMINS)
async def edit_app_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    url = f"{BASE_URL}/app/{data['id']}"
    response = requests.put(url, json={"name": data["name"]})
    if response.status_code == 200:
        await message.answer("Name successfully updated.")
        return
    else:
        await message.answer("Error updating")
        return

# async def edit_app_name(query: types.CallbackQuery, app_id: str):
#     new_name = "New App Name"
#
#     data = {"name": new_name}
#     response = requests.patch(url, json=data)
#     if response.status_code == 200:
#         await query.answer("App name updated successfully.")
#     else:
#         await query.answer("Failed to update app name.")
#
# async def edit_app_photo(query: types.CallbackQuery, app_id: str):
#     new_photo = "new_photo.jpg"
#     url = f'{BASE_URL}/app/{app_id}'
#     data = {"app_pic": new_photo}
#     response = requests.patch(url, json=data)
#     if response.status_code == 200:
#         await query.answer("App photo updated successfully.")
#     else:
#         await query.answer("Failed to update app photo.")



@dp.callback_query_handler(lambda query: query.data == 'productSettings', user_id=ADMINS)
async def edit_products(query: types.CallbackQuery):
    url = f'{BASE_URL}/app/'
    response = requests.get(url)
    apps = response.json()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for app in apps:
        keyboard.add(types.InlineKeyboardButton(app["name"], callback_data=f"appProduct_{app['id']}"))
    await query.message.answer("Choose app for products:", reply_markup=keyboard)
    await query.answer()
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
@dp.callback_query_handler(lambda query: query.data.startswith('appProduct_'), user_id=ADMINS)
async def select_app_product(query: types.CallbackQuery):
    app_id = query.data.split('_')[-1]
    url1 = f'{BASE_URL}/products/{app_id}'
    response = requests.get(url1)
    products = response.json()
    keyboard = InlineKeyboardMarkup(row_width=1)
    for product in products:
        button_text = f"{product['quantity']} {product['name']} - {product['price']}"
        button_data = f"editProduct_{product['id']}"
        keyboard.add(InlineKeyboardButton(button_text, callback_data=button_data))
    keyboard.add(InlineKeyboardButton("Add Product", callback_data=f"addProduct_{app_id}"))
    url2 = f'{BASE_URL}/app/{app_id}'
    response = requests.get(url2)
    app_data = response.json()
    await bot.send_photo(query.message.chat.id,
                         app_data['app_pic'],
                         caption=app_data['name'],
                         reply_markup=keyboard)
    await query.answer(f"You selected app with ID {app_id} for products.")

@dp.callback_query_handler(lambda query: query.data.startswith('editProduct_'), user_id=ADMINS)
async def EditSelectedProduct(query: types.CallbackQuery):
    product_id = query.data.split('_')[-1]
    url = f'{BASE_URL}/products/{product_id}'
    response = requests.get(url)
    product = response.json()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("Edit name", callback_data=f"change_app_1_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Edit quantity", callback_data=f"change_app_2_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Edit price", callback_data=f"change_app_3_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Delete product", callback_data=f"change_app_4_{product_id}"))
    text = (f"Selected product: {product['name']} {product['quantity']}"
            f"Price: {product['price']}")
    await query.message.answer(text, reply_markup=keyboard)
    await query.answer(f"You selected to edit app with ID {product_id}.")

@dp.callback_query_handler(lambda query: query.data.startswith('change_app_'), user_id=ADMINS)
async def change_product(query: types.CallbackQuery):
    action_code, product_id = query.data.split('_')[-2:]
    url = f'{BASE_URL}/product/{product_id}'

    if action_code == '1':
        await query.message.answer('You selected to edit the name of the product.')
        await SingleDataForm.text.set()
    elif action_code == '2':
        await query.answer("You selected to edit the quantity of the product.")
        # Perform actions to change the quantity of the product
    elif action_code == '3':
        await query.answer("You selected to edit the price of the product.")
        # Perform actions to change the price of the product
    elif action_code == '4':
        response = requests.delete(url)
        if response.status_code == 204:
            await query.answer("Product deleted successfully.")
        else:
            await query.answer("Failed to delete product.")
    else:
        await query.answer("Invalid action.")

@dp.callback_query_handler(lambda query: query.data.startswith('change_app_1'), user_id=ADMINS)
async def edit_product_name(query: types.CallbackQuery):
    product_id = query.data.split('_')[-1]
    await query.message.answer('You selected to edit the name of the product.')
    # await editProductName(product_id, query.from_user.id)

@dp.callback_query_handler(lambda query: query.data.startswith('addProduct_'), user_id=ADMINS)
async def add_product(query: types.CallbackQuery, state: FSMContext):
    await AddProductStates.app.set()
    app_id = query.data.split('_')[-1]
    async with state.proxy() as data:
        data['app'] = app_id
    await query.message.answer("Please provide details for the new product.")
    await query.message.answer("Enter the name of the product:")
    await AddProductStates.name.set()

@dp.message_handler(state=AddProductStates.name, user_id=ADMINS)
async def add_product_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Please enter the quantity of the new product.")
    await AddProductStates.quantity.set()

@dp.message_handler(state=AddProductStates.quantity, user_id=ADMINS)
async def add_product_quantity(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quantity'] = int(message.text)
    await message.answer("Please enter the price of the new product.")
    await AddProductStates.price.set()

@dp.message_handler(state=AddProductStates.price, user_id=ADMINS)
async def add_product_price(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['price'] = float(message.text)
    product_data = {
        'app': data['app'],
        'name': data['name'],
        'quantity': data['quantity'],
        'price': data['price']
    }
    url = f'{BASE_URL}/product/'
    response = requests.post(url, json=product_data)
    if response.status_code == 201:
        await message.answer("New product added successfully.")
    else:
        await message.answer("Failed to add new product.")
    await state.finish()




@dp.callback_query_handler(lambda query: query.data == 'card_settings', user_id=ADMINS)
async def edit_cards(query: types.CallbackQuery):
    await query.answer()
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
    await query.message.answer("Edit Cards is not implemented yet.")



async def shutdown(dp):
    await dp.bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)