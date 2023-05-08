# https://www.bet365.com.au/?#/AC/B19/C20459137/D50/E190002/F50/

import argparse
import collections
import logging
import re
import sys
import time

import asyncio
import socket
import websockets
from websockets.extensions import permessage_deflate


# ------------------------------------------------------------


# Instancia para registrar eventos.
logger = logging.getLogger(__name__)

# Configuración del registro de eventos.
# Se enviarán a la salida estándar con un nivel DEBUG.
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='\n>>>: %(message)s'
)


# -------------------------------------------------------------


class WebSocketClient():

    # longitud del mapa de caracteres.
    _MAP_LEN = 64

    # Mapa de caracteres.
    _char_map = [
        ["A", "d"], ["B", "e"], ["C", "f"], ["D", "g"], ["E", "h"], ["F", "i"], ["G", "j"],
        ["H", "k"], ["I", "l"], ["J", "m"], ["K", "n"], ["L", "o"], ["M", "p"], ["N", "q"], ["O", "r"],
        ["P", "s"], ["Q", "t"], ["R", "u"], ["S", "v"], ["T", "w"], ["U", "x"], ["V", "y"], ["W", "z"],
        ["X", "a"], ["Y", "b"], ["Z", "c"], ["a", "Q"], ["b", "R"], ["c", "S"], ["d", "T"], ["e", "U"],
        ["f", "V"], ["g", "W"], ["h", "X"], ["i", "Y"], ["j", "Z"], ["k", "A"], ["l", "B"], ["m", "C"],
        ["n", "D"], ["o", "E"], ["p", "F"], ["q", "0"], ["r", "1"], ["s", "2"], ["t", "3"], ["u", "4"],
        ["v", "5"], ["w", "6"], ["x", "7"], ["y", "8"], ["z", "9"], ["0", "G"], ["1", "H"], ["2", "I"],
        ["3", "J"], ["4", "K"], ["5", "L"], ["6", "M"], ["7", "N"], ["8", "O"], ["9", "P"],
        ["\n", ":|~"], ["\r", ""]
    ]

    _WSS_URLS_CONNECTION = 'wss://premws-pt3.365lpodds.com/zap/'
    _URLS_NSTTOKEN_ID = 'https://www.bet365.com.au/'

    # Configuración para las solicitudes que se realice.
    _REQ_EXTENSIONS = [permessage_deflate.ClientPerMessageDeflateFactory(
                server_max_window_bits=15,
                client_max_window_bits=15,
                compress_settings={'memLevel': 4},
            )]

    # Protocolo de la solicitud.
    _REQ_PROTOCOLS = ['zap-protocol-v3']

    # Objeto para definir los encabezados.
    R_HEADER = collections.namedtuple('Header','name value')

    # Encabezados de la solicitud.
    _REQ_HEADERS = [
            R_HEADER('Sec-WebSocket-Version', '13'),
            R_HEADER('Accept-Encoding', 'gzip, deflate, br'),
            R_HEADER('Pragma', 'no-cache'),
            R_HEADER('Cookie', 'rmbs=3; aps03=cf=N&cg=1&cst=0&ct=13&hd=N&lng=30&tzi=29; __cf_bm=sMEFTlsTiiKz212fRW5Drb6GZ0H6wuO4q67LikvKNiE-1683436232-0-AcUqETqt8pduGrj1q23JKfO5H8ENxy/yPlnoQCdyrig9767i0lA0edivEnbvht1ObKO6q9yC91y2v2UbHtCOON4=; pstk=77B251D19179C2D2A5385E7D45918533000003; cc=1; swt=AfNo/hK23upGkDk9inhTQ3XKVO2B540y0uxWXKgW8iJvRwdBeyF4cwBkTylHO/jfQZ4j7Hj/jRtemcEWRviALkKywQXBTDYUsa2r6ZSzsqV+qIr9qvCYICTMLKjPHU+WTRzB8UIgIJlgPKZznajo/VldkEOpyAlPG8jkDKTVQQ=='),
            R_HEADER('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35')
    ]


    # -----------------------------------------------------------


    def __init__(self, url=None, **kwargs):
        self.url = url or self._WSS_URLS_CONNECTION
        self.reply_timeout = kwargs.get('reply_timeout') or 60
        self.sleep_time = kwargs.get('sleep_time') or 5
        self.callback = kwargs.get('callback')


    async def listen_forever(self):
        while True:
            logger.debug('Creando una nueva conexión...\n')

            session_id, nst_token = self._get_session_and_nst_via_selenium()
            nst_auth_token = self._gen_nst_auth_code_str(nst_token)

            try:
                async with websockets.connect(
                                        self.url,
                                        extra_headers=self._REQ_HEADERS,
                                        extensions=self._REQ_EXTENSIONS,
                                        subprotocols=self._REQ_PROTOCOLS) as ws:

                    logger.debug(f'Se creó la conexión a {self.url}\n')

                    message = f'\x23\x03P\x01__time, S_{session_id}, D_{nst_auth_token}\x00'

                    time.sleep(0.5)

                    await ws.send(message)

                    logger.debug(f"\n>> {message}\n")

                    while True:
                        try:
                            reply = await asyncio.wait_for(ws.recv(), timeout=self.reply_timeout)

                        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                            logger.debug(
                                f'\nError - reintentando conectarse en {self.sleep_time} segundos (Ctrl-C para salir).\n')
                            await asyncio.sleep(self.sleep_time)
                            break

                        logger.debug(f'\nRespuesta del servidor >> {reply}\n')

                        if self.callback:
                            await self.callback(reply, ws)

            except socket.gaierror:
                logger.debug(
                    f'\nError - reintentando conectarse en {self.sleep_time} segundos (Ctrl-C para salir).\n')
                await asyncio.sleep(self.sleep_time)
                continue

            except ConnectionRefusedError:
                logger.debug('\nNadie parece escuchar este endpoint. Por favor verifica la URL.')
                logger.debug(f'Reintentando conectarse en {self.sleep_time} segundos (Ctrl-C para salir).\n')
                await asyncio.sleep(self.sleep_time)
                continue


    def _re_nst_token_feom_page_source(self, page_source) :
        pattern1 = re.compile("d\[b\(\\'0x1\\\'\)\][\s]*=[\s]*\\\'.*?\\\'[\s]*;")
        pattern2 = re.compile("d\[b\(\\'0x0\\\'\)\][\s]*=[\s]*\\\'.*?\\\'[\s]*;")

        r1= pattern1.findall(page_source)
        r2= pattern2.findall(page_source)

        if len(r1) > 0 and len(r2) > 0:
            sr1 = r1[0].split('\'')[3]
            sr2 = r2[0].split('\'')[3]
            nst_token = '.'.join([sr1,sr2])
            logger.debug(f'NST Token ID:{nst_token}\n')
            return nst_token


    def _gen_nst_auth_code_str(self, nst_token):
        d_str = self._nst_decrypt(nst_token)
        logger.debug(f"NST AUTH STR:{d_str}\n")
        return d_str


    def _nst_encrypt(self, nst_token):
        ret = ""
        for r in range(len(nst_token)):
            n = nst_token[r]
            for s in range(self._MAP_LEN):
                if n == self._char_map[s][0]:
                    n = self._char_map[s][1]
                    break
            ret += n
        return ret


    def _nst_decrypt(self, nst_token):
        ret = ""
        nst_token_len = len(nst_token)
        r = 0

        while nst_token_len > r:
            n = nst_token[r]

            for s in range(self._MAP_LEN):
                if ":" == n and ":|~" == nst_token[r, r+3]:
                    n = "\n"
                    r += 2
                    break

                if (n == self._char_map[s][1]):
                    n = self._char_map[s][0]
                    break

            ret += n
            r += 1

        return ret


    def _get_session_and_nst_via_selenium(self):
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-setuid-sandbox')

        options.add_argument('User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35')
        options.add_argument('Host=www.bet365.com.au')
        options.add_argument('Referer=https://www.bet365.com.au/?')
        options.add_argument('Accept=*/*')
        options.add_argument('Accept-Encoding=gzip, deflate, br')
        options.add_argument('Accept-Language=en-US,en;q=0.9')
        options.add_argument('Connection=keep-alive')
        options.add_argument('Sec-Fetch-Dest=empty')
        options.add_argument('Sec-Fetch-Mode=cors')
        options.add_argument('Sec-Fetch-Site=same-origin')

        driver = webdriver.Chrome(options=options)

        driver.get(self._URLS_NSTTOKEN_ID + '?#/AC/B19/C20459137/D50/E190002/F50/')

        wait = WebDriverWait(driver, 60)
        elem = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'src-ParticipantFixtureDetailsHigher_Team')))
        ps = driver.page_source

        logger.debug(f'Código fuente de la página:\n\n{ps}\n')

        time.sleep(6)

        nst_token = self._re_nst_token_feom_page_source(ps)

        session_id = [d['value'] for d in driver.get_cookies() if d['name'] == 'pstk'][0]

        logger.debug(f"\nnst_token: {nst_token}, session_id: {session_id}\n")

        return session_id, nst_token


# -----------------------------------------------------------


def start_ws_client(client):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.listen_forever())


async def callback_fn(data, ws):
    # Write here your logic.
    if data.startswith('100'):
        time.sleep(0.2)
        req = str('\x16\x00CONFIG_1_3,OVInPlay_1_3,Media_L1_Z3,XL_L1_Z3_C1_W3\x01')
        await ws.send(req)


# -----------------------------------------------------------


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('--url',
                        required=False,
                        # set here your URL
                        default=None,
                        dest='url',
                        help='Websocket URL')

    parser.add_argument('--reply-timeout',
                        required=False,
                        dest='reply_timeout',
                        type=int,
                        help='Timeout for reply from server')

    parser.add_argument('--sleep',
                        required=False,
                        type=int,
                        dest='sleep_time',
                        default=None,
                        help='Sleep time before retrieving connection')

    args = parser.parse_args()

    ws_client = WebSocketClient(**vars(args), callback=callback_fn)

    start_ws_client(ws_client)