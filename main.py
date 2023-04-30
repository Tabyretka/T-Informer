from aiogram import Bot, executor, Dispatcher, types
from data import db_session, markups as nav
from data.users import User
from data.dateparser import parse
from misc.env import TgKeys
import aiohttp
import os
import asyncio
import aioschedule
import aiogram.utils.markdown as fmt

bot = Bot(token=TgKeys.TOKEN)
dp = Dispatcher(bot)

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

@dp.message_handler(lambda message: message.text.startswith('http'))
async def add_url(message: types.Message):
    url = message.text
    async with aiohttp.ClientSession() as session:
        res = await parse(session=session, url=url.strip())
        if res:
            db_sess = db_session.create_session()
            user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
            user.urls = url
            db_sess.commit()
            db_sess.close()
            await message.answer(f"Успешно добавлено!\n\n{res[0]}\n{res[1]}", reply_markup=nav.mainMenu)
        else:
            await message.answer("Проверьте ссылку! Возможно, сезон уже закончился.", reply_markup=nav.mainMenu)


@dp.message_handler(lambda message: message.text == "Отслеживаемый тайтл")
async def tracked_anime(message: types.Message):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    url = user.urls
    if url:
        async with aiohttp.ClientSession() as session:
            res = await parse(session=session, url=url.strip())
            if res:
                db_sess.close()
                
                await message.answer(
                fmt.text(
                fmt.text(fmt.hbold(res[0])),
                fmt.text(res[1]),
                fmt.text(fmt.hlink(title="ССЫЛКА", url=url)),
                    sep="\n"
                    ), parse_mode="HTML"
                )
                #await message.answer(f"{res[0]}\n{res[1]}\n{url}, reply_markup=nav.mainMenu)
            else:
                user.urls = ""
                db_sess.commit()
                await bot.send_message(str(user.telegram_id),
                                       f"Не удалось получить информацию о новых сериях, возможно, сезон закончился.\n{res[0]} больше не отслеживается.",
                                       reply_markup=nav.mainMenu)
    else:
        await bot.send_message(message.from_user.id, "Нет аниме на отслеживании!",
                                   reply_markup=nav.mainMenu)
    db_sess.close()


@dp.message_handler(lambda message: message.text == "Профиль")
async def profile_info(message: types.Message):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    await message.answer(f"{message.from_user.first_name}\nid в базе: {user.id}\nОтслеживаемое аниме: {user.urls}\nПервое использование: {user.created_date}")
    db_sess.close()



@dp.message_handler()
async def other_messages(message: types.Message):
    await message.answer("Прости, но я не понимаю.", reply_markup=nav.mainMenu)


async def check_titles():
    db_sess = db_session.create_session()
    users = db_sess.query(User).all()
    async with aiohttp.ClientSession() as session:
        for user in users:
            url = user.urls
            if url:
                res = await parse(session=session, url=user.urls.strip())
                if res:
                    await bot.send_message(str(user.telegram_id),
                        fmt.text(
                        fmt.text(fmt.hbold(res[0])),
                        fmt.text(res[1]),
                        fmt.text(fmt.hlink(title="ССЫЛКА", url=url)),
                            sep="\n"
                            ), parse_mode="HTML"
                        )
                    # await bot.send_message(str(user.telegram_id), f"{res[0]}\n{res[1]}", reply_markup=nav.mainMenu)
                else:
                    user.urls = ""
                    db_sess.commit()
                    await bot.send_message(str(user.telegram_id),
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
    await bot.close()


if __name__ == "__main__":
    if not os.path.exists("db"):
        os.mkdir("db")
    db_session.global_init("db/db.sqlite")
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=shutdown)
