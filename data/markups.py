from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

btn1 = KeyboardButton("Отслеживаемый тайтл")
btn2 = KeyboardButton("Профиль")
mainMenu = ReplyKeyboardMarkup(resize_keyboard=True).add(btn1).add(btn2)
