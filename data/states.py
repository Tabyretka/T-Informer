from aiogram.dispatcher.filters.state import State, StatesGroup


class AniStates(StatesGroup):
    name = State()
    chooseRes = State()
    episode = State()
    player = State()