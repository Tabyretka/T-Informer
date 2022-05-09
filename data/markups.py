from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

"""Главное меню"""
btnCurrentUrl = KeyboardButton("Отслеживаемый тайтл")
btnProfile = KeyboardButton("Профиль")
btnSeries = KeyboardButton("Получить ссылку на серию")
mainMenu = ReplyKeyboardMarkup(resize_keyboard=True).add(btnCurrentUrl, btnProfile, btnSeries)

"""Сап меню"""
btnCancel = KeyboardButton("Отмена")
supMenu = ReplyKeyboardMarkup(resize_keyboard=True).add(btnCancel)