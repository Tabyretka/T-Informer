from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

btnMain = KeyboardButton("Главное меню")

"""Главное меню"""
btnCurrentUrl = KeyboardButton("Отслеживаемый тайтл")
btnProfile = KeyboardButton("Профиль")
mainMenu = ReplyKeyboardMarkup(resize_keyboard=True).add(btnCurrentUrl, btnProfile)
