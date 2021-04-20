import discord
from requests import get
import datetime as dt
from deck_site.data import db_session
from deck_site.data.users import User
from deck_site.data.games import Games
from deck_site.data.decks import Decks
from discord.ext import commands
from discord.ext.commands import MemberConverter
from pprint import pprint
import asyncio
import datetime

TOKEN = "ODI3NTcwMjAyNTcyNjE5ODU2.YGc8zw.l_wWjYdHwvwZX8jc8HnT03BayvU"
db_session.global_init("deck_site/db/mtd_decks.db")


class MtgBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.games = {}
        self.pares = {}

    async def on_message(self, message):
        if message.content.startswith('mtg! '):
            await self.process_commands(message)


class MtgCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pares = self.bot.pares
        self.converter = MemberConverter()

    @commands.command(name='info')
    async def help(self, ctx):
        await ctx.send('```КОМАНДЫ MTD-B```' +
                       '```mtg! create - создаёт игру в определённом канале\n' + \
                       'mtg! join - присоединение к игре (команду можно использовать только во время регистрации)\n' + \
                       'mtg! end - заканчивает регистрацию\n' + \
                       'mtg! start_tour - начинает тур, который длится 1 час, и разбивает игроков\n' + \
                       'mtg! end_tour - заканчивает тур и начинает время на запись результатов\n' + \
                       'mtg! parings - выводит паринг в который входит пользователь написавший сообщение\n' + \
                       'mtg! result {win/lose/draw} - заносит результат пары в таблицу\n' + \
                       'mtg! deck {user}{True/False} - выводит колоду игрока user(все или одну, по умолчанию все)\n' + \
                       'mtg! members {date} - выводит участников определённой игры(если игр по данной дате найдено ' + \
                       'больше одной выводит самую первую\n' + \
                       'mtg! top3 - выводит 3 лучших игрока за всё время\n' + \
                       'mtg! most_popular - выводит игрока с наибольшей посещаемостью\n' + \
                       'mtg! end_game - выводит результаты игроков, заносит результаты в общую таблицу```')

    @commands.command(name='create')
    async def start(self, ctx):
        if ctx.message.channel in self.bot.games.keys():
            await ctx.send("Игра уже началась")
            return
        await ctx.send(
            'Начался сбор игроков пишите "mtg! join" чтобы присоедениться,' +
            'через 1 минуту регестрация закончится автоматически')
        self.bot.games[ctx.message.channel] = Game()
        await asyncio.sleep(30)
        print(self.bot.games[ctx.message.channel].is_joinable)
        if self.bot.games[ctx.message.channel].is_joinable:
            await self.end(ctx)

    @commands.command(name='join')
    async def join(self, ctx):
        if ctx.channel in self.bot.games.keys():
            try:
                self.bot.games[ctx.channel].add_member(ctx.message.author)
            except Exception as ex:
                await ctx.send(ex)
            else:
                await ctx.send(f"К игре присоединяется {ctx.message.author.mention}!")

    @commands.command(name='end')
    async def end(self, ctx):
        if ctx.channel in self.bot.games.keys():
            cur_game = self.bot.games[ctx.channel]
            cur_game_members = [member for member in cur_game.get_members(True)]
            try:
                cur_game.end_join()
            except ValueError as ex:
                await ctx.send(ex)
            except RuntimeError as ex:
                await ctx.send(ex)
                self.bot.games.pop(ctx.channel)
            else:
                rounds_to_play = (len(cur_game_members) // 2) + 1 if len(cur_game_members) % 2 != 0 else (
                        len(cur_game_members) // 2)
                cur_game.rounds_to_play = rounds_to_play
                await ctx.send("Сбор игроков закончен")
                await ctx.send("Игра началась!\n" +
                               f"Участники сегодняшней игры:\n" +
                               f"{', '.join(member.mention for member in cur_game.get_members(True))}\n" +
                               f"Количество туров: {rounds_to_play}")
                await ctx.send("Через 30 секунд автоматически начнётся 1 тур")
                await asyncio.sleep(10)
                if cur_game.is_startable():
                    await self.start_tour(ctx)

    @commands.command(name='parings')
    async def parings(self, ctx):
        if ctx.channel in self.bot.games.keys():
            if not self.pares:
                await ctx.send('Для использования команды необходимо дождаться объявления парингов')
                return
            cur_game = self.bot.games[ctx.channel]
            name = ctx.message.author
            member1, member2 = cur_game.find_pare(self.pares, name)
            await ctx.send(f"Ты в паре:\n{member1.mention} vs {member2.mention}")

    @commands.command(name='start_tour')
    async def start_tour(self, ctx):
        if ctx.channel in self.bot.games.keys():
            cur_game = self.bot.games[ctx.channel]
            try:
                cur_game.start_tour()
            except Exception as ex:
                await ctx.send(ex)
            else:
                tour = cur_game.update_round()
                if tour == -1:
                    await self.end_game(ctx)
                else:
                    cur_game.pares_that_cant_write_results = {}
                    self.pares = cur_game.make_pares()

                    pprint(self.pares)

                    pares_to_print = ''
                    counter = 1
                    for key, value in self.pares.items():
                        if value == 'auto_win':
                            pares_to_print += f'{counter}. {key.mention} остался без пары и проходит в следуюущий тур!\n'
                        else:
                            pares_to_print += f'{counter}. {key.mention} против {value.mention}\n'
                        counter += 1
                    await ctx.send(f"Паринги {tour} тура:\n" +
                                   f"{pares_to_print}\n" +
                                   'У вас есть 1 час на тур')
                    await asyncio.sleep(10)
                    if cur_game.is_endable():
                        await self.end_tour(ctx)

    @commands.command(name='members')
    async def get_members(self, ctx, date):
        db_sess = db_session.create_session()
        date = date.split('-')
        date = dt.datetime(int(date[0]), int(date[1]), int(date[2]), 00, 00, 00)
        players = db_sess.query(Games).filter(Games.played_date == date).first().players[1:-1]
        print(players)
        to_print = ''
        for player in players.split(', '):
            to_print += f'{player[1:-1]}\n'

        await ctx.send(f'Участники игры {date.date()}:\n{to_print}')

    @commands.command(name='top3')
    async def get_top3(self, ctx):
        db_sess = db_session.create_session()
        users = db_sess.query(User).all()
        top3 = dict(sorted({user.username: user.points for user in users}.items(), key=lambda x: -x[1])[:3])
        to_print = ''
        counter = 1
        for player, points in top3.items():
            to_print += f'{counter}. {player} всего очков {points}\n'
            counter += 1

        await ctx.send(to_print)

    @commands.command(name='most_popular')
    async def get_most_popular(self, ctx):
        db_sess = db_session.create_session()
        users = db_sess.query(User).all()
        most_popular = max({user.username: user.games_played for user in users}.items(), key=lambda x: x[1])[0]
        await ctx.send(f'Игрок посетивший турниры самое большое число раз: {most_popular}')

    @commands.command(name='deck')
    async def get_deck(self, ctx, user, all=True):
        db_sess = db_session.create_session()
        try:
            user_id = db_sess.query(User).filter(User.username == user).first().id
        except Exception:
            await ctx.send('Игрок не зарегестрирован')
        else:
            try:
                if all:
                    decks = db_sess.query(Decks).filter(Decks.user_id == user_id).all()
                else:
                    decks = [db_sess.query(Decks).filter(Decks.user_id == user_id).first()]
            except Exception:
                await ctx.send('У игрока нет зарегестрированных колод')
            else:
                for i, deck in enumerate(decks, 1):
                    deck = get(f'http://localhost:5000/api/deck/{deck.id}').json()['deck']
                    await ctx.send(f'{i}.Колода игрока {user}:'
                                   f'\n*{deck["name"]}*'
                                   f'\n**Основная колода**:\n```{deck["main_deck"]}```'
                                   f'\n**Сайдборд**:\n```{deck["side_board"]}```')

    @commands.command(name='end_tour')
    async def end_tour(self, ctx):
        if ctx.channel in self.bot.games.keys():
            cur_game = self.bot.games[ctx.channel]
            try:
                cur_game.end_tour()
            except Exception as ex:
                await ctx.send(ex)
            else:
                await ctx.send('У вас есть 2 минуты, чтобы внести результаты дуэлей в таблицу,\n' +
                               'с помощью команды "mtg! result {win/lose/draw}"\n' +
                               'Если у вас автоматическая победа результаты вводить не нужно')
                cur_game.can_write_results = True
                cur_game.give_auto_points(self.pares)
                await asyncio.sleep(120)
                cur_game.can_write_results = False
                if cur_game.is_startable():
                    await ctx.send('Время на запись результатов закончено. Все неуспевшие получают 0 очков за тур')
                    await self.start_tour(ctx)

    @commands.command(name='result')
    async def result(self, ctx, result):
        if ctx.channel in self.bot.games.keys():
            cur_game = self.bot.games[ctx.channel]
            result = result.lower()
            member = ctx.message.author
            try:
                cur_game.give_points(member, result, self.pares)
            except Exception as ex:
                await ctx.send(ex)
            else:
                member1, member2 = cur_game.find_pare(self.pares, member)
                member1, points1, member2, points2 = cur_game.get_current_members(member1, member2)
                await ctx.send(f'{member1.mention} : {points1}\n{member2.mention} : {points2}')

    @commands.command(name='end_game')
    async def end_game(self, ctx):
        if ctx.channel in self.bot.games.keys():
            cur_game = self.bot.games[ctx.channel]
            cur_game.endable = False
            cur_game.startable = False
            winners = cur_game.get_winners()
            cur_game.end_game()
            if len(winners) < 3:
                await ctx.send('Игра окончена\n' +
                               f'1 место: {winners[0][0].name} количество очков: {winners[0][1]}\n' +
                               f'2 место: {winners[1][0].name} количество очков: {winners[1][1]}')
            else:
                await ctx.send('Игра закончена\n' +
                               f'1 место: {winners[0][0].name} количество очков: {winners[0][1]} \n' +
                               f'2 место: {winners[1][0].name} количество очков: {winners[1][1]} \n' +
                               f'3 место: {winners[2][0].name} количество очков: {winners[2][1]} ')
            self.bot.games.pop(ctx.channel)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # обработчик исключений в командах
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Такой команды не существует")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Недостаточно аргументов для команды")
        else:
            print(error)


