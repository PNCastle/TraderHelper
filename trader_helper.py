#Author: Paul Castleberry
#Purpose: A discord bot to aid stock traders.

#A flag for simple switching between tokens for discord servers. A cloned server is used 
#during development for debugging purposes before deployment to live server
TESTING = False

import discord
import asyncio
import json
import os
import time
import operator
import pandas as pd
import numpy as np

from discord.ext import commands

#below you must place your discord tokens for your specific servers, beta corresponds
#to the testing server and live for the actual discord server

#the path variables correspond to the directory in which the script, json, and csv files
#exist on your particular machine

beta = "" #beta Token
beta_path = r''
live = "" #live Token
live_path = r''


#control flow for test/live server
if TESTING:
    TOKEN = beta
    PATH  = beta_path
else:
    TOKEN = live
    PATH  = live_path

os.chdir(PATH)

#client = commands.bot(command_prefix = "$")
client = discord.Client()
server = discord.Server

#this is a URL link used to retrieve live stock quotes and display an image into discord
chart_link = "https://www.stockscores.com/chart.asp?TickerSymbol=$&TimeRange=|&"\
             "zInterval=d&Volume=1&ChartType=CandleStick&Stockscores=1&ChartWid"\
             "th=1100&ChartHeight=480&LogScale=&Band=&avgType1=&movAvg1=&avgTyp"\
             "e2=&movAvg2=&Indicator1=None&Indicator2=None&Indicator3=None&Indi"\
             "cator4=None&endDate=&CompareWith=&entryPrice=&stopLossPrice=&cand"\
             "les=redgreen"

#we must load our csv file containing all pertainable stock symbols into a data structure, 
#namely OTC BB stocks and Pink Sheets
symbol_frame = pd.read_csv(PATH+'/OTCBB.csv', names=['Symbol', 'Description'],skiprows=[0,1])
symbol_array = np.array(symbol_frame)

#the list of commands available to admins of the discord server (note $clear has been disabled)
command_array = ['$entry', '$chart', '$level', '$ranks', '$picks', '$allpicks', '$mypicks', '$yourpicks', '$commands', '$clear', '$board', '$reset']

#a message to console notifying user that the bot is running
@client.event
async def on_ready():
    print('\nLogged in as: '+ client.user.name +"\n")

#when a new member joints the discord they should be automatically promoted to the starting rank
@client.event
async def on_member_join(member):

    server = member.server
    channels = list(server.channels)
    channel_id_strato = 0

    #a message should be printed in the primary channel for new users, this for loop ensures we are in the primary channel
    for channel_name in channels:
        if str(channel_name) == "strato-chat":
            break
        channel_id_strato += 1

    #send a message to the channel that a new member has joined. This string can be customized appropriately
    await client.send_message(channels[channel_id_strato], 'Welcome {} to the (main chat room) #strato-chat.'.format(member.mention))

    #this controls the actual promotion of the new member
    role = discord.utils.get(member.server.roles, name='strato')
    await client.add_roles(member, role)

    #we must assign invite reward to the member who invites our new user. this is managed below by opening the json file holding
    #invite data and updating it accordingly
    invites = await client.invites_from(member.server)

    with open('invites.json', 'r') as f:
        invites_old = json.load(f)

    with open('users.json', 'r') as f:
        users = json.load(f)

    for invite in invites:
        await update_data(users, invite.inviter)
        await update_invite_data(invites_old, invite, users)

    with open('users.json', 'w') as f:
        json.dump(users, f)

    with open('invites.json', 'w') as f:
        json.dump(invites_old, f)

