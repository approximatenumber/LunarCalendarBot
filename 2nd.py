from telegram import Updater, TelegramError, Update, Bot
import logging
import os
import re
import sys
from tinydb import TinyDB, Query
from tinydb.queries import where
from tinydb.operations import delete
from tinydb.storages import MemoryStorage
from threading import Thread
from time import sleep
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.error import URLError

try:
    sys.path.append('.private')
    from config import TOKEN       # importing secret TOKEN
except ImportError:
    print("need TOKEN from .private/config.py")
    raise SystemExit

URL = 'http://www.oracle-today.ru/moon'
TIMEOUT = 600
CHATS = 'chats.json'
log_file = "bot.log"
logging.basicConfig(level = logging.WARNING, filename=log_file, format='%(asctime)s:%(levelname)s - %(message)s')
logging.FileHandler(log_file, mode='w')


def main(**args):

    def start(bot, update):
        message = update.message
        chat_id = message.chat.id
        if not db.contains(chats_q.chat_id == chat_id):
            db.insert({'chat_id': chat_id})
            text = 'Вы подписаны на рассылку лунного гороскопа.'
            bot.sendMessage(chat_id=chat_id, text=text)
            logging.warning('%s added' % chat_id)

    def stop(bot, update):
        message = update.message
        chat_id = message.chat.id
        if db.contains(chats_q.chat_id == chat_id) is True:
            db.remove(chats_q.chat_id == chat_id)
            text = 'Вы отписались от рассылки лунного гороскопа.'
            bot.sendMessage(chat_id=chat_id, text=text)
            logging.warning('%s removed' % chat_id)

    def oracle_read():
        try:
            oracle = open('oracle', 'r').read()
            return oracle
        except Exception:
            return False

    def oracle_write(oracle):
        with open('oracle', 'w') as file:
            file.write(oracle)
    try:
        chat_db = TinyDB(CHATS)
    except ValueError:
        os.remove(CHATS)
        chat_db = TinyDB(CHATS)
    chats_q = Query()

    updater = Updater(TOKEN, workers=2)
    dp = updater.dispatcher
    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("stop", stop)
#    dp.addErrorHandler(error)
    update_queue = updater.start_polling(poll_interval=1, timeout=5)

    while True:
        soup = BeautifulSoup(urlopen(URL), 'html.parser')
        oracle_upd = soup.findAll('div', {'class': 'informer_active'})[0].getText().replace('\r','')
        if oracle_upd != oracle_read():
            logging.warning('oracle updated')
            oracle_write(oracle_upd)
            for chat_ids in db.all():
                    for chat_id in chat_ids:
                        Bot(token=TOKEN).sendMessage(chat_id=chat_ids[chat_id], text=oracle_upd)
                        logging.warning('%s notified' % chat_id)
        sleep(TIMEOUT)


if __name__ == '__main__':
    main()
