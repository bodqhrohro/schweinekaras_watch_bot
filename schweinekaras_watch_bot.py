import requests
import telebot
import logging
from threading import Thread, Event
from collections import deque

logging.basicConfig(level=logging.INFO)

TOKEN = 'your_token'

NEBOARD_POSTING_INTERVAL = 20
NEBOARD_BASE = 'https://neboard.me/'
NEBOARD_POST_FILE_LIMIT = 5
NEBOARD_SWINE_THREAD_ID = 123456
NEBOARD_TRIPCODE = 'your_tripcode'

bot = telebot.TeleBot(TOKEN, threaded=False)

msg_queue = deque()

class Msg:
    def __init__(self, file_paths, caption):
        self.file_paths = file_paths
        self.caption = caption


class EditThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.timer = Event()

    def run(self):
        session = requests.Session()
        # obtain initial cookies
        session.get(NEBOARD_BASE)

        while not self.timer.wait(NEBOARD_POSTING_INTERVAL):
            while len(msg_queue) <= 0:
                self.timer.wait(1)

            msg = msg_queue.popleft()
            logging.info('Fetching files ' + ', '.join(msg.file_paths))
            files = [(
                path.split('/')[-1],
                requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(TOKEN, path)).content,
                'image/jpeg'
            ) for path in msg.file_paths]

            if len(files) > NEBOARD_POST_FILE_LIMIT:
                #TODO: postpone excessive files to the next post
                files = files[0:NEBOARD_POST_FILE_LIMIT]

            logging.info('Neboard request')
            post_result = session.post('{0}/api/post/{1}/'.format(NEBOARD_BASE, NEBOARD_SWINE_THREAD_ID), \
                    data = {
                        'title': '',
                        'tripcode': NEBOARD_TRIPCODE,
                        'text': msg.caption or '',
                        'attachment_urls': '',
                    }, files = [('attachments', file) for file in files])

            if post_result.status_code != 200:
                # failure, will try again
                logging.error((post_result.status_code, post_result.text))
                msg_queue.appendleft(msg)
            else:
                logging.info('Reposted files ' + ', '.join(msg.file_paths))



thread = EditThread()
thread.start()


@bot.channel_post_handler(content_types=['photo'])
def new_swine(message):
    logging.info('Got post {0}'.format(message.message_id))
    file_info = bot.get_file(message.photo[-1].file_id)
    msg_queue.append(Msg([file_info.file_path], message.caption))


while True:
    try:
        bot.polling(none_stop=True)
    except Exception as ex:
        logging.error(ex)
