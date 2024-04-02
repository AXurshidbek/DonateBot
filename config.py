import asyncio
import json
import logging
import aiogram
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# from db_config import DBConfig


# cursor = DBConfig()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token="6830102506:AAFVPp9CVF7jvJ7RKXjHtJQpraXMCgSak5c")
dp = Dispatcher(bot)
admin_user_id = [5729115581]


# Command handlers
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    is_admin = str(message.from_user.id) in admin_user_id

    if is_admin:
        await message.answer(f"Salom {message.from_user.first_name}!\n\n"
                             "Sizda admin sifatida belgilangansiz."
                             "Foydalanish qo'llanmasini olish uchun\n"
                             "/help buyrug'idan foydalaning"
                             )
    else:
        inline_kb = InlineKeyboardMarkup(row_width=2)
        inline_kb.add(InlineKeyboardButton("O'zbek", callback_data='lang_uz'),
                      InlineKeyboardButton("Русский", callback_data='lang_ru'),
                      InlineKeyboardButton("English", callback_data='lang_en'))

        await message.answer(f"Salom {message.from_user.first_name}.\n\n"
                            "Bu Donation bot.\n"
                            "Botdan foydalanish tilini tanlang.\n" +
                            f"Привет, {message.from_user.first_name}.\n\n"
                            "Это бот для пожертвований.\n"
                            "Выберите язык для использования бота.\n"+
                             f"Hello {message.from_user.first_name}.\n\n"
                             "This is a Donation bot.\n"
                             "Choose the language to use the bot."
                             , reply_markup=inline_kb
                             )

@dp.callback_query_handler(lambda query: True)
async def handle_callback_query(query: types.CallbackQuery):
    # Example handling of button clicks
    if query.data == 'lang_uz':
        await query.answer("You clicked Button 1!")
    elif query.data == 'lang_ru':
        await query.answer("You clicked Button 2!")
    elif query.data == 'lang_en':
        await query.answer("You clicked Button")

@dp.message_handler(commands=["help"])
async def help_command(message: types.Message):
    is_admin = str(message.from_user.id) in admin_user_id

    if is_admin:
        await message.answer("Adminlar uchun quyidagi buyruqlar mavjud:\n"
                             "/signal - signallar qabul qilish\n"
                             "/send - signallarni yuborish\n"
                             )
    else:
        await message.answer("Bu botdan foydalanish va signallar qabul qila olishingiz uchun sizdan obuna bo'lish talab qilinadi.\n"
                             "Obuna bo'lish uchun adminga murojat qiling\n"
                             "admin: @SMART_MONE_ADMIN\n"
                             "va /subscribe buyrug'ini yuboring"
                             )


