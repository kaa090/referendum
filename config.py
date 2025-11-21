import logging

FILE_LOG = "referendums.log"
FILE_DB = "referendums.db"
FILE_README = "readme.txt"
FILE_HELP = "help.txt"
LEVEL = logging.INFO	#restart if changed. LEVEL = [DEBUG, INFO, WARNING, ERROR, CRITICAL]

RFR_GAME = 0
RFR_GAME_CMD = 'game'
RFR_SINGLE = 1
RFR_SINGLE_CMD = 'single'
RFR_MULTI = 2
RFR_MULTI_CMD = 'multi'
RFR_GAME2 = 3
RFR_GAME2_CMD = 'game2'

BUTTON_ID_YES = 1
BUTTON_ID_NO = 2
BUTTON_ID_Q = 3
BUTTON_ID_ADD = 4
BUTTON_ID_DEL = 5
BUTTON_ID_OPT = 6

PLAYER_TYPE_USUAL   = 0
PLAYER_TYPE_REGULAR = 1
PLAYER_TYPE_BANNED  = 2