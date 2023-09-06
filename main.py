import scratchconnect as sc
import html
import time
import threading
import os
from dotenv import load_dotenv

load_dotenv()

# https://stackoverflow.com/questions/2697039/python-equivalent-of-setinterval/48709380#48709380
class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = threading.Event()
        thread = threading.Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime = time.time() + self.interval
        while not self.stopEvent.wait(nextTime - time.time()):
            nextTime += self.interval
            self.action()

    def cancel(self):
        self.stopEvent.set()


def encode_string(string):
    string = html.unescape(string)
    string = string.replace('\t', 'ₜ')
    string = string.replace('\n', 'ₙ')

    chars = list(
        'ₜₙ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'
    )
    encoded_string = ""
    for char in string:
        if char not in chars:
            encoded_string += '98'  # unsupported char
            continue
        encoded_string += str(chars.index(char) + 1).zfill(2)

    if len(encoded_string) > 254:
        encoded_string = encoded_string[:254] + '00'

    return encoded_string


def connect_cloud():
    global CLOUD
    CLOUD = PROJECT.connect_cloud_variables()


def fetch_all_comments():
    try:
        offset = 0
        limit = 40
        comments = []
        while True:
            batch = PROJECT.comments(limit=limit, offset=offset)[0]
            comments += batch
            if len(batch) != 40:
                break
            offset += 40
        return comments
    except:
        return fetch_all_comments()


def update_title():
    comment_count = len(fetch_all_comments())
    print(
        f"Updating title: {comment_count} comment{'s' if comment_count != 1 else ''}"
    )
    PROJECT.set_title(
        f"This project has {len(fetch_all_comments())} comment{'s' if comment_count != 1 else ''}"
    )


def get_cloud_var(name, limit=1):
    try:
        return CLOUD.get_cloud_variable_value(name, limit)
    except:
        return get_cloud_var(name, limit)


def set_cloud_var(name, value):
    try:
        CLOUD.set_cloud_variable(name, value)
    except:
        set_cloud_var(name, value)

USER = sc.ScratchConnect(os.getenv('name'), os.getenv('password'))
PROJECT = USER.connect_project(os.getenv('project'), False)
COMMENT_LIMIT = int(os.getenv('comment_limit'))

interval = setInterval(600, update_title)
"""
request = "" => no request
request = "0" => front end processing request
request = "1xxx" => requesting username with offset xxx
request = "2xxx" => requesting content with offset xxx
"""

connect_cloud()
CLOUD.start_event()

set_cloud_var('REQUEST', '')


def handle_request():
    while True:
        request = str(get_cloud_var('REQUEST')[0])
        if request == "0":
            time.sleep(5)
            connect_cloud()
            request = str(get_cloud_var('REQUEST')[0])
            if request == "0":
                set_cloud_var('REQUEST', '')
                continue
        if request == "" or len(request) == 0:
            continue
        print('Valid request:', request)

        if request[0] in ["1", "2"]:
            connect_cloud()
            PROJECT.update_data()
            comments = PROJECT.comments(limit=COMMENT_LIMIT,
                                        offset=(int(request[1:])))[0]

            request = request[0]
            for i in range(COMMENT_LIMIT):
                if i >= len(comments):
                    set_cloud_var(str(i + 1), "")
                    continue

                elif request == '1':
                    set_cloud_var(
                        str(i + 1),
                        encode_string(comments[i]['author']['username']))
                elif request == '2':
                    set_cloud_var(str(i + 1),
                                    encode_string(comments[i]['content']))

            set_cloud_var('REQUEST', "0")


# wow wasnt this fun
thread = threading.Thread(target=handle_request)
thread.start()
while True:
    thread.join(timeout=0.0)
    if not thread.is_alive():
        print('Thread died, restarting')
        thread = threading.Thread(target=handle_request)
        thread.start()