# @dp.message_handler(commands=["subscribe"])
# async def subscribe_command(message: types.Message):
#     is_admin = str(message.from_user.id) in admin_user_id
#     if is_admin:
#         await message.answer("Siz admin ekaningiz uchun obuna bo'lish mumkin emas.")
#     else:
#         user_id = message.from_user.id
#         user_name = message.from_user.full_name
#         user_username = message.from_user.username
#         user_photo = None
#
#         if user_id not in [int(user["id"]) for user in users]:
#             photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
#             keyboard = types.InlineKeyboardMarkup()
#             keyboard.add(types.InlineKeyboardButton("Qo'shish", callback_data=f"add_{user_id}"))
#             keyboard.add(types.InlineKeyboardButton("Rad etish", callback_data=f"ignore_{user_id}"))
#             if photos.photos:
#                 photo_file_id = photos.photos[0][-1].file_id
#                 await bot.send_photo(chat_id=admin_user_id, photo=photo_file_id,
#                                      caption=f"Yangi foydalanuvchi:\n"
#                                             f"ID: {user_id}\n"
#                                             f"Ism: {user_name}\n"
#                                             f"Foydalanuvchi nomi: {user_username}\n"
#                                             "Bu foydalanuvchini qo'shishni hohlaysizmi?",
#                                      reply_markup=keyboard)
#             else:
#                 await bot.send_message(chat_id=admin_user_id,
#                                        text=f"New user:\nID: {user_id}\nName: {user_name}\nUsername: {user_username}\n"
#                                             "Do you want to add this user?",
#                                        reply_markup=keyboard)
#             await message.answer("Adminga obuna bo'lish so'rovi yuborildi. Kutishda qoling!")
#         else:
#             await message.answer("Siz allaqachon obunachilar ro'yxatida borsiz.")
#
# @dp.callback_query_handler(lambda query: query.data.startswith(("add", "ignore")))
# async def handle_subscription_action(callback_query: types.CallbackQuery):
#     action, user_id = callback_query.data.split("_")
#     user_id = int(user_id)
#     if action == "add":
#         if user_id not in [int(user["id"]) for user in users]:
#             users.append({"id": user_id})
#             with open("users.json", "w") as file:
#                 json.dump(users, file)
#             await bot.send_message(chat_id=user_id, text="Siz admin tomonidan tasdiqlandingiz.\n Endi signallarni qabul qilib olasiz.")
#         else:
#             await bot.send_message(chat_id=user_id,
#                                    text="")
#     elif action == "ignore":
#         await bot.send_message(chat_id=user_id,
#                                text="Siz admin tomonidan rad etildingiz.\n Iltimos adminga murojaat qiling.\nadmin: @SMART_MONE_ADMIN")
#         await callback_query.answer("Foydalanuvchi ignore qilingan.")
#
#     await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
#
# @dp.message_handler(commands=['signal'])
# async def handle_signal_command(message: types.Message):
#     is_admin = str(message.from_user.id) in admin_user_id
#     global signal_mode
#     if is_admin:
#         signal_mode = True
#         await message.answer("Obunachilarga yubormoqchi bo'lgan habarlaringizni joylang va /send buyrug'i yordamida ularni  yuboring.")
#     else:
#         await message.answer("Bunday buyruq mavjud emas.")
#
# @dp.message_handler(commands=['send'])
# async def handle_send_command(message: types.Message):
#     is_admin = str(message.from_user.id) in admin_user_id
#     global signal_mode
#     if is_admin:
#         if signal_mode:
#             signal_mode = False
#             await message.answer("Habarlaringiz yuborildi!")
#             for stored_message in stored_messages:
#                 for user in [int(user["id"]) for user in users]:
#                     # Check if the message has been sent to this user before
#                     if user not in sent_users:
#                         try:
#                             content = stored_message.text or stored_message.caption or ''
#                             media = stored_message.photo or None
#                             if media:
#                                 await bot.send_photo(user, photo=media[-1]['file_id'], caption=content)
#                             elif content:
#                                 await bot.send_message(user, content)
#                             logging.info(f"Message forwarded to user {user}")
#                             sent_users.add(user)  # Add the user ID to sent_users set
#                         except Exception as e:
#                             logging.error(f"Failed to forward message to user {user}: {e}")
#                 sent_users.clear()
#             stored_messages.clear()
#         else:
#             await message.answer("/send buyrug'idan foydalanishdan avval /signal buyqug'i yordamida habarlaringizni yuroring.")
#     else:
#         await message.answer("Bunday buyruq mavjud emas.")
#
#
# @dp.message_handler(content_types=['text'])
# async def handle_admin_message(message: types.Message):
#     is_admin = str(message.from_user.id) in admin_user_id
#     if is_admin:
#         if signal_mode:
#             stored_messages.append(message)
#             await message.answer("Xabar qabul qilindi. Iltimos, boshqa xabar yuboring yoki tugatish uchun /send buyrug'idan foydalaning.")
#         else:
#             await message.answer("Signal yuborish uchun /signal buyrug'idan foydalaning.")
#
#
# @dp.message_handler(content_types=["photo"])
# async def handle_photo(message: types.Message):
#     logging.info(message)
#     is_admin = str(message.from_user.id) in admin_user_id
#     if is_admin:
#         if signal_mode:
#             stored_messages.append(message)
#             await message.answer("Xabar qabul qilindi. Iltimos, boshqa xabar yuboring yoki tugatish uchun /send buyrug'idan foydalaning.")
#             logging.info(message)
#         else:
#             await message.answer("Signal yuborish uchun /signal buyrug'idan foydalaning.")
#     else:
#         await message.answer("Siz rasm yubora olmaysiz.")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

