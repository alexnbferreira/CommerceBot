# -*- coding: utf-8 -*-
import datetime
import json
import time
from decimal import Decimal
from functools import wraps
import logging
import requests
import telegram
import yaml
from requests.auth import HTTPBasicAuth
from telegram.ext import CommandHandler, Dispatcher, Updater

token = ""
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

try:
    with open("config.yaml", "r") as config_file:
        config = yaml.load(config_file)
        token = config["token"]
        git_user = config["git"]["user"]
        git_password = config["git"]["password"]
        tg_url = "https://api.telegram.org/bot{token}/".format(token=token)
        auth = HTTPBasicAuth(git_user, git_password)
except Exception as e:
    log.info (e)
    exit(-1)

    
git_url = "https://api.github.com/"
git_link = "https://github.com/"
cmc_link = "https://api.coinmarketcap.com/v2/ticker/2650/"
git_file = "gits.json"



class CBTBot:

    last_commit = None
    last_repo = None
    repos = []
    bot = None
    subscribers = []

    def __init__(self, git_user):
        self.git_user = git_user
        self.git_link = git_link + self.git_user
        self.get_repos()
        self.bot = telegram.Bot(token=token)
        self.updater = Updater(token=token)
        self.dispatcher = self.updater.dispatcher
        self.dispatcher.add_handler(
            CommandHandler("subscribe", self.add_subscriber))
        self.dispatcher.add_handler(CommandHandler(
            "unsubscribe", self.remove_subscriber))
        self.dispatcher.add_handler(CommandHandler("start", self.welcome))
        self.dispatcher.add_handler(
            CommandHandler("price", self.get_current_price))
        self.dispatcher.add_handler(CommandHandler(
            "ethprice", self.get_current_eth_price))
        self.dispatcher.add_handler(CommandHandler(
            "btcprice", self.get_current_btc_price))
        self.fetch_subs()
        self.updater.start_polling()

    def get_repos(self):
        self.repos = []
        self.last_commit = None
        self.last_repo = None
        if self.git_user is None:
            return 0
        else:
            r = requests.get(git_url + "users/" + self.git_user + "/repos", auth=auth)
            r = r.json()
            for repo in r:
                self.repos.append(repo["name"])
                if self.last_commit is None or repo["pushed_at"] > self.last_commit:
                    self.last_commit = repo["pushed_at"]
                    self.last_repo = repo["name"]
            log.info ("Finished cycling repos. Last updated repo was {} at {}".format(self.last_repo, self.last_commit))

    def is_admin_message(self, update):
        msg = update["message"]
        user = msg.from_user.id
        chat = msg.chat.id
        if chat == user:
            log.info ("Private Chat")
            return True
        admins = self.bot.get_chat_administrators(chat)
        for adm in admins:
            if user == adm.user.id:
                return True
        return False

    def fetch_subs(self):
        fp = open(git_file, "r")
        try:
            parsed_file = json.load(fp)
            self.subscribers = parsed_file["subscribers"]
        except Exception as e:
            log.info (e)
            self.write_subs()
            self.subscribers = []

        fp.close()

    def write_subs(self):
        with open(git_file, "w") as of:
            dic = {}
            dic["subscribers"] = self.subscribers
            of.write(json.dumps(dic))

    def welcome(self, bot, update):
        log.info ("Sending welcome text with available commands")
        text = "Hello\n\nMy name is CommerceBot! I am pretty simple to use:\n/subscribe to start receiving notifications for every commit that CBT submits.\n/unsubscribe to remove that subscription.\n/price to get info on the latest USD price!\n/ethprice Same as /price, converted to ETH\n/btcprice Same as /price, converted to BTC\n\nGood Luck!"
        self.bot.send_message(chat_id=update.message.chat_id,
                              text=text, parse_mode=telegram.ParseMode.MARKDOWN)

    def add_subscriber(self, bot, update):
        log.info ("Trying to add a new subscriber...")
        id = update.message.chat_id
        if not self.is_admin_message(update):
            log.info ("Not admin")
            self.bot.send_message(
                chat_id=id, text="This command is reserved for chat administators. If you wish to receive notifications privately, please send me a direct message.")
            return 0
        exists = id in self.subscribers
        log.info ("Subscriber exists? {}".format(id in self.subscribers))
        if not exists:
            log.info ("Adding Subscriber...")
            self.subscribers.append(id)
            self.write_subs()
            text = "Subscription completed successfully. I will now notify of new commits that happen on CBT's Github."
            self.bot.send_message(chat_id=id, text=text,
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            log.info ("Sub already exists...")
            text = "This channel/user is already subscribed to the notification system."
            self.bot.send_message(chat_id=id, text=text,
                                  parse_mode=telegram.ParseMode.MARKDOWN)

    def remove_subscriber(self, bot, update):
        log.info ("Trying to remove a subscriber...")
        id = update.message.chat_id
        if not self.is_admin_message(update):
            log.info ("Not admin")
            self.bot.send_message(
                chat_id=id, text="This command is reserved for chat administators. If you wish to receive notifications privately, please send me a direct message.")
            return 0
        exists = id in self.subscribers
        log.info ("Subscriber exists? {}".format(id in self.subscribers))
        if exists:
            self.subscribers.remove(id)
            self.write_subs()
            text = "You have successfully unsubscribed from CBT's GitHub notifications."
            self.bot.send_message(chat_id=id, text=text,
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            text = "You haven't subscribed to CBT's GitHub notifications."
            self.bot.send_message(chat_id=id, text=text,
                                  parse_mode=telegram.ParseMode.MARKDOWN)

    def get_current_price(self, bot, update, currency="$"):
        log.info ("Fetching current price")
        id = update.message.chat_id
        log.info (cmc_link + ("" if currency == "$" else "?convert={}".format(currency)))
        obj = json.loads(requests.get(cmc_link + ("" if currency ==
                                                  "$" else "?convert={}".format(currency))).text, parse_float=Decimal)
        search_in = "USD" if currency == "$" else currency
        cmc_price = obj["data"]["quotes"][search_in]["price"]
        cmc_change = obj["data"]["quotes"][search_in]["percent_change_24h"]
        up_down = "Up" if cmc_change > 0 else "Down"
        text = "CBT's last price: {} {}.\n{} {}% in the last 24 hours.".format(
            currency, cmc_price, up_down, cmc_change)
        self.bot.send_message(chat_id=id, text=text)

    def get_current_eth_price(self, bot, update):
        self.get_current_price(bot, update, currency="ETH")

    def get_current_btc_price(self, bot, update):
        self.get_current_price(bot, update, currency="BTC")
    
    def check_updates(self):
        for repo in self.repos:
            url = git_url + "repos/" + self.git_user + "/" + repo
            repo_info = requests.get(url, auth=auth).json()
            if repo_info["pushed_at"] > self.last_commit:
                log.info ("Found an update!")
                self.last_commit = repo_info["pushed_at"]
                self.last_repo = repo
                return True
        return False

    def send_updated_commit(self):
        text = "New commit on repository {}. [Check it out!]({})".format(
            self.last_repo, self.git_link + "/" + self.last_repo)
        log.info (text)
        for sub in self.subscribers:
            self.bot.send_message(chat_id=sub, text=text,
                                  parse_mode=telegram.ParseMode.MARKDOWN)


if __name__ == "__main__":
    log.info ("Starting CommerceBlock git bot...")
    bot = CBTBot("commerceblock")
    while True:
        if bot.check_updates():
            bot.send_updated_commit()
        time.sleep(60)
