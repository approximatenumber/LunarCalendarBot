#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Exit codes of functions addUser() and delUser():
# 0 - well done
# 1 - something goes wrong
# 3 - no such user
# 4 - user is already in database

# importing modules
import telegram, configparser, logging, os, sys, re
from threading import Thread
from time import sleep, localtime
from bs4 import BeautifulSoup
try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen                          # python 2 (raspbian)
try:
    from urllib.error import URLError
except ImportError:
    from urllib2 import URLError                                # python 2 (raspbian)
try:
    sys.path.append('.private'); from config import TOKEN       # importing secret TOKEN
except ImportError:
    print("need TOKEN from .private/config.py")
    sys.exit(1)

# variables
user_db = "user_db"
news = "last_news"
TIMEOUT = 1200 # 20 mins
URL = "http://horoscopes.rambler.ru/moon/"
log_file = "bot.log"
start_time = 12
stop_time = 13


def main():
    logging.basicConfig(level = logging.WARNING,filename=log_file,format='%(asctime)s:%(levelname)s - %(message)s')

    sendMessage = lambda chat_id, msg: bot.sendMessage(chat_id, msg)

    getCurrentNews = lambda: open(news, 'r').read()

    def notificateUser():
        while True:
            if start_time <= localtime()[3] <= stop_time and getLastNews() == 0:       # there are new message and time is between 12:00 and 13:00 am
                with open(user_db,'r') as file:
                    for chat_id in file.read().splitlines():
                        msg = getCurrentNews()
                        sendMessage(chat_id, msg)
                        logging.warning('user with chat_id %s is notified' % chat_id)
            sleep(TIMEOUT)
        return 0
    
    def getLastNews(): 
        try:
            soup = BeautifulSoup(urlopen(URL), "html.parser")
            # get last message with bs (some magic :-| )
            new_message_date = soup.findAll("div", {"class":"b-content__date"})[0].getText().replace('        ', '').replace('\n\xa0/\xa0','/')
            new_message_text = soup.findAll("div", {"class":"b-content__text"})[0].getText()
            new_message = new_message_date + new_message_text
            old_message = getCurrentNews()
            if new_message not in old_message:
                # got new message, so update the file
                with open(news, 'w') as file:
                    file.write(new_message)
                    logging.warning('got new message, news updated')
                    return 0
            else:                                                               # file and variable are the same, so no news
                return 1
        except Exception as error:
            logging.error('some problems with getLastNews(): %s' % error)
            sleep(30)
            return 1
  
    def echo(bot, update_id):                                                       # Request updates after the last update_id
        for update in bot.getUpdates(offset=update_id, timeout=10):                 # chat_id is required to reply to any message
            chat_id = update.message.chat_id
            update_id = update.update_id + 1
            message = update.message.text

            if message == "/start":                                                 # Reply to the start message
                if addUser(chat_id) == 0:
                    msg = "Вы подписаны на ежедневную рассылку лунного гороскопа от \
                                \"Рамблер.Гороскопы\".  Это сегодняшний прогноз:" + getCurrentNews()
                    sendMessage(chat_id, msg)
                elif addUser(chat_id) == 4:
                    msg = "Вы уже подписаны на рассылку!"
                    sendMessage(chat_id, msg)
                else:
                    msg = "У нас что-то пошло не так..."
                    sendMessage(chat_id, msg)
            elif message == "/stop":                                                # Reply to the message
                if delUser(chat_id) == 0:
                    msg = "Вы отписались от рассылки Рамблер.Гороскопы."
                    sendMessage(chat_id, msg)
                elif delUser(chat_id) == 3:
                    msg = "А Вы не подписаны на рассылки Рамблер.Гороскопы."
                    sendMessage(chat_id, msg)
                else:
                    msg = "У нас что-то пошло не так..."
                    sendMessage(chat_id, msg)
            elif message:
                msg = "Напишите /start или /stop."
                sendMessage(chat_id, msg)
        return update_id  

    def addUser(chat_id):
        try:
            if os.path.exists(user_db):
                with open(user_db,'r') as file:
                    if str(chat_id) in file.read().splitlines():
                        logging.warning('user %s already in database' % chat_id)
                        return 4
                        pass
                    else:
                        with open(user_db,'a') as file:
                            file.write(str(chat_id) + '\n')
                        logging.warning('added %s' % chat_id)
                        return 0
            else:                                                                       # db does not exist
                with open(user_db,'w') as file:
                    file.write(str(chat_id) + '\n')
                logging.warning('DB created! added %s' % chat_id)
                return 0
        except Exception:
            logging.error('addUser(): some problems with %s while' % chat_id)
            return 1
  
    def delUser(chat_id):
        try:
            if os.path.exists(user_db):
                users = open(user_db).read()
                if str(chat_id) in users:                                                 # if chat_id in user_db,..
                    new_user_db = open(user_db,"w")
                    new_user_db.write(re.sub(str(chat_id) + '\n','', users))                # ..so delete it
                    new_user_db.close()
                    logging.warning('%s is deleted' % chat_id)
                    return 0
                else:
                    logging.warning('no such user: %s' % chat_id)
                    pass
                    return 3
            else:                                                                       # db does not exist
                open(user_db, 'w').close()
                logging.warning('no such user: %s' % chat_id)
                return 3
        except Exception:
            logging.error('delUser(): some problems with %s' % chat_id)
            return 1

# initialization
    for file in news, user_db:
        if not os.path.exists(file):
            open(file, 'w').close()
            logging.warning('file %s created' % file)
    open(log_file, 'w').close()
    logging.warning('bot started...')

    bot = telegram.Bot(TOKEN)
    try:
        update_id = bot.getUpdates()[0].update_id
    except IndexError:
        update_id = None

# body
    t = Thread(target=notificateUser)
    t.daemon = True
    t.start()

    while True:
        try:
            update_id = echo(bot, update_id)
        except telegram.TelegramError as e:
            # These are network problems with Telegram.
            if e.message in ("Bad Gateway", "Timed out"):
                sleep(1)
            elif e.message == "Unauthorized":
                # The user has removed or blocked the bot.
                update_id += 1
            else:
                raise e
        except URLError as e:
            # These are network problems on our end.
            sleep(1)

if __name__ == '__main__':
    main()
