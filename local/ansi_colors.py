"""
Provides constants for the basic ANSI color code escape sequences.
"""


FG_BLACK   = "\x1b[30m"
FG_RED     = "\x1b[31m"
FG_GREEN   = "\x1b[32m"
FG_YELLOW  = "\x1b[33m"
FG_BLUE    = "\x1b[34m"
FG_MAGENTA = "\x1b[35m"
FG_CYAN    = "\x1b[36m"
FG_WHITE   = "\x1b[37m"

FG_HI_BLACK   = "\x1b[90m"
FG_HI_RED     = "\x1b[91m"
FG_HI_GREEN   = "\x1b[92m"
FG_HI_YELLOW  = "\x1b[93m"
FG_HI_BLUE    = "\x1b[94m"
FG_HI_MAGENTA = "\x1b[95m"
FG_HI_CYAN    = "\x1b[96m"
FG_HI_WHITE   = "\x1b[97m"

RESET     = "\x1b[0m"


FG_SELECTION = [
    FG_RED   , FG_GREEN   , FG_YELLOW   , FG_BLUE   , FG_MAGENTA   , FG_CYAN   , FG_WHITE   ,
    FG_HI_RED, FG_HI_GREEN, FG_HI_YELLOW, FG_HI_BLUE, FG_HI_MAGENTA, FG_HI_CYAN, FG_HI_WHITE,
]
