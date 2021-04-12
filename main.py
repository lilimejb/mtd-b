import discord
from random import choice
from deck_site.data import db_session
from deck_site.data.users import User
from discord.ext import commands
from pprint import pprint
import asyncio

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

    @commands.command(name='create')
    async def start(self, ctx):
        await ctx.send(
            'Начался сбор игроков пишите "mtg! join" чтобы присоедениться,' +
            'через 1 минуту регестрация закончится автоматически')
        self.bot.games[ctx.message.channel] = Game()
        await asyncio.sleep(10)
        await ctx.send('Время на регестрацию вышло')
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
            except Exception as ex:
                await ctx.send(ex)
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
        name = ctx.message.author
        if self.pares[name] == 'auto_win':
            await ctx.send(f"Ты проходишь в следуюущий тур с автоматической победой")
        if name in self.pares.keys():
            await ctx.send(f"Твой соперник {self.pares[name].mention}")
        if name in self.pares.values():
            for key, value in self.pares.items():
                if name == value:
                    await ctx.send(f"Твой соперник {key.mention}")

    @commands.command(name='start_tour')
    async def start_tour(self, ctx):
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
                self.pares = cur_game.make_pares()

                pprint(self.pares)

                pares_to_print = ''
                for key, value in self.pares.items():
                    if value == 'auto_win':
                        pares_to_print += f'{key.mention} остался без пары и проходит в следуюущий тур!\n'
                    else:
                        pares_to_print += f'{key.mention} против {value.mention}\n'
                await ctx.send(f"Паринги {tour} тура:\n" +
                               f"{pares_to_print}\n" +
                               'У вас есть 1 час на тур')
                await asyncio.sleep(10)
                if cur_game.is_endable():
                    await self.end_tour(ctx)

    @commands.command(name='end_tour')
    async def end_tour(self, ctx):
        cur_game = self.bot.games[ctx.channel]
        try:
            cur_game.end_tour()
        except Exception as ex:
            await ctx.send(ex)
        else:
            # TODO сделать создание новых парингов
            await ctx.send('У вас есть 2 минуты, чтобы внести результаты дуэлей в таблицу,\n' +
                           'с помощью команды "mtg! result {win/lose/draw}"\n'+
                           'Если у вас автоматическая победа результаты вводить не нужно')
            cur_game.can_write_results = True
            cur_game.give_auto_points(self.pares)
            await asyncio.sleep(10)
            await ctx.send('Время на запись результатов закончено. Все неуспевшие получают 0 очков за тур')
            cur_game.can_write_results = False
            if cur_game.is_startable():
                await self.start_tour(ctx)

    @commands.command(name='result')
    async def result(self, ctx, result):
        cur_game = self.bot.games[ctx.channel]
        result = result.lower()
        member = ctx.message.author
        try:
            cur_game.give_points(member, result, self.pares)
        except Exception as ex:
            await ctx.send(ex)
        else:
            members = cur_game.get_members()
            result_to_print = ''
            for key, value in members.items():
                result_to_print += f'{key.name}: {value}\n'
            await ctx.send(f'{result_to_print}')

    @commands.command(name='end_game')
    async def end_game(self, ctx):
        cur_game = self.bot.games[ctx.channel]
        winners = cur_game.get_winners()
        cur_game.end_game()
        if len(winners) < 3:
            await ctx.send('Игра окончена\n' +
                           f'1 место: {winners[0][0].name} c {winners[0][1]} количеством очков\n' +
                           f'2 место: {winners[1][0].name} c {winners[1][1]} количеством очков\n')
        else:
            await ctx.send('Игра закончена\n' +
                           f'1 место: {winners[0][0].name} c {winners[0][1]} количеством очков\n' +
                           f'2 место: {winners[1][0].name} c {winners[1][1]} количеством очков\n' +
                           f'3 место: {winners[2][0].name} c {winners[2][1]} количеством очков\n')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # обработчик исключений в командах
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Такой команды не существует")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Недостаточно аргументов для команды")
        else:
            print(error)


class Game:
    def __init__(self):
        self.members = {}
        self.joinable = True
        self.cur_round = 0
        self.rounds_to_play = None
        self.can_write_results = False
        self.startable = True
        self.endable = False

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

    def end_join(self):
        if self.joinable:
            if len(self.members) > 1:
                self.joinable = False
            else:
                raise ValueError('Нельзя начать игру, в которой нет игроков')
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
        members = [member for member in self.members.keys()]
        pares = {}
        if len(members) > 1:
            if len(members) % 2 != 0:
                pares[members[-1]] = 'auto_win'
                for i in range(len(members) - 2):
                    if members[i] not in pares.keys() and members[i] not in pares.values():
                        pares[members[i]] = members[i + 1]
            else:
                for i in range(len(members) - 1):
                    if members[i] not in pares.keys() and members[
                        i] not in pares.values():
                        pares[members[i]] = members[i + 1]
        return pares

    def give_auto_points(self, pares):
        if 'auto_win' in pares.values():
            for key, value in pares.items():
                if value == 'auto_win':
                    self.members[key] += 2
                    break

    def give_points(self, member, result, pares):
        if self.can_write_results:
            if result == 'win' or result == 'победа':
                if member in self.members.keys():
                    self.members[member] += 2

            elif result == 'lose' or result == 'поражение':
                if member in self.members.keys():
                    if member in pares.keys():
                        for key, value in pares.items():
                            if member == key:
                                self.members[value] += 2
                                break
                    elif member in pares.values():
                        for key, value in pares.items():
                            if member == value:
                                self.members[key] += 2
                                break

            elif result == 'draw' or result == 'ничья':
                if member in self.members.keys():
                    if member in pares.keys():
                        self.members[member] += 1
                        self.members[pares[member]] += 1
                    if member in pares.values():
                        for key, value in pares.items():
                            if member == value:
                                self.members[key] += 1
                                self.members[value] += 1
                                break
        else:
            raise ValueError('Сейчас не время записи результатов')

    def update_round(self):
        # начало нового раунда
        if self.cur_round == self.rounds_to_play and not self.can_write_results:
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
        user = db_sess.query(User).all()
        names = {}
        for name, point in self.members.items():
            names[name] = point
        for pers in user:
            pers.points += names[pers.username]
        db_sess.commit()


bot = MtgBot(command_prefix='mtg! ')
bot.add_cog(MtgCommands(bot))
bot.run(TOKEN)
