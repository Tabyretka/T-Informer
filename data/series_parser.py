from anicli_ru.extractors.animego import Anime


def search(name: str):
    anime = Anime()
    res = anime.search(name)
    return res


def get_episodes(res, title_num: int):
    episodes = res[title_num].episodes()
    return episodes


def get_players(episodes, episode_num: int):
    players = episodes[episode_num].player()
    return players


def get_url(players, player_num: int):
    return players[player_num].get_video()