# оснвной класс игры
class Game:
    def __init__(self):
        self.members = {}
        self.joinable = True
        self.cur_round = 0
        self.rounds_to_play = None
        self.can_write_results = False
        self.pares_that_cant_write_results = {}
        self.startable = True
        self.endable = False

    def is_joinable(self):
        return self.joinable

    # добавляет пользователя в игру
    def add_member(self, member):
        if self.joinable:
            if member in self.members.keys():
                raise ValueError(f"{member.mention}, ты уже в игре!")
            else:
                db_sess = db_session.create_session()
                user = db_sess.query(User).all()
                in_table = False
                for pers in user:
                    if str(member) == str(pers.username):
                        in_table = True
                if in_table:
                    self.members[member] = 0
                else:
                    raise ValueError('Для того, чтобы приянть участие в турнире нужно зарегистрироваться на сайте')
        else:
            raise ValueError('Сбор игроков уже завершен')

    # заканчивает регестрацию игроков
    def end_join(self):
        if self.joinable:
            self.joinable = False
            if len(self.members.keys()) > 1:
                pass
            else:
                raise RuntimeError(
                    'Нельзя начать игру, в которой нет игроков.\nНапишите "mtg! create" чтобы начать поиск заново')
        else:
            raise ValueError('Сбор игроков уже завершен')

    def start_tour(self):
        if self.startable:
            self.startable = False
            self.endable = True
        else:
            raise ValueError('Тур уже начался')

    def is_startable(self):
        return self.startable

    def end_tour(self):
        if self.endable:
            self.endable = False
            self.startable = True
        else:
            raise ValueError('Нельзя закончить не начатый тур')

    def is_endable(self):
        return self.endable

    def make_pares(self):
        if self.cur_round == 1:
            db_sess = db_session.create_session()
            members = [member for member in self.members.keys()]
            members_names = [f'{member.name}#{member.discriminator}' for member in self.members.keys()]
            players = {}

            for i, member in enumerate(members_names):
                players[members[i]] = db_sess.query(User).filter(User.username == member).first().points
            players = [key for key, value in sorted(players.items(), key=lambda x: x[1], reverse=True)]

        else:
            players = [key for key, value in sorted(self.members.items(), key=lambda x: x[1], reverse=True)]
        pares = {}
        if len(players) % 2 != 0:
            pares[players[-1]] = 'auto_win'
            for i in range(len(players) - 2):
                if players[i] not in pares.keys() and players[i] not in pares.values():
                    pares[players[i]] = players[i + 1]
        else:
            for i in range(len(players) - 1):
                if players[i] not in pares.keys() and players[i] not in pares.values():
                    pares[players[i]] = players[i + 1]
        return pares

    def find_pare(self, pares, name):
        if name in pares.keys():
            return name, pares[name]
        if name in pares.values():
            for key, value in pares.items():
                if name == value:
                    return key, value

    def give_auto_points(self, pares):
        if 'auto_win' in pares.values():
            for key, value in pares.items():
                if value == 'auto_win':
                    self.members[key] += 2
                    self.pares_that_cant_write_results[key] = 'auto_win'
                    break

    def get_current_members(self, member1, member2):
        return member1, self.members[member1], member2, self.members[member2]

    def give_points(self, member, result, pares):
        if self.can_write_results:
            if member in self.members.keys():
                member1, member2 = self.find_pare(pares, member)
                if member1 not in self.pares_that_cant_write_results.keys():
                    if result in ['win', 'lose', 'draw', 'победа', 'поражение', 'ничья']:
                        if result == 'win' or result == 'победа':
                            self.members[member] += 2

                        elif result == 'lose' or result == 'поражение':
                            if member == member2:
                                self.members[member1] += 2
                            if member == member1:
                                self.members[member2] += 2

                        elif result == 'draw' or result == 'ничья':
                            self.members[member1] += 1
                            self.members[member2] += 1

                        self.pares_that_cant_write_results[member1] = member2
                    else:
                        raise ValueError('Результат неверно указан')
                else:
                    raise ValueError('Ваша пара уже записала результат')
            else:
                raise ValueError('Вас нет в списке участников')
        else:
            raise ValueError('Сейчас не время записи результатов')

    def update_round(self):
        # начало нового раунда
        if self.cur_round == self.rounds_to_play:
            return -1
        else:
            self.cur_round += 1
            return self.cur_round

    def get_winners(self):
        return list(sorted(self.members.items(), key=lambda x: x[1], reverse=True))

    def get_members(self, names_only=False):
        return self.members.keys() if names_only else self.members

    def end_game(self):
        # заканчивает игру (добовляет файлы в бд)
        db_sess = db_session.create_session()
        games = Games(
            players=f'{[f"{member.name}#{member.discriminator}" for member in self.get_members(names_only=True)]}',
            played_date=datetime.datetime.now().date()
        )
        db_sess.add(games)
        for member in self.members.keys():
            db_sess.query(User).filter(User.username == f'{member.name}#{member.discriminator}').first().points += \
                self.members[member]
            db_sess.query(User).filter(
                User.username == f'{member.name}#{member.discriminator}').first().games_played += 1
        db_sess.commit()


bot = MtgBot(command_prefix='mtg! ')
bot.add_cog(MtgCommands(bot))
bot.run(TOKEN)