#below is the primary logic for our discord bot. every message sent by a user in the discord server is parsed and if certain
#requirements are met the bot will respond accordingly
@client.event
async def on_message(message):

    #Initialize
    server = message.server
    channels = list(server.channels)
    author = str(message.author)
    content = str(message.content)
    author = author[0:author.index('#')]
    content = content[7: len(content)]
    split_content = content.split()
    full_content = str(message.content)
    full_split_content = full_content.split()
    symbol_mentioned = False
    symbol = ''

    #parse the user message and see if one of our stock symbols from our csv file was mentioned. if so this will flag that a ticker
    #was mentioned which will have multiple effects. a user is warded experience points for participating productively in the 
    #discord. ticker mentions as well as invites to the server are the criteria for a user to rank up within the discord channel.
    if len(full_split_content) > 0 and not (client.user == message.author):
        if not full_split_content[0] in command_array:
            for item in full_split_content:
                symbol_check = item
                if symbol_check[0] == '$':
                    symbol_check = symbol_check[1: len(item)]
                if symbol_check.upper() in symbol_array:
                    symbol_mentioned = True
                    symbol = symbol_check.upper()

    #$entry command
    #the entry command lets users notify other members of the discord channel that they have bought into a particular stock
    #the bot will then post in a channel the entry that was made, where no other users can send messages. this provides
    #a channel that is entirely filled with entries made by each trader. this servers the purpose of letting users quickly
    #see what stocks others are bought into exclusively. it also provides time stamped, unalterable messages that traders
    #can share later, when they wish to boast about a good play that provided them a profit. 
    if message.content.startswith('$entry'):
        channel_id_entries = 0
        for channel_name in channels:
            if str(channel_name) == "entries":
                break
            channel_id_entries += 1

        #below is a feedback message for users who are attempting to use the entry command but are not following the
        #format required. this will be sent back to the user in an attempt to help them use the correct formatting.
        example = "$entry $xxxx 10mil .007"
        default_format = "$entry\t$(ticker)\t(lot size)\t(entry point)\n\nexample:\n\n" + example
        format_tip = author+", when posting a play, please follow the format:\n\n"+default_format
        frame = "\n\n-------------------------------------\n\n"
        template = frame+"\t"+author+" has opened a position:\n\n\t"+content + frame

        if (len(split_content) == 3):
            ticker = split_content[0]
            lot_size = split_content[1]
            entry_point = split_content[2]
            valid_message = False
            valid_message = ticker[0] == '$' and lot_size[0].isdigit() and (entry_point[0] == '.' or entry_point[0].isdigit())
            if valid_message:
                tmp = await client.send_message(channels[channel_id_entries], 'Testing')
                await client.edit_message(tmp, template)
                tmp = await client.send_message(message.channel, 'success')
                await client.edit_message(tmp, author +", your play has been posted in \"entries\".")
            else:
                tmp = await client.send_message(message.channel, 'error')
                await client.edit_message(tmp, format_tip)
        else:
            tmp = await client.send_message(message.channel, 'error')
            await client.edit_message(tmp, format_tip)
    #$chart command
    if message.content.startswith('$chart'):
        channel_id_charting = 0
        for channel_name in channels:
            if str(channel_name) == "charting":
                break
            channel_id_charting += 1

        chart = str(message.content)
        chart_split = chart.split()
        chart_print = chart_link
        time_frame = '30'
        valid_length = False
        print_local = False
        valid_length = (len(chart_split[1]) == 4 or len(chart_split[1]) == 5 or len(chart_split[1]) == 6)
        if chart_split[1][0] == '$' and valid_length:
            ticker_lookup = chart_split[1][1: len(chart_split[1])]
            print(ticker_lookup)
            chart_final = chart_print.replace('$', ticker_lookup)

            if (len(chart_split) > 2):
                if chart_split[2].isdigit():
                    time_frame = chart_split[2]
                if chart_split[2] == '$':
                    print_local = True
                if (len(chart_split) > 3):
                    if chart_split[3].isdigit():
                        time_frame = chart_split[3]
                    if chart_split[3] == '$':
                        print_local = True

            chart_final = chart_final.replace('|', time_frame)
            print(chart_final)

            embed = discord.Embed()
            embed.set_image(url=chart_final)
            ticker_lookup = "Chart for $"+ticker_lookup.upper()
            if print_local:
                tmp = await client.send_message(message.channel, ticker_lookup)
                await client.send_message(message.channel, embed = embed)
            else:
                tmp = await client.send_message(channels[channel_id_charting], ticker_lookup)
                await client.send_message(channels[channel_id_charting], embed = embed)
                await client.send_message(message.channel, author +": "+ticker_lookup + " posted in \"charting\"." )


    with open('users.json', 'r') as f:
        users = json.load(f)

    await update_data(users, message.author)
    if symbol_mentioned:
        await update_symbol_data(symbol)
        await add_experience(users, message.author, 1)
        await level_up(users, message.author, message.channel)

    with open('users.json', 'w') as f:
        json.dump(users, f)
    #$level command
    if message.content.startswith('$level'):
        with open('users.json', 'r') as f:
            users = json.load(f)

        await get_level(users, message.author, message.channel)

        with open('users.json', 'w') as f:
            json.dump(users, f)
    #$board command
    if message.content.startswith('$board'):
        if str(message.channel) == 'test-room':
            with open('users.json', 'r') as f:
                users = json.load(f)
            await print_leaderboard(users, message.channel)
            with open('users.json', 'w') as f:
                json.dump(users, f)

    if message.content.startswith('$ranks'):
        await print_symbol_board(message.channel)

    if message.content.startswith('$reset'):
        if str(message.channel) == 'test-room':
            empty_set = {}
            with open('symbols.json', 'w') as f:
                json.dump(empty_set, f)

            with open('picks.json', 'w') as f:
                json.dump(empty_set, f)

    if message.content.startswith('$picks'):
        await set_picks(full_split_content, message.author, channels)

    if message.content.startswith('$allpicks'):
        await print_picks(message.channel)

    if message.content.startswith('$mypicks'):
        await print_my_picks(message.author, message.channel)

    if message.content.startswith('$yourpicks'):
        if len(full_split_content) > 1:
            user_mention = full_split_content[1]
            if user_mention[0:2] == '<@':
                await print_your_picks(user_mention, message.channel)

    if message.content.startswith('$commands'):
        print(str(command_array))
        await client.send_message(message.channel, 'Please see \"user-commands\" for more details\n' + str(command_array) )

