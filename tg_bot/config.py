class Config(object):
    LOGGER = True

    # REQUIRED
    API_KEY = "1748849417:AAEgXw1McZEcZndKyirEu_gk3QKWqj-gAsQ"
    OWNER_ID = "1060318977" # If you dont know, run the bot and do /id in your private chat with it
    OWNER_USERNAME = "rsrmusic"

    # RECOMMENDED
    SQLALCHEMY_DATABASE_URI = 'mysql://root:EmJhTmNo9j3Q3lVlVXAM@containers-us-west-10.railway.app:6625/railway'  # needed for any database modules
    MESSAGE_DUMP = -1001465429519  # needed to make sure 'save from' messages persist
    LOAD = []
    NO_LOAD = ['translation', 'rss']
    WEBHOOK = False
    URL = None

    # OPTIONAL
    SUDO_USERS = []  # List of id's (not usernames) for users which have sudo access to the bot.
    SUPPORT_USERS = []  # List of id's (not usernames) for users which are allowed to gban, but can also be banned.
    WHITELIST_USERS = []  # List of id's (not usernames) for users which WONT be banned/kicked by the bot.
    DONATION_LINK = None  # EG, paypal
    CERT_PATH = None
    PORT = 8443
    DEL_CMDS = True  # Whether or not you should delete "blue text must click" commands
    STRICT_GBAN = True
    WORKERS = 8  # Number of subthreads to use. This is the recommended amount - see for yourself what works best!
    BAN_STICKER = 'CAADAgADOwADPPEcAXkko5EB3YGYAg'  # banhammer marie sticker
    ALLOW_EXCL = True # Allow ! commands as well as /
    STRICT_GMUTE = True

class Production(Config):
    LOGGER = False


class Development(Config):
    LOGGER = True
