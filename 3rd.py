from telegram import Bot, TelegramError
from telegram.ext import Updater, CommandHandler
import logging
import os
import sys
import pickledb as pkl
from time import sleep
from bs4 import BeautifulSoup
from urllib.request import urlopen

try:
    sys.path.append('.private')
    from config import TOKEN  # importing secret TOKEN
except ImportError:
    print("need TOKEN from .private/config.py")
    raise SystemExit

URL = 'http://www.oracle-today.ru/moon'
TIMEOUT = 600
chat_file = 'chats.db'
oracle_file = 'oracle.db'


class Chats():
    def __init__(self, chat_file):
        self.chat_db = pkl.load(chat_file, False)
        try:
            num = self.chat_db.llen('chats')
            logging.warning('chats in DB: %s' % num)
        except KeyError:
            self.chat_db.lcreate('chats')
            logging.warning('chat DB created')

    def add(self, chat_id):
        self.chat_db.ladd('chats', chat_id)
        self.chat_db.dump()

    def remove(self, chat_id):
        for num in range(self.chat_db.llen('chats')):
            if chat_id == self.chat_db.lget('chats', num):
                self.chat_db.lpop('chats', num)
                self.chat_db.dump()

    def contains(self, chat_id):
        for num in range(self.chat_db.llen('chats')):
            if chat_id == self.chat_db.lget('chats', num):
                return True
            return False

    def getall(self):
        return self.chat_db.lgetall('chats')


class Oracle():
    def __init__(self, oracle_file):
        self.oracle_db = pkl.load(oracle_file, False)
        if not self.oracle_db.get('oracle'):
            self.oracle_db.set('oracle', 'empty')

    def read(self, key):
        value = self.oracle_db.get(key)
        return value

    def store(self, key, value):
        self.oracle_db.set(key, value)
        self.oracle_db.dump()

    def download(self):
        soup = BeautifulSoup(urlopen(URL), 'html.parser')
        oracle = soup.findAll('div', {'class': 'informer_active'})[0].getText().replace('\r', '')
        return oracle

    def check_update(self, old, new):
        if old != new:
            return True
        else:
            return False


def main(**args):
    def init_log(log_file):
        logging.basicConfig(level=logging.WARNING, filename=log_file, format='%(asctime)s:%(levelname)s - %(message)s')
        logging.FileHandler(log_file, mode='w')
        logger = logging.getLogger(__name__)

    def start(bot, update):
        message = update.message
        chat_id = message.chat.id
        if not chats.contains(chat_id):
            chats.add(chat_id)
            text = 'Вы подписаны на рассылку лунного гороскопа!'
            bot.sendMessage(chat_id=chat_id, text=text)
            logging.warning('%s added' % chat_id)
        else:
            text = 'Вы уже подписаны!'
            bot.sendMessage(chat_id=chat_id, text=text)

    def stop(bot, update):
        message = update.message
        chat_id = message.chat.id
        if chats.contains(chat_id):
            chats.remove(chat_id)
            text = 'Вы отписались от рассылки лунного гороскопа!'
            bot.sendMessage(chat_id=chat_id, text=text)
            logging.warning('%s removed' % chat_id)
        else:
            text = 'Вы уже отписались!'
            bot.sendMessage(chat_id=chat_id, text=text)

    def send_msg(chat_id, text):
        try:
            Bot(token=TOKEN).sendMessage(chat_id, text)
        except TelegramError as err:
            if err.message == "Unauthorized":
                chats.remove(chat_id)
                logging.warning('chat_id %s blocked us. Removed' % chat_id)
            else:
                logging.error('Telegram error for chat_id %s: %s' % (chat_id, err))

    def error(bot, update, error):
        logging.warning('Update "%s" caused error "%s"' % (update, error))
        sleep(10)

    init_log('bot.log')

    oracle = Oracle(oracle_file)
    chats = Chats(chat_file)

    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_error_handler(error)
    updater.start_polling(poll_interval=1, timeout=10)

    while True:
        try:
            stored_oracle = oracle.read('oracle')
            downloaded_oracle = oracle.download()
            if oracle.check_update(stored_oracle, downloaded_oracle) is True:
                oracle.store('oracle', downloaded_oracle)
                for chat_id in chats.getall():
                    message = oracle.read('oracle')
                    send_msg(chat_id, message)
        except Exception as err:
            logging.error('Error while processing: %s' % err)
        sleep(TIMEOUT)


if __name__ == '__main__':
    main()