async def print_your_picks(trader, channel):
    with open('picks.json', 'r') as f:
        picks = json.load(f)
    trader_id = trader[2: len(trader)-1]

    if not trader_id in picks:
        await client.send_message(channel, trader + " has not made any picks.")
    else:
        user_picks = str(picks[trader_id]['picks'])
        await client.send_message(channel, trader + '\'s picks are :\t' + user_picks)


    with open('picks.json', 'w') as f:
        json.dump(picks, f)

async def print_my_picks(trader, channel):
    with open('picks.json', 'r') as f:
        picks = json.load(f)

    name = picks[trader.id]['name']
    picks = str(picks[trader.id]['picks'])

    await client.send_message(channel, name + '\'s picks are :\t' + picks)

async def update_picks_data(trader, trader_picks):
    with open('picks.json', 'r') as f:
        picks = json.load(f)

    if trader.id not in picks:
        picks[trader.id] = {}
        picks[trader.id]['name'] = trader.mention
        picks[trader.id]['picks'] = trader_picks
    else:
        old_picks = picks[trader.id]['picks']
        new_picks = old_picks + trader_picks
        picks[trader.id]['picks'] = new_picks

    with open('picks.json', 'w') as f:
        json.dump(picks, f)

async def print_picks(channel):
    with open('picks.json', 'r') as f:
        picks = json.load(f)

    await client.send_message(channel, "Current Trader Picks:\n")

    for trader in picks:
        await client.send_message(channel, picks[trader]['name'] + '\'s picks are:\t' + str(picks[trader]['picks']))

    print(picks)

async def set_picks(picks, trader, channels):
    channel_id_picks = 0
    for channel_name in channels:
        if str(channel_name) == "user-daily-picks":
            break
        channel_id_picks += 1

    valid_picks = []
    for pick in picks:
        ticker = pick
        if ticker[0] == '$':
            ticker = ticker[1: len(ticker)]
        if ticker.upper() in symbol_array:
            valid_ticker = "$" + ticker.upper()
            valid_picks.append(valid_ticker)

    if len(valid_picks) > 0:
        await update_picks_data(trader, valid_picks)
        await client.send_message(channels[channel_id_picks], '\n' + trader.mention + '\'s tickers to watch are:\n')
        count = 1
        for pick in valid_picks:
            await client.send_message(channels[channel_id_picks], '#' + str(count) + '\t' + pick + '\n')
            count += 1

async def update_symbol_data(symbol):
    with open('symbols.json', 'r') as f:
        symbols = json.load(f)

    if not symbol in symbols:
        symbols[symbol] = {}
        symbols[symbol]['symbol'] = symbol
        symbols[symbol]['count'] = 1
    else:
        symbols[symbol]['count'] += 1

    with open('symbols.json', 'w') as f:
        json.dump(symbols, f)

