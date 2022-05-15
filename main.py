import aiohttp, aioschedule, asyncio, os
from aiogram import Bot, executor, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from data import db_session, markups as nav
from data.users import User
from data.dateparser import parse
from data import series_parser
from data.states import AniStates
from config import TOKEN

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


async def shutdown(dp):
    await storage.close()
    await bot.close()


@dp.message_handler(commands=["start"])
async def command_start(message: types.Message):
    start_message = """Использование:\nДля изменения отслеживаемого тайтла просто пришлите ссылку.
    
Проверка выхода новых серий происходит каждый день в 09:00 и 21:00"""
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        user = User(telegram_id=message.from_user.id)
        db_sess.add(user)
        db_sess.commit()
        db_sess.close()
    await bot.send_message(message.from_user.id, f"Привет, {message.from_user.first_name}\n\n{start_message}",
                           reply_markup=nav.mainMenu)


@dp.message_handler(commands=["ani"], state=None)
@dp.message_handler(Text(equals='Получить ссылку на серию', ignore_case=True), state=None)
async def test(message: types.Message):
    await message.answer("Пришлите название тайтла", reply_markup=nav.supMenu)
    await AniStates.name.set()


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='отмена', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Действие отменено', reply_markup=nav.mainMenu)


@dp.message_handler(state=AniStates.name)
async def test2(message: types.Message, state: FSMContext):
    name = message.text
    res = series_parser.search(name)
    mes = ""
    if res is None:
        await state.finish()
        await message.answer("Результаты не найдены", reply_markup=nav.mainMenu)
        return
    for i in enumerate(res):
        mes += f"{i[0] + 1}. {i[1]}\n"
    await state.update_data({"res": res})
    await message.answer(f"{mes}\nПришлите порядковый номер требуемого аниме", reply_markup=nav.supMenu)
    await AniStates.next()


@dp.message_handler(state=AniStates.chooseRes)
async def chooseRes(message: types.Message, state: FSMContext):
    num = int(message.text) - 1
    data = await state.get_data()
    res = data.get("res")
    episodes = series_parser.get_episodes(res, num)
    mes = ""
    for i in enumerate(episodes):
        mes += f"{i[0] + 1}. {i[1]}\n"
    l = [mes[i:i + 1000] for i in range(0, len(mes), 1000)]
    await state.update_data({"episodes": episodes})
    for i in l:
        await message.answer(f"{i}\nПришлите порядковый номер требуемой серии", reply_markup=nav.supMenu)
    await AniStates.next()


@dp.message_handler(state=AniStates.episode)
async def test2(message: types.Message, state: FSMContext):
    num = int(message.text) - 1
    data = await state.get_data()
    episodes = data.get("episodes")
    players = series_parser.get_players(episodes, num)
    if players:
        mes = ""
        for i in enumerate(players):
            mes += f"{i[0] + 1}. {i[1]}\n"
        await state.update_data({"players": players})
        await message.answer(f"{mes}\nПришлите порядковый номер требуемого плеера", reply_markup=nav.supMenu)
        await AniStates.next()
    else:
        await message.answer("Озвучка не найдена, возможно, серия еще не вышла.", reply_markup=nav.mainMenu)
        await state.finish()


@dp.message_handler(state=AniStates.player)
async def test3(message: types.Message, state: FSMContext):
    num = int(message.text) - 1
    data = await state.get_data()
    players = data.get("players")
    url = series_parser.get_url(players, num)
    headers = {"Referer": "https://aniboom.one", "Accept-Language": "ru-RU",
               "User-Agent": "Mozilla/5.0 (Macintosh; PPC Mac OS X 10_6_7 rv:6.0) Gecko/20170115 Firefox/35.0"}
    await message.answer(
        f"Для воспроизведения видео с AniBoom необходимо указать следующие заголовки:\n\n{headers}\n\n{url}",
        reply_markup=nav.mainMenu)
    await state.finish()


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


async def check_titles():
    db_sess = db_session.create_session()
    users = db_sess.query(User).all()
    async with aiohttp.ClientSession() as session:
        for user in users:
            if user.urls is not None and user.urls != "":
                res = await parse(session=session, url=user.urls.strip())
                if res[0] != "ERROR":
                    await bot.send_message(user.telegram_id, f"{res[0]}\n{res[1]}")
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


if __name__ == "__main__":
    if not os.path.exists("db"):
        os.mkdir("db")
    db_session.global_init("db/db.sqlite")
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=shutdown)
