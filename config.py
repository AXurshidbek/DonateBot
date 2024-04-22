import os
import re
import json
import logging
from datetime import datetime
import requests
from aiogram import Bot, Dispatcher, types
from aiogram import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ParseMode, \
    callback_query
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

USER_LANG = requests.get(f'{BASE_URL}/user/all_user_lang/').json()
AUTHED_USERS = list(requests.get(f'{BASE_URL}/user/all_user_auth/').json())

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

class OrderForm(StatesGroup):
    gamer_id = State()
    product = State()

class AddAppStates(StatesGroup):
    name = State()
    photo = State()

class AddProductStates(StatesGroup):
    app = State()
    name = State()
    quantity = State()
    price = State()

class CardCreation(StatesGroup):
    Name = State()
    Number = State()
    TypeCard = State()
    Description = State()

class SingleDataAppForm(StatesGroup):
    id = State()
    text = State()
class SingleDataProductForm(StatesGroup):
    id = State()
    type = State()
    text = State()
class SingleDataCardForm(StatesGroup):
    id = State()
    type = State()
    text = State()

class PaginationForm(StatesGroup):
    json = State()
    index = State()

CANCEL_KEYBOARD = types.ReplyKeyboardMarkup(keyboard=[
                        [types.KeyboardButton("Cancel ❌")]],
                        resize_keyboard=True)
@dp.message_handler(lambda message: message.text == "Cancel ❌")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Operation canceled. Returning to the main menu.")
    await admin_menu(message)

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
    url = f'{BASE_URL}/user/createTgUser/'
    response = requests.post(url, json=data)
    if response.status_code == 201:
        logging.info("User created successfully:", response.json())
        USER_LANG[str(tg_user_id)] = lang
        await choice_Sign(query.from_user.id)
        await bot.delete_message(query.message.chat.id, query.message.message_id)
    else:
        logging.info("Error creating user:")

async def __(user_id: int, event: str):
    lang_code = USER_LANG[str(user_id)]
    return translations[lang_code][event]

async def choice_Sign(user_id: int):
    url = f'{BASE_URL}/user/is_authenticated/{user_id}'
    response = requests.get(url)
    if response.status_code == 200:
        if response.json() == True:
            await bot.send_message(user_id, "Qanday xizmatdan foydalanasiz")
            await send_main_menu(user_id)
        else:

            register = await __(user_id, "register")
            login = await __(user_id, "login")
            select_option = await __(user_id, "select_option")
            await bot.send_message(
                user_id,
                select_option,
                reply_markup=types.ReplyKeyboardMarkup(
                    keyboard=[
                        [types.KeyboardButton(register)],
                        [types.KeyboardButton(login)]
                    ],
                    resize_keyboard=True
                )
            )
    else:
        await bot.send_message(user_id, "Error with bot, try again later")

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
@dp.message_handler(lambda message: message.text in ["📝 Register", "📝 Зарегистрироваться", "📝 Roʻyxatdan oʻtish"])
async def start_registration(message: types.Message):
    ask_name = await __(message.from_user.id, "ask_name")
    await bot.send_message(message.from_user.id, ask_name)
    await RegistrationForm.name.set()

