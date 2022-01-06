#! /bin/python3

from bs4.element import ResultSet
from bs4 import BeautifulSoup
from urllib.parse import unquote

import sys
import os
import requests
import logging
getDefaultRows: bool = True #get default (white) rows on nyaa
getDangerRows: bool = True #get danger (red) rows on nyaa
TUImode: bool = False #use a tui instead of dmenu
useTor: bool = True #use tor network if getting ConnectionResetError
loggingLevel: int = logging.INFO #print debug
baseUrl: str = 'https://nyaa.si/?s=seeders&o=desc' #base url (by default searches by most seeders)
webtorrentArgs: str = "--keep-seeding --mpv" #args (by default starts mpv)
maxPageNum: int = 5 #max page to get on nyaa (by default 5), if your number is too big you may encounter some delay
dmenuArgs = {"font": "Ubuntu-15"} #additional args for dmenu

if not TUImode:
    import dmenu

if useTor:
    import time


logging.basicConfig()
logging.getLogger().setLevel(loggingLevel)

def getRows(soup : BeautifulSoup, getDefault = getDefaultRows, getDanger = getDangerRows) -> ResultSet:
    rows = soup.find_all('tr', class_='success')
    if getDefault:
        rows += soup.find_all('tr', class_='default')
    if getDanger:
        rows += soup.find_all('tr', class_='danger')
    return rows

def get_tor_session():
    session = requests.session()
    # Tor uses the 9050 port as the default socks port
    session.proxies = {'http':  'socks5://127.0.0.1:9050',
                       'https': 'socks5://127.0.0.1:9050'}
    return session

def getTorrents(url: str) -> dict:
    torrents = []
    count = 0
    for pageNum in range(1, maxPageNum): 
        pageUrl = f"{url}&p={str(pageNum)}"
        logging.info(f"Getting page {str(pageNum)} with url {pageUrl}")

        if useTor:    
            s = get_tor_session()
        try:
            if useTor:
                pageHtml = s.get(pageUrl)
            else:
                pageHtml = requests.get(pageUrl)
        except:
            continue

        soup = BeautifulSoup(pageHtml.text, 'html.parser')
        logging.info(f"Got page {str(pageNum)} !")

        rows = getRows(soup)
        logging.info(f"Got {str(len(rows))} rows from page {str(pageNum)}")

        for row in rows:
            td = row.find_all('td', class_='text-center')
            links = td[0].find_all('a')
            size = td[1]

            # size = next((x for x in td if "GiB" in x.text or "$MiB" in x.text), None)
            try:
                size = "[" + size.get_text() + "] "
            except:
                size = ""

            magnet = unquote(links[1]['href'])
            name = row.find_all('a',text=True)[0].get_text()
            torrents.append({"name": size + name, "magnet": magnet})

        if len(rows) == 0:
            break

    print(count)
    return torrents

def _choiceD(dict: dict, subElem = "") -> str:
    choice = dmenu.show((x.get(subElem) for x in dict), lines=25, **dmenuArgs)
    return next((x for x in dict if x.get(subElem) == choice), None)

def _choiceT(dict: dict, subElem = "") -> str:
    elems = list((x.get(subElem) for x in dict))
    elemsReverse = list(elems)
    elemsReverse.reverse()
    for i, elem in enumerate(elemsReverse):
        print(f"{str(len(elems) - i)}: {elem}")
    #seems to be working
    index = int(input("Enter your choice: ")) -1
    
    return dict[index]

def choice(dict: dict, subElem = "") -> str: #lazy
    if TUImode:
        return _choiceT(dict, subElem)
    return _choiceD(dict, subElem)

def ask(prompt: str) -> str:
    if TUImode:
        return input(prompt)
    return dmenu.show([], prompt=prompt, **dmenuArgs)
    

if __name__ == '__main__':

    if useTor:
        os.system('sudo systemctl start tor')
        time.sleep(0.1)
    query = " ".join(sys.argv[1:]).replace(" ", "+")
    if len(query) == 0:
        query = ask("Search tags: ").replace(" ", "+")

    torrents = getTorrents(f"{baseUrl}&q={query}")
    logging.info(f"Got {str(len(torrents))} total entries")
    if len(torrents) == 0:
        sys.exit(1)

    if useTor:
        os.system('sudo systemctl stop tor')
    magnet = choice(torrents, subElem="name").get("magnet")
    logging.info(f"Got magnet link: {magnet}")
    
    logging.info("Loading webtorrent")
    if os.name == "posix":
        os.system(f"webtorrent \"{magnet}\" {webtorrentArgs}")
    else:
        print("TODO: find how to run webtorrent-cli on windows. don't make an issue for this except if it's been 2 months since the last commit")
        #os.system(f"./webtorrent \"{magnet}\" {webtorrentArgs}")