async def print_symbol_board(channel):
    with open('symbols.json', 'r') as f:
        symbols = json.load(f)

    symbols_sorted = []
    for symbol in symbols:
        symbols_sorted.append([symbols[symbol]['count'], symbols[symbol]['symbol']])

    symbols_sorted.sort(reverse=True)
    counter = 0
    await client.send_message(channel, 'The top mentioned tickers are:')
    while counter < 10 and len(symbols_sorted) > counter:
        mentions = str(symbols_sorted[counter][0])
        ticker = symbols_sorted[counter][1]
        await client.send_message(channel, '\n#'+ str(counter+1) +': \t${} with {} mentions'.format(ticker,mentions))
        counter += 1

    #print(symbols_sorted)

    with open('symbols.json', 'w') as f:
        json.dump(symbols, f)

async def print_leaderboard(users, channel):
    for user in users:
        name = users[user]['name']
        exp = users[user]['experience']
        inv = users[user]['invites']
        await client.send_message(channel, 'Name: {}.\tTicker Mentions: {}.\t Invites: {}.\n'.format(name, exp, inv))

async def update_invite_data(invites_old, invite, users):
    if not invite.id in invites_old:
        invites_old[invite.id] = {}
        invites_old[invite.id]["inviter"] = str(invite.inviter)
        invites_old[invite.id]["id"] = invite.id
        invites_old[invite.id]["uses"] = invite.uses
        if (invite.uses > 0):
            await add_invite(invite, users)
    else:
        if invites_old[invite.id]["uses"] < invite.uses:
            await add_invite(invite, users)
        invites_old[invite.id]["uses"] = invite.uses

async def get_level(users, user, channel):
    exp = users[user.id]['experience']
    inv = users[user.id]['invites']
    await update_data(users,user)
    await client.send_message(channel, 'Hello {}, your current ticker mentions are {} and invites to the room are {}. Keep grinding!\n\nRemember it takes 30 seconds between actions to gain ticker mentions.'.format(user.mention,exp, inv))

async def add_invite(invite, users):
    user = invite.inviter
    users[user.id]['invites'] += 1

async def update_data(users,user):
    if not user.id in users:
        users[user.id] = {}
        users[user.id]['name'] = str(user)
        users[user.id]['experience'] = 0
        users[user.id]['level'] = 1
        users[user.id]['invites'] = 0
        users[user.id]['time'] = time.time()

async def add_experience(users, user, exp):
    now = time.time()
    last_time = users[user.id]['time']
    if (now - last_time) > 30:
        users[user.id]['experience'] += exp
        users[user.id]['time'] = now

async def level_up(users, user, channel):
    experience = users[user.id]['experience']
    current_level = users[user.id]['level']
    invites = users[user.id]['invites']

    if experience >= 100 and current_level < 2 and invites >= 1:
        await client.send_message(channel, '{} is now a member of {}, well done trader!'.format(user.mention, 'meso'))
        users[user.id]['level'] = 2
        role = discord.utils.get(user.server.roles, name='meso')
        await client.add_roles(user, role)

    if experience >= 400 and current_level < 3 and invites >= 3:
        await client.send_message(channel, '{} is now a member of {}, the air is getting thin up here.'.format(user.mention, 'thermo'))
        users[user.id]['level'] = 3
        role = discord.utils.get(user.server.roles, name='thermo')
        await client.add_roles(user, role)

    if experience >= 800 and current_level < 4 and invites >= 5:
        await client.send_message(channel, '{} is now a member of {}, look at all those ants at their day jobs.'.format(user.mention, 'exo'))
        users[user.id]['level'] = 4
        role = discord.utils.get(user.server.roles, name='exo')
        await client.add_roles(user, role)

    if experience >= 1200 and current_level < 5 and invites >= 7:
        await client.send_message(channel, '{} is now a member of {}, welcome to space moon-walker$$$$$.'.format(user.mention, 'moon'))
        users[user.id]['level'] = 5
        role = discord.utils.get(user.server.roles, name='moon')
        await client.add_roles(user, role)

client.run(TOKEN)