@dp.message_handler(state=RegistrationForm.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    share_contact = await __(message.from_user.id, "share_contact")
    keyboard.add(KeyboardButton(text=share_contact, request_contact=True))
    ask_phone = await __(message.from_user.id, "ask_phone")
    await message.answer(ask_phone, reply_markup=keyboard)
    await RegistrationForm.phone_number.set()

@dp.message_handler(state=RegistrationForm.phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    if message.contact:
        phone_number = message.contact.phone_number
    else:
        phone_number = message.text

    if not re.match(r'^\+[1-9]\d{1,14}$', phone_number):
        error_phone = await __(message.from_user.id, "error_phone")
        await message.answer(error_phone)
        return

    async with state.proxy() as data:
        data['phone_number'] = phone_number

    logging.info("Phone number received: %s", phone_number)
    ask_email = await __(message.from_user.id, "ask_email")
    await message.answer(ask_email, reply_markup=None)
    await RegistrationForm.email.set()


@dp.message_handler(state=RegistrationForm.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()

    # Email validation using a regular expression
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        error_email = await __(message.from_user.id, "error_email")
        await message.answer(error_email)
        await RegistrationForm.email.set()
        return

    async with state.proxy() as data:
        data['email'] = email

    logging.info("Email received: %s", email)
    ask_password = await __(message.from_user.id, "ask_password")
    await message.answer(ask_password)
    await RegistrationForm.password1.set()

@dp.message_handler(state=RegistrationForm.password1)
async def process_password1(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['password1'] = message.text
    confirm_password = await __(message.from_user.id, "confirm_password")
    await message.answer(confirm_password)
    await RegistrationForm.password2.set()

@dp.message_handler(state=RegistrationForm.password2)
async def process_password2(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['password2'] = message.text

    if data['password1'] != data['password2']:
        pass_error_match = await __(message.from_user.id, "error_password")
        await message.answer(pass_error_match)
        await RegistrationForm.password1.set()
        return

    url = f'{BASE_URL}/user/createUser/'
    user = {
        "name": data['name'],
        "phone_number": data['phone_number'],
        "email": data['email'],
        "password": data['password1'],
        "balance": 0
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=user, headers=headers)
    await state.finish()
    if response.status_code == 201:
        responseUser = response.json()
        creation_account = await __(message.from_user.id, "creation_account")
        conf_text = await bot.send_message(message.from_user.id, creation_account)
        authenticate = requests.get(f'{BASE_URL}/user/authenticate/{message.from_user.id}/{responseUser["id"]}')
        if authenticate.status_code == 200:
            AUTHED_USERS.append(message.from_user.id)
            success_auth = await __(message.from_user.id, "success_auth")
            await bot.edit_message_text(text=success_auth, chat_id=message.chat.id, message_id=conf_text.message_id)
            await send_main_menu(message.from_user.id)
            success_register = await __(message.from_user.id, "success_register")
            await bot.edit_message_text(text=success_register, chat_id=message.chat.id, message_id=conf_text.message_id)
            return
        else:
            fail_auth = await __(message.from_user.id, "fail_auth")
            await bot.edit_message_text(text=fail_auth, chat_id=message.chat.id, message_id=conf_text.message_id)
            await choice_Sign(message.from_user.id)
    else:
        fail_register = await __(message.from_user.id, "fail_register")
        await bot.send_message(message.from_user.id, fail_register)
        await choice_Sign(message.from_user.id)


#### LOGIN ####
@dp.message_handler(lambda message: message.text in ["🔑 Login", "🔑 Kirish", "🔑 Войти"])
async def start_login(message: types.Message):
    tg_user_id = message.from_user.id
    url = f'{BASE_URL}/user/is_authenticated/{tg_user_id}'
    response = requests.get(url)
    if response.status_code == 200:
        if response.json() == True:
            await bot.send_message(message.from_user.id, "You are now logged in.")
        else:
            ask_email = await __(message.from_user.id, "ask_email")
            await bot.send_message(message.from_user.id, ask_email)
            await LoginForm.email.set()
    else:
        logging.info(f'Error while logging in user: {message.from_user.id}')
    return

@dp.message_handler(state=LoginForm.email)
async def process_login_email(message: types.Message, state: FSMContext):
    email = message.text.strip()

    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        email_format_error = await __(message.from_user.id, "email_format_error")
        await message.answer(email_format_error)
        return

    url = f'{BASE_URL}/user/checkEmail/'
    params = {"email": email}
    respone = requests.get(url, params=params)
    if respone.status_code == 404:
        email_not_found = await __(message.from_user.id, "email_not_found")
        await message.answer(email_not_found)
        await LoginForm.email.set()
        return

    async with state.proxy() as data:
        data['email'] = email

    logging.info("Email received for login: %s", email)
    enter_password = await __(message.from_user.id, "enter_password")
    await message.answer(enter_password)
    await LoginForm.password.set()
    return

@dp.message_handler(state=LoginForm.password)
async def process_login_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    async with state.proxy() as data:
        email = data.get('email')
    url = f'{BASE_URL}/user/checkPassword/'
    payload = {'email': email, 'password': password, 'tg_user_id': message.from_user.id}
    response = requests.get(url, json=payload)
    if response.status_code == 200 and response.json():
        logged_in = await __(message.from_user.id, "logged_in")
        await message.answer(logged_in)
        await state.finish()
        await send_main_menu(message.from_user.id)
        return
    else:
        incorrect_password = await __(message.from_user.id, "incorrect_password")
        await message.answer(incorrect_password)
        await LoginForm.password.set()

#### MAIN PAGE ####
async def send_main_menu(user_id: int):
    select_option = await __(user_id, event="select_option")
    shop = await __(user_id, "shop")
    top_up_balance = await __(user_id, "top_up_balance")
    orders_history = await __(user_id, "orders_history")
    payments_history = await __(user_id, "payments_history")
    profile = await __(user_id, "profile")
    settings = await __(user_id, "settings")
    main_menu_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(shop),
                KeyboardButton(top_up_balance),
            ],
            [
                KeyboardButton(orders_history),
                KeyboardButton(payments_history),
            ],
            [
                KeyboardButton(profile),
                KeyboardButton(settings),
            ]
        ],
        resize_keyboard=True
    )
    await bot.send_message(user_id, select_option, reply_markup=main_menu_keyboard)

@dp.message_handler(lambda message: message.text in ["Shop 🛒"])
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
        shop_select = await __(user_id, "shop_select")
        await bot.send_message(user_id, shop_select, reply_markup=inline_keyboard)
    else:
        error_app = await __(message.from_user.id, "error_app")
        await bot.send_message(user_id, error_app)

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
    photo = app_data["app_pic"]
    await bot.send_photo(callback_query.from_user.id, photo, caption=app_data['name'], reply_markup=keyboard)
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await callback_query.answer()

@dp.callback_query_handler(lambda query: query.data.startswith('buy_product_'))
async def process_buy_product(callback_query: types.CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split('_')[2])
    await OrderForm.product.set()
    async with state.proxy() as data:
        data['product'] = product_id
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    gamer_id = await __(callback_query.from_user.id, "gamer_id")
    await callback_query.message.answer(gamer_id)
    await OrderForm.gamer_id.set()

@dp.message_handler(state=OrderForm.gamer_id)
async def process_gamer_id(message: types.Message, state: FSMContext):
    gamer_id = message.text
    async with state.proxy() as data:
        data['gamer_id'] = gamer_id
        product_id = data['product']
    await state.finish()
    url = f'{BASE_URL}/product/{product_id}'
    response = requests.get(url)
    product_data = response.json()

    urlApp = f"{BASE_URL}/app/{product_data['app']}"
    response = requests.get(urlApp)
    app_data = response.json()

    tg_user_id = message.from_user.id
    url0 = f'{BASE_URL}/user/get_user/{tg_user_id}'
    user = requests.get(url0).json()
    if user['balance'] >= float(product_data['price']):
        order_data = {
            "user": user['id'],
            "gamer_id": gamer_id,
            "product": product_id,
            "is_completed": False,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f%z")
        }
        order_url = f"{BASE_URL}/order/create/"
        order_response = requests.post(order_url, json=order_data)
        order_data = order_response.json()
        if order_response.status_code == 201:
            order_id = order_data.get('id')
            order_success = await __(message.from_user.id, "order_success")
            await message.answer(f"{order_success} {product_data['name']} {product_data['quantity']}")
            new_order = (f"Foydalanuvchi {message.from_user.username if message.from_user.username else message.from_user.first_name} dan yangi buyurtma\n\n"
                         f"Ilova: {app_data['name']}\n"
                         f"O'yinchi ID: {order_data['gamer_id']}\n"
                         f"Miqdori: {product_data['quantity']} {product_data['name']}\n"
                         f"Narxi: {product_data['price']}")
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(InlineKeyboardButton("Bajarildi", callback_data=f"confirm_order_{order_id}"))
            keyboard.add(InlineKeyboardButton("Keyinroq", callback_data="button_data"))
            await bot.send_message(ADMINS, new_order, reply_markup=keyboard)
        else:
            order_fail = await __(message.from_user.id, "order_fail")
            await message.answer(f"{order_fail} {product_data['name']} {product_data['quantity']}")
    else:
        lack_of_balance = await __(callback_query.from_user.id, "lack_of_balance")
        await bot.send_message(tg_user_id, lack_of_balance)
    return

@dp.callback_query_handler(lambda query: query.data.startswith('confirm_order_'))
async def confirm_order(callback_query: types.CallbackQuery):
    order_id = int(callback_query.data.split('_')[2])
    url = f'{BASE_URL}/order/complete/{order_id}'
    response = requests.get(url)
    if response.status_code == 200:
        user = response.json()['user']
        order = response.json()['order']
        tg_user_id = response.json()['tg_user_id']
        url1 = f'{BASE_URL}/product/{order["product"]}'
        response = requests.get(url1)
        product_data = response.json()
        order_done = await __(tg_user_id, "order_done")
        order_data = f"{user['name']} {order_done} {order['gamer_id']}"
        await bot.send_message(tg_user_id, order_data)
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await bot.answer_callback_query(callback_query.id, text=None)

#### Top up balance ####
@dp.message_handler(lambda message: message.text in ["Top up balance 💵"])
async def top_up_balance_function(message: types.Message):
    url = f'{BASE_URL}/cards/'
    response = requests.get(url)
    cards = response.json()
    keyboard = InlineKeyboardMarkup()
    for card in cards:
        keyboard.add(InlineKeyboardButton(f"{card['name']}", callback_data=f"select_card_{card['id']}"))
    ask_card = await __(message.from_user.id, "ask_card")
    await message.answer(ask_card, reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('select_card_'))
async def process_card_selection(query: types.CallbackQuery, state: FSMContext):
    await bot.delete_message(query.message.chat.id, query.message.message_id)
    card_id = query.data.split('_')[2]
    async with state.proxy() as data:
        data['card'] = card_id

    url = f'{BASE_URL}/cards/{card_id}'
    response = requests.get(url)
    if response.status_code == 200:
        card = response.json()
        selected_card = await __(query.from_user.id, "selected_card")
        await query.message.answer(f"{selected_card}",
                                   parse_mode='Markdown')
        await PaymentForm.amount.set()
    else:
        logging.info("Card not found")
@dp.message_handler(state=PaymentForm.amount)
async def process_amount(message: types.Message, state: FSMContext):
    if message.text.isalnum():
        async with state.proxy() as data:
            data['amount'] = message.text
    else:
        await message.answer("Please enter a valid amount.")
        await PaymentForm.amount.set()
        return
    screenshot_for_pay = await __(message.from_user.id, "screenshot_for_pay")
    await message.answer(screenshot_for_pay)
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
    user = requests.get(f'{BASE_URL}/user/get_user/{tg_user_id}').json()['id']
    payload = {
        'user': user,
        'card_id': card_id,
        'price': amount,
        'cheque_pic': screenshot
    }
    payment_url = f'{BASE_URL}/payment/create/'
    response = requests.post(payment_url, json=payload)
    payment = response.json()
    if response.status_code == 201:
        completed_payment = await __(message.from_user.id, "payment_complete")
        await message.answer(completed_payment)
        new_payment = (
            f"Foydalanuvchi {message.from_user.username if message.from_user.username else message.from_user.first_name} dan yangi to'lov\n\n"
            f"Miqdori: {payment['price']}\n"
            f"Vaqti: {payment['datetime']}\n"
            f"Card: {payment['card_id']}")
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(InlineKeyboardButton("Qabul qilish", callback_data=f"confirm_payment_{payment['id']}"))
        keyboard.add(InlineKeyboardButton("Keyinroq", callback_data="button_data"))
        photo = payment['cheque_pic']
        await bot.send_photo(ADMINS, photo, caption=new_payment, reply_markup=keyboard)
    else:
        fail_payment = await __(message.from_user.id, "payment_fail")
        await message.answer(fail_payment)
    await state.finish()
@dp.callback_query_handler(lambda query: query.data.startswith('confirm_payment_'))
async def confirm_payment(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    payment_id = int(callback_query.data.split('_')[2])
    url = f'{BASE_URL}/payment/accept/{payment_id}'
    response = requests.get(url)
    if response.status_code == 200:
        user = response.json()['user']
        tg_user_id = response.json()['tg_user_id']
        payment = response.json()['payment']
        confirmed_payment = await __(callback_query.from_user.id, "payment_confirmed")
        payment_data = f"{confirmed_payment}"
        await bot.send_message(tg_user_id, payment_data)
    await bot.answer_callback_query(callback_query.id, text=None)


################## ORDER ###########################
@dp.message_handler(lambda message: message.text == "Orders history")
async def orders_history_function(message: types.Message):
    user_id = message.from_user.id
    url = f'{BASE_URL}/order/list/?owner_by={user_id}'
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
        await bot.send_message(user_id, "Failed to fetch order history.")


# @dp.message_handler(lambda message: message.text == "Payments history")
# async def payments_history_function(message: types.Message):
#     user_id = message.from_user.id
#     url = f'{BASE_URL}/payment/list/?owner_by={user_id}'
#     response = requests.get(url)
#     if response.status_code == 200:
#         payments = response.json()
#         if payments:
#             grouped_payments = {}
#             for payment in payments:
#                 payment_datetime = datetime.strptime(payment['datetime'], "%Y-%m-%dT%H:%M:%S.%f%z")
#                 date_str = payment_datetime.strftime("%Y-%m-%d")
#                 time_str = payment_datetime.strftime("%H:%M")
#                 if payment["is_accepted"] is False and payment["is_rejected"] is False:
#                     status = "⏳"
#                 elif payment["is_accepted"] is True and payment["is_rejected"] is False:
#                     status = "✅"
#                 elif payment["is_accepted"] is False and payment["is_rejected"] is True:
#                     status = "❌"
#                 payment_info = f"{time_str} - $: {payment['price']}"
#                 if date_str not in grouped_payments:
#                     grouped_payments[date_str] = []
#                 payment_info += " | " + status
#                 grouped_payments[date_str].append(payment_info)
#
#             for date, payments_info in grouped_payments.items():
#                 payments_message = f"{date}:\n"
#                 payments_message += "\n".join(payments_info)
#                 await bot.send_message(user_id, payments_message)
#         else:
#             await bot.send_message(user_id, "No payment history found.")
#     else:
#         await bot.send_message(user_id, "Failed to fetch payment history.")

@dp.message_handler(lambda message: message.text == "Payments history")
async def payments_history_function(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    url = f'{BASE_URL}/payment/list/?owner_by={user_id}'
    response = requests.get(url)
    if response.status_code == 200:
        payments = response.json()
        async with state.proxy() as data:
            data['json'] = payments
            data['index'] = 0
        if payments:
            text =""
            numb = 0
            buttons = []
            for i in range(data['index'], len(payments)%10):
                payment = data['json'][i]
                payment_datetime = datetime.strptime(payment['datetime'], "%Y-%m-%dT%H:%M:%S.%f%z")
                date_str = payment_datetime.strftime("%Y-%m-%d")
                time_str = payment_datetime.strftime("%H:%M")
                text += f"{numb+1}. {date_str}  {time_str} - {get_payment_status(payment)} {payment['price']}\n"
                buttons.append(InlineKeyboardButton(text=str(numb+1), callback_data=f"callPaymentInfo_{payment['id']}"))
                numb += 1
            keyboard = InlineKeyboardMarkup(row_width=5)
            keyboard.add(*buttons)
            mbuttons = []
            mbuttons.append(InlineKeyboardButton(text="⬅️", callback_data="pagination_0"))
            mbuttons.append(InlineKeyboardButton(text="❌", callback_data="pagination_1"))
            mbuttons.append(InlineKeyboardButton(text="➡️", callback_data="pagination_2"))
            keyboard.add(*mbuttons)
            await message.answer(f"{data['index']+1}-{numb} to'lovlar {len(payments)} dan\n\n{text}", reply_markup=keyboard)
        else:
            await bot.send_message(user_id, "No payment history found.")
    else:
        await bot.send_message(user_id, "Failed to fetch payment history.")



def get_payment_status(payment):
    if payment["is_accepted"]:
        return "✅"
    elif payment["is_rejected"]:
        return "❌"
    else:
        return "⏳"
@dp.callback_query_handler(lambda query: query.data.startswith('pagination_'))
async def handle_pagination_callback(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data.get('index', 0)
    total_payments = len(data.get('json', []))

    if query.data == 'pagination_0':
        index = max(index - 10, 0)
    elif query.data == 'pagination_1':
        await bot.delete_message(query.message.chat.id, query.message.message_id)
    elif query.data == 'pagination_2':
        index = min(index + 10, total_payments - 1)
    async with state.proxy() as data:
        data['index'] = index

    await query.answer()
    await payments_history_function(query.message, state)

############################################################

@dp.callback_query_handler(lambda query: query.data.startswith('payment_page_'))
async def handle_payment_pagination(query: types.CallbackQuery):
    user_id = query.from_user.id
    page_number = int(query.data.split('_')[-1])

    url = f'{BASE_URL}/payment/history/{user_id}'
    response = requests.get(url)
    if response.status_code == 200:
        payments = response.json()
        if payments:
            chunked_payments = [payments[i:i + 10] for i in range(0, len(payments), 10)]
            total_pages = len(chunked_payments)
            if 1 <= page_number <= total_pages:
                payment_info = ""
                for payment in chunked_payments[page_number - 1]:
                    payment_info += f"Date: {payment['datetime']}, Amount: {payment['price']}\n"
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                if total_pages > 1:
                    if page_number > 1:
                        keyboard.add(types.InlineKeyboardButton("Previous", callback_data=f"payment_page_{page_number - 1}"))
                    if page_number < total_pages:
                        keyboard.add(types.InlineKeyboardButton("Next", callback_data=f"payment_page_{page_number + 1}"))
                await query.message.edit_text(payment_info, reply_markup=keyboard)
            else:
                await query.answer("Invalid page number.", show_alert=True)
        else:
            await query.answer("No payment history found.")
    else:
        await query.answer("Failed to fetch payment history.")


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
        keyboard.add(types.InlineKeyboardButton('Logout', callback_data='logout'))
        await message.answer(message_text, reply_markup=keyboard)
    else:
        await message.answer("Error with server!")

@dp.callback_query_handler(lambda query: query.data == 'profile_edit')
async def edit_profile(callback_query: types.CallbackQuery):
    await callback_query.answer("You selected to edit your profile.")
    # Here you can implement the logic to handle the editing of the profile
@dp.callback_query_handler(lambda query: query.data == 'logout')
async def edit_profile(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    keyboad = types.InlineKeyboardMarkup(row_width=1)
    keyboad.add(types.InlineKeyboardButton('Yes', callback_data='logoutConfirm_yes'))
    keyboad.add(types.InlineKeyboardButton('No', callback_data='LogoutConfirm_no'))
    await callback_query.message.answer("Are you sure to logout?", reply_markup=keyboad)

@dp.callback_query_handler(lambda query: query.data.startswith('logoutConfirm_'))
async def logout_confirm(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    answer = callback_query.data.split('_')[-1]
    user_id = callback_query.from_user.id
    url = f'{BASE_URL}/user/deauthenticate/{user_id}'
    if answer == 'yes':
        response = requests.get(url)
        if response.status_code == 200:
            is_true = response.json()
            if not is_true:
                await callback_query.message.answer("Logged out successfully.")
                await choice_Sign(callback_query.from_user.id)
                return
    else:
        await callback_query.message.answer("Profildan chiqilmadi.")




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
    keyboard.add(types.KeyboardButton("Buyurtmalar"))
    keyboard.add(types.KeyboardButton("To'lovlar"))
    keyboard.add(types.KeyboardButton("Bot sozlamalari"))

    await message.answer("Admin Menu:", reply_markup=keyboard)

@dp.message_handler(text="Buyurtmalar", user_id=ADMINS)
async def OrdersAdmin(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Bajarilmagan buyurtmalar", callback_data="sortOrder_0"))
    keyboard.add(types.InlineKeyboardButton("Qabul qilingan buyurtmalar", callback_data="sortOrder_1"))
    keyboard.add(types.InlineKeyboardButton("Rad etilgan buyurtmalar", callback_data="sortOrder_2"))
    await message.edit_text("Buyurtma turini tanlang:", reply_markup=keyboard)
@dp.callback_query_handler(lambda query: query.data.startswith('sortOrder_'), user_id=ADMINS)
async def handle_sort_order(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    sorting_option = int(callback_query.data.split('_')[-1])
    url = f"{BASE_URL}/order/list/"
    if sorting_option == 0:
        response = requests.get(url+"?filter_by=requests")
        if response.status_code == 200:
            orders = response.json()
            apps = requests.get(f'{BASE_URL}/app/').json()
            products = requests.get(f'{BASE_URL}/product').json()
            for order in orders:
                product = next((p for p in products if p['id'] == order['product']), None)
                app = next((p for p in apps if p['id'] == product["app"]), None)
                order_text= (
                    f"Buyurtma egasi: {callback_query.from_user.username if callback_query.from_user.username else callback_query.from_user.first_name}\n\n"
                    f"Ilova: {app['name']}\n"
                    f"O'yinchi ID: {order['gamer_id']}\n"
                    f"Miqdori: {product['quantity']} {product['name']}\n"
                    f"Narxi: {product['price']}")
                keyboard = InlineKeyboardMarkup(row_width=2)
                keyboard.add(InlineKeyboardButton("Bajarildi", callback_data=f"confirm_order_{order['id']}"))
                keyboard.add(InlineKeyboardButton("Keyinroq", callback_data="button_data"))
                await bot.send_message(ADMINS, order_text, reply_markup=keyboard)
    elif sorting_option == 1:
        response = requests.get(url + "?filter_by=done")
        if response.status_code == 200:
            orders = response.json()
            apps = requests.get(f'{BASE_URL}/app/').json()
            products = requests.get(f'{BASE_URL}/product').json()
            for order in orders:
                product = next((p for p in products if p['id'] == order['product']), None)
                app = next((p for p in apps if p['id'] == product["app"]), None)
                order_text= (
                    f"Buyurtma egasi: {callback_query.from_user.username if callback_query.from_user.username else callback_query.from_user.first_name}\n\n"
                    f"Ilova: {app['name']}\n"
                    f"O'yinchi ID: {order['gamer_id']}\n"
                    f"Miqdori: {product['quantity']} {product['name']}\n"
                    f"Narxi: {product['price']}")
                keyboard = InlineKeyboardMarkup(row_width=2)
                keyboard.add(InlineKeyboardButton("Bajarildi", callback_data=f"confirm_order_{order['id']}"))
                keyboard.add(InlineKeyboardButton("Keyinroq", callback_data="button_data"))
                await bot.send_message(ADMINS, order_text, reply_markup=keyboard)
    elif sorting_option == 2:
        response = requests.get(url + "?filter_by=rejected")
        if response.status_code == 200:
            orders = response.json()
            apps = requests.get(f'{BASE_URL}/app/').json()
            products = requests.get(f'{BASE_URL}/product').json()
            for order in orders:
                product = next((p for p in products if p['id'] == order['product']), None)
                app = next((p for p in apps if p['id'] == product["app"]), None)
                order_text= (
                    f"Buyurtma egasi: {callback_query.from_user.username if callback_query.from_user.username else callback_query.from_user.first_name}\n\n"
                    f"Ilova: {app['name']}\n"
                    f"O'yinchi ID: {order['gamer_id']}\n"
                    f"Miqdori: {product['quantity']} {product['name']}\n"
                    f"Narxi: {product['price']}")
                keyboard = InlineKeyboardMarkup(row_width=2)
                keyboard.add(InlineKeyboardButton("Bajarildi", callback_data=f"confirm_order_{order['id']}"))
                keyboard.add(InlineKeyboardButton("Keyinroq", callback_data="button_data"))
                await bot.send_message(ADMINS, order_text, reply_markup=keyboard)

    await callback_query.answer(f"Sorting option selected: {sorting_option}")

##### TO'LOVLAR

@dp.message_handler(text="To'lovlar", user_id=ADMINS)
async def PaymentsAdmin(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Tekshirilmagan to'lovlar", callback_data="sortPayment_0"))
    keyboard.add(types.InlineKeyboardButton("Tasdiqlangan to'lovlar", callback_data="sortPayment_1"))
    keyboard.add(types.InlineKeyboardButton("Rad etilgan to'lovlar", callback_data="sortPayment_2"))
    await message.answer("To'lov turini tanlang:", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('sortPayment_'), user_id=ADMINS)
async def handle_payment_sort_order(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    sorting_option = int(callback_query.data.split('_')[-1])
    url = f"{BASE_URL}/payment/list/"
    if sorting_option == 0:
        response = requests.get(url + "?filter_by=requests/")
        if response.status_code == 200:
            payments = response.json()
            if payments:
                grouped_payments = {}
                for payment in payments:
                    payment_datetime = datetime.strptime(payment['datetime'], "%Y-%m-%dT%H:%M:%S.%f%z")
                    date_str = payment_datetime.strftime("%Y-%m-%d")
                    time_str = payment_datetime.strftime("%H:%M")
                    if payment["is_accepted"] is False and payment["is_rejected"] is False:
                        status = "⏳"
                    elif payment["is_accepted"] is True and payment["is_rejected"] is False:
                        status = "✅"
                    elif payment["is_accepted"] is False and payment["is_rejected"] is True:
                        status = "❌"
                    payment_info = f"{time_str} - $: {payment['price']}"
                    if date_str not in grouped_payments:
                        grouped_payments[date_str] = []
                    payment_info += " | " + status
                    grouped_payments[date_str].append(payment_info)

                for date, payments_info in grouped_payments.items():
                    payments_message = f"{date}:\n"
                    payments_message += "\n".join(payments_info)
                    await callback_query.message.answer(payments_message)
            else:
                await callback_query.message.answer("No payment history found.")
    elif sorting_option == 1:
        response = requests.get(url + "?filter_by=done/")
        if response.status_code == 200:
            payments = response.json()
            if payments:
                grouped_payments = {}
                for payment in payments:
                    payment_datetime = datetime.strptime(payment['datetime'], "%Y-%m-%dT%H:%M:%S.%f%z")
                    date_str = payment_datetime.strftime("%Y-%m-%d")
                    time_str = payment_datetime.strftime("%H:%M")
                    payment_info = f"{time_str} - $: {payment['price']}"
                    if date_str not in grouped_payments:
                        grouped_payments[date_str] = []
                    grouped_payments[date_str].append(payment_info)

                for date, payments_info in grouped_payments.items():
                    payments_message = f"{date}:\n"
                    payments_message += "\n".join(payments_info)
                    await callback_query.message.answer(payments_message)
            else:
                await callback_query.message.answer("No payment history found.")

    await callback_query.answer(f"Sorting option selected: {sorting_option}")


############# CONFIGURATION
@dp.message_handler(text="Bot sozlamalari", user_id=ADMINS)
async def Congigurations(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(types.InlineKeyboardButton("Ilovalar", callback_data="appSettings"))
    keyboard.add(types.InlineKeyboardButton("Mahsulotlar", callback_data="productSettings"))
    keyboard.add(types.InlineKeyboardButton("Kartalar", callback_data="card_settings"))

    await message.answer("Kerakli bo'limni tanlang🔢:", reply_markup=keyboard)
@dp.callback_query_handler(lambda query: query.data == 'appSettings', user_id=ADMINS)
async def appSettings(query: types.CallbackQuery):
    url = f'{BASE_URL}/app/'
    response = requests.get(url)
    apps = response.json()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for app in apps:
        keyboard.add(types.InlineKeyboardButton(app["name"], callback_data=f"edit_app_{app['id']}"))
    keyboard.add(types.InlineKeyboardButton("Yangi ilova🆕", callback_data="add_app"))
    await query.message.edit_text("Ilovani tanlang yoki yarating📲:", reply_markup=keyboard)
    await query.answer()

############## ADD NEW APP #########################
@dp.callback_query_handler(lambda query: query.data == 'add_app', user_id=ADMINS)
async def add_app(query: types.CallbackQuery):
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
    await query.message.answer("Yangi ilova uchun nom kiriting🏷:")
    await AddAppStates.name.set()
@dp.message_handler(state=AddAppStates.name, user_id=ADMINS)
async def add_app_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Ilova uchun rasm yuboring 🖼:")
    await AddAppStates.photo.set()
@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddAppStates.photo, user_id=ADMINS)
async def add_app_photo(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
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
        await message.answer_photo(app['app_pic'], caption=f"Yangi ilova: {app['name']}")
    else:
        await message.answer("Ilova yaratishda xatolik.")
    await state.finish()


################# EDIT APP #######################
@dp.callback_query_handler(lambda query: query.data.startswith('edit_app_'), user_id=ADMINS)
async def edit_app(query: types.CallbackQuery):
    await bot.delete_message(query.message.chat.id, query.message.message_id)
    app_id = query.data.split('_')[-1]
    url = f'{BASE_URL}/app/{app_id}'
    response = requests.get(url)
    app = response.json()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("Mahsulot", callback_data=f"appProduct_{app_id}"))
    keyboard.add(types.InlineKeyboardButton("Nomni tahrirlash 📝", callback_data=f"editAPPname_{app_id}"))
    keyboard.add(types.InlineKeyboardButton("Rasmni tahrirlash 🖼", callback_data=f"editAPPphoto_{app_id}"))
    keyboard.add(types.InlineKeyboardButton("Ilovani o'chirish ❌", callback_data=f"deleteAPP_{app_id}"))
    photo = app["app_pic"]
    await bot.send_photo(query.from_user.id, photo=photo, caption=app['name'], reply_markup=keyboard)
    await query.answer()

######## DELETE APP
@dp.callback_query_handler(lambda query: query.data.startswith('deleteAPP_'), user_id=ADMINS)
async def deleteAPPyesno(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    app_id = callback_query.data.split('_')[-1]
    keyboad = types.InlineKeyboardMarkup(row_width=1)
    keyboad.add(types.InlineKeyboardButton('Ha', callback_data=f'deleteAPPConfirm_{1}_{app_id}'))
    keyboad.add(types.InlineKeyboardButton('Yo`q', callback_data=f'deleteAPPConfirm_{0}_{app_id}'))
    await callback_query.message.answer("Ilovani rostdan o'chirmoqchimisiz ❌?", reply_markup=keyboad)
@dp.callback_query_handler(lambda query: query.data.startswith('deleteAPPConfirm_'))
async def deleteAPPconfirm(callback_query: types.CallbackQuery):
    confirmation, app_id = callback_query.data.split('_')[-2:]
    if confirmation == "1":
        url = f'{BASE_URL}/app/{app_id}'
        response = requests.delete(url)
        if response.status_code == 204:
            await callback_query.message.edit_text("Ilova muvaffaqqiyatli o'chirildi.", reply_markup=None)
        else:
            await callback_query.message.edit_text("Ilovani o'chirishda xatolik.", reply_markup=None)
    else:
        await callback_query.message.edit_text("Ilovani o'chirish bekor qilindi.", reply_markup=None)

##### EDIT NAME
@dp.callback_query_handler(lambda query: query.data.startswith('editAPPname_'), user_id=ADMINS)
async def editAPPname(callback_query: types.CallbackQuery, state: FSMContext):
    app_id = callback_query.data.split('_')[-1]
    async with state.proxy() as data:
        data['id'] = app_id
    await callback_query.message.edit_text("Iltimos, ilova uchun yangi nom kiriting ✏️:")
    await SingleDataAppForm.text.set()

@dp.message_handler(state=SingleDataAppForm.text, user_id=ADMINS)
async def get_app_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    url = f"{BASE_URL}/app/{data['id']}/"
    response = requests.patch(url, json={"name": data["text"]})
    await state.finish()
    if response.status_code == 200:
        await message.answer("Ilova nomi muvaffaqqiyatli yangilandi ✅.")
    else:
        await message.answer("Ilova nomi yangilanmadi❗️.")

##### EDIT PHOTO
@dp.callback_query_handler(lambda query: query.data.startswith('editAPPphoto_'), user_id=ADMINS)
async def editAPPphoto(callback_query: types.CallbackQuery, state: FSMContext):
    app_id = callback_query.data.split('_')[-1]
    async with state.proxy() as data:
        data['id'] = app_id
    await callback_query.message.edit_text("Iltimos, ilova uchun yangi rasm yuboring 🖼:")
    await SingleDataAppForm.text.set()
@dp.message_handler(state=SingleDataAppForm.text, content_types=types.ContentType.PHOTO, user_id=ADMINS)
async def get_app_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.photo[-1].file_id
    url = f"{BASE_URL}/app/{data['id']}/"
    response = requests.patch(url, json={"app_pic": data["text"]})
    await state.finish()
    if response.status_code == 200:
        await message.answer("Ilova rasmi muvaffaqqiyatli yangilandi ✅.")
    else:
        await message.answer("Rasm yangilanmadi❗️.")



############ EDIT PRODUCT ##################
@dp.callback_query_handler(lambda query: query.data == 'productSettings', user_id=ADMINS)
async def edit_products(query: types.CallbackQuery):
    url = f'{BASE_URL}/app/'
    response = requests.get(url)
    apps = response.json()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for app in apps:
        keyboard.add(types.InlineKeyboardButton(app["name"], callback_data=f"appProduct_{app['id']}"))
    await query.message.edit_text("Ilovani tanlang 📲:", reply_markup=keyboard)
    await query.answer()
@dp.callback_query_handler(lambda query: query.data.startswith('appProduct_'), user_id=ADMINS)
async def select_app_product(callback_query: types.CallbackQuery):
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    app_id = callback_query.data.split('_')[-1]
    url1 = f'{BASE_URL}/products/{app_id}'
    response = requests.get(url1)
    products = response.json()
    keyboard = InlineKeyboardMarkup(row_width=1)
    for product in products:
        button_text = f"{product['quantity']} {product['name']} - {product['price']}"
        button_data = f"editProduct_{product['id']}"
        keyboard.add(InlineKeyboardButton(button_text, callback_data=button_data))
    keyboard.add(InlineKeyboardButton("Yangi qo'shish 🆕", callback_data=f"addProduct_{app_id}"))
    url2 = f'{BASE_URL}/app/{app_id}'
    response = requests.get(url2)
    app_data = response.json()
    await bot.send_photo(callback_query.from_user.id,
                         photo=app_data['app_pic'],
                         caption=f"Ilova 📲: {app_data['name']}\nMahsulotlar ⚔️:",
                         reply_markup=keyboard)
    await callback_query.answer()


############# NEW PRODUCT ######################
@dp.callback_query_handler(lambda query: query.data.startswith('addProduct_'), user_id=ADMINS)
async def add_product(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    await AddProductStates.app.set()
    app_id = query.data.split('_')[-1]
    async with state.proxy() as data:
        data['app'] = app_id
    await query.message.edit_text("Iltimos yangi mahsulot uchun ma'lumotlarni kiriting.\nMahsulot uchun nom🏷:", reply_markup=None)
    await AddProductStates.name.set()

@dp.message_handler(state=AddProductStates.name, user_id=ADMINS)
async def add_product_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Mahsulot miqdori🧮:")
    await AddProductStates.quantity.set()

@dp.message_handler(state=AddProductStates.quantity, user_id=ADMINS)
async def add_product_quantity(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quantity'] = int(message.text)
    await message.answer("Mahsulot narxi💰:")
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
        await message.answer("Yangi mahsulot muvaffaqqiyatli qo'shildi✅.")
    else:
        await message.answer("Mahsulot yaratishda xatolik❌.")
    await state.finish()


############### EDIT PRODUCT ####################
@dp.callback_query_handler(lambda query: query.data.startswith('editProduct_'), user_id=ADMINS)
async def EditSelectedProduct(query: types.CallbackQuery):
    product_id = query.data.split('_')[-1]
    url = f'{BASE_URL}/product/{product_id}'
    response = requests.get(url)
    product = response.json()
    print(product)
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("Nom🏷", callback_data=f"changeProduct_1_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Miqdori🧮", callback_data=f"changeProduct_2_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Narxi💰", callback_data=f"changeProduct_3_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("O'chirish❌", callback_data=f"deleteProduct_{product_id}"))
    text = (f"O'zgartirmoqchi bo'lgan bo'limingizni tanlang: \n"
            f"Nomi: {product['name']}\n"
            f"Miqdori: {product['quantity']}\n"
            f"Narxi: {product['price']}")
    await query.message.edit_text(text, reply_markup=keyboard)
    await query.answer(f"You selected to edit product with ID {product_id}.")

######## DELETE APP
@dp.callback_query_handler(lambda query: query.data.startswith('deleteProduct_'), user_id=ADMINS)
async def deleteAPPyesno(callback_query: types.CallbackQuery):
    app_id = callback_query.data.split('_')[-1]
    keyboad = types.InlineKeyboardMarkup(row_width=1)
    buttons = [types.InlineKeyboardButton('Ha', callback_data=f'deleteProductConfirm_{1}_{app_id}'),
               types.InlineKeyboardButton("Yo'q", callback_data=f'deleteProductConfirm_{0}_{app_id}')]
    keyboad.add(*buttons)
    await callback_query.message.edit_text("Mahsulotni rostdan o'chirmoqchimisiz❌?", reply_markup=keyboad)

@dp.callback_query_handler(lambda query: query.data.startswith('deleteProductConfirm_'))
async def deleteAPPconfirm(callback_query: types.CallbackQuery):
    confirmation, app_id = callback_query.data.split('_')[-2:]
    if confirmation == "1":
        url = f'{BASE_URL}/product/{app_id}'
        response = requests.delete(url)
        if response.status_code == 204:
            await callback_query.message.edit_text("Mahsulot muvaffaqqiyatli o'chirildi❌.", reply_markup=None)
        else:
            await callback_query.message.edit_text("Mahsulot o'chirishda xatolik❗️.", reply_markup=None)
    else:
        await callback_query.message.edit_text("Bekor qilindi.", reply_markup=None)

##### EDIT PRODUCT DATA
@dp.callback_query_handler(lambda query: query.data.startswith('changeProduct_'), user_id=ADMINS)
async def editProduct(callback_query: types.CallbackQuery, state: FSMContext):
    action_id, product_id = callback_query.data.split('_')[-2:]
    async with state.proxy() as data:
        data['id'] = product_id
        if action_id == '1':
            data['type'] = "name"
            await callback_query.message.edit_text("Mahsulot uchun yangi nomni kiriting:", reply_markup=None)
        elif action_id == '2':
            data['type'] = "quantity"
            await callback_query.message.edit_text("Mahsulot uchun yangi miqdorni kiriting:", reply_markup=None)
        elif action_id == '3':
            data['type'] = "price"
            await callback_query.message.edit_text("Mahsulot uchun yangi narxni kiriting:", reply_markup=None)
    await SingleDataProductForm.text.set()

@dp.message_handler(state=SingleDataProductForm.text, user_id=ADMINS)
async def get_product_detail(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
        column = data['type']
    url = f"{BASE_URL}/product/{data['id']}/"
    response = requests.patch(url, json={column: data["text"]})
    await state.finish()
    if response.status_code == 200:
        await message.answer("Ma'lumot muvaffaqqiyatli yangilangi✅.")
    else:
        await message.answer("Ma'lumot yangilanishida xatolik.")

############### EDIT CARDS #############
@dp.callback_query_handler(lambda query: query.data == 'card_settings', user_id=ADMINS)
async def edit_cards(query: types.CallbackQuery):
    await query.answer()
    url = f'{BASE_URL}/cards'
    response = requests.get(url)
    if response.status_code == 200:
        cards = response.json()
        keyboard = types.InlineKeyboardMarkup()
        for card in cards:
            keyboard.add(types.InlineKeyboardButton(f'{card["name"]} - {card["type"]}', callback_data=f"editCard_{card['id']}"))
        keyboard.add(types.InlineKeyboardButton('Yangi karta🆕', callback_data=f"addNewCard"))
        await query.message.edit_text(text="Kartani tanlang💳:", reply_markup=keyboard)
    else:
        await query.message.answer("Karta bilan xatolik.")
    return
@dp.callback_query_handler(lambda query: query.data.startswith('editCard_'), user_id=ADMINS)
async def EditSelectedCard(query: types.CallbackQuery):
    await query.answer()
    product_id = query.data.split('_')[-1]
    url = f'{BASE_URL}/cards/{product_id}'
    response = requests.get(url)
    card = response.json()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("Nomi", callback_data=f"changeCard_1_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Raqami", callback_data=f"changeCard_2_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Turi", callback_data=f"changeCard_3_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Izohi", callback_data=f"changeCard_4_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("O'chirish❌", callback_data=f"deleteProduct_{product_id}"))
    text = (f"Tanlangan karta ma'lumotlari📝: "
            f"Egasi: {card['name']} "
            f"Raqami: `{card['number']}`"
            f"Turi: {card['type']}"
            f"Izoh: {card['description']}"
            f"\n\nKerakli bo'limni tanlang:")
    await query.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('changeCard_'), user_id=ADMINS)
async def editProduct(callback_query: types.CallbackQuery, state: FSMContext):
    action_id, card_id = callback_query.data.split('_')[-2:]
    async with state.proxy() as data:
        data['id'] = card_id
        if action_id == '1':
            data['type'] = "name"
            await callback_query.message.edit_text("Karta egasini kiriting:", reply_markup=None)
        elif action_id == '2':
            data['type'] = "number"
            await callback_query.message.answer("Karta raqamini kiriting:", reply_markup=None)
        elif action_id == '3':
            data['type'] = "type"
            await callback_query.message.answer("Karta turini kiriting:", reply_markup=None)
        elif action_id == '4':
            data['type'] = "description"
            await callback_query.message.answer("Karta izohini kiriting:", reply_markup=None)
    await SingleDataCardForm.text.set()

@dp.message_handler(state=SingleDataCardForm.text, user_id=ADMINS)
async def get_card_data(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    url = f"{BASE_URL}/cards/{data['id']}/"
    response = requests.patch(url, json={data['type']: data["text"]})
    await state.finish()
    if response.status_code == 200:
        await message.answer("Ma'luumot muvaffaqqiyatli yangilandi✅.")
    else:
        await message.answer("Malumot yangilanishida xatolik.")

########## NEW CARD ###############
@dp.callback_query_handler(lambda query: query.data == 'addNewCard', user_id=ADMINS)
async def add_new_card(query: types.CallbackQuery):
    await query.message.edit_text(query.from_user.id, "Yangi karta yaratamiz💳.\nKarta egasining ismi va familyasini kiriting:",
                           reply_markup=None)
    await CardCreation.Name.set()

@dp.message_handler(state=CardCreation.Name, user_id=ADMINS)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Yangi karta raqamini kiriting:")
    await CardCreation.Number.set()

@dp.message_handler(state=CardCreation.Number, user_id=ADMINS)
async def process_number(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['number'] = message.text
    keyboard = ReplyKeyboardMarkup(row_width=2)
    buttons = [types.KeyboardButton("Humo"),
                types.KeyboardButton("Uzcard"),
                types.KeyboardButton("Visa"),
                types.KeyboardButton("Mastercard")]
    keyboard.add(*buttons)
    await message.answer("Select the type of the card:", reply_markup=keyboard)
    await CardCreation.TypeCard.set()

@dp.callback_query_handler(state=CardCreation.TypeCard, user_id=ADMINS)
async def process_type(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['typeCard'] = message.text
    keyword = ReplyKeyboardMarkup()
    keyword.add(types.KeyboardButton("O'tkazib yuborish"),)
    await message.answer("Karta uchun izoh kiriting: \n(Izoh ixtiyoriy)", reply_markup=keyword)
    await CardCreation.Description.set()

@dp.message_handler(state=CardCreation.Description, user_id=ADMINS)
async def process_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = None if message.text == "O'tkazib yuborish" else message.text
        url = f"{BASE_URL}/cards/"
        new_card = {
            "name": data['name'],
            "number": data['number'],
            "type": data['typeCard'],
            "description": data['description']
        }
        response = requests.post(url, json=new_card)
        if response.status_code == 201:
            await message.answer(f"Yangi karta muvaffaqqiyatli qo'shildi:\n```{new_card['number']}```", parse_mode='Markdown')
        else:
            await message.answer("Karta yaratishda xatolik❗️.")
    await state.finish()

async def shutdown(dp):
    await dp.bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)