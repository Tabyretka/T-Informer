from aiogram import Bot, executor, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from data import db_session
from data.users import User
from data.dateparser import parse
from config import TOKEN
import aiohttp
import os
import asyncio
import aioschedule

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

#жестчайший говнокод

@dp.message_handler(commands=["start"])
async def command_start(message: types.Message):
    img = open("img/start.png", "rb")

    start_message = """Использование:\nДля изменения отслеживаемого тайтла пришлите ссылку (прим. см. фото).
    
Проверка выхода новых серий происходит каждый день в 09:00 и 21:00"""
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        user = User(telegram_id=message.from_user.id)
        db_sess.add(user)
        db_sess.commit()
        db_sess.close()
    await bot.send_photo(message.from_user.id, img,
                         caption=f"Привет, {message.from_user.first_name}\n\n{start_message}",
                         reply_markup=nav.mainMenu)


async def add_url(message: types.Message):
    url = message.text
    if url != "":
        async with aiohttp.ClientSession() as session:
            res = await parse(session=session, url=url.strip())
            if res[0] != "ERROR":
                db_sess = db_session.create_session()
                user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
                user.urls = url
                db_sess.commit()
                db_sess.close()
                await message.answer(f"Успешно добавлено!\n\n{res[0]}\n{res[1]}", reply_markup=nav.mainMenu)
            else:
                await message.answer("Проверьте ссылку! Возможно, сезон уже закончился.", reply_markup=nav.mainMenu)

    else:
        await message.answer("Вы не указали ссылку!", reply_markup=nav.mainMenu)


@dp.message_handler()
async def other_messages(message: types.Message):
    if message.text == "Отслеживаемый тайтл":
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
        url = user.urls
        if url is not None and url != "":
            async with aiohttp.ClientSession() as session:
                res = await parse(session=session, url=url.strip())
                if res[0] != "ERROR":
                    db_sess.close()
                    await message.answer(f"Отслеживаемый тайтл:\n{res[0]}\n{res[1]}\n{url}", reply_markup=nav.mainMenu)
                else:
                    user.urls = ""
                    db_sess.commit()
                    await bot.send_message(user.telegram_id,
                                           f"Не удалось получить информацию о новых сериях, возможно, сезон закончился. Тайтл снят с отслеживаняи.",
                                           reply_markup=nav.mainMenu)
        else:
            await bot.send_message(message.from_user.id, "У вас еще нет тайтла на отслеживании!",
                                   reply_markup=nav.mainMenu)
        db_sess.close()
    elif message.text == "Профиль":
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
        await message.answer(
            f"{message.from_user.first_name}\nid в базе: {user.id}\nОтслеживаемый тайт: {user.urls}\nДобавлен в базу: {user.created_date}")
        db_sess.close()
    elif "animego.org" in message.text.strip():
        await add_url(message)
    else:
        await message.answer("Прости, но я не понимаю.", reply_markup=nav.mainMenu)
        # await bot.send_voice(message.from_user.id, open("audio/anime.mp3", "rb"), reply_markup=nav.mainMenu)


async def check_titles():
    db_sess = db_session.create_session()
    users = db_sess.query(User).all()
    async with aiohttp.ClientSession() as session:
        for user in users:
            if user.urls is not None and user.urls != "":
                res = await parse(session=session, url=user.urls.strip())
                if res[0] != "ERROR":
                    await bot.send_message(user.telegram_id, f"{res[0]}\n{res[1]}", reply_markup=nav.mainMenu)
                else:
                    user.urls = ""
                    db_sess.commit()
                    await bot.send_message(user.telegram_id,
                                           f"Не удалось получить информацию о новых сериях, возможно, сезон закончился. Тайтл снят с отслеживаняи.",
                                           reply_markup=nav.mainMenu)
    db_sess.close()


async def scheduler():
    aioschedule.every().day.at("21:00").do(check_titles)
    aioschedule.every().day.at("09:00").do(check_titles)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(_):
    asyncio.create_task(scheduler())


async def shutdown(dp):
    await storage.close()
    await bot.close()


if __name__ == "__main__":
    if not os.path.exists("db"):
        os.mkdir("db")
    db_session.global_init("db/db.sqlite")
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=shutdown)
