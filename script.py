import html
import gradio as gr

import requests
import re
from bs4 import BeautifulSoup
import urllib
import json
import time

class BingTranslator:
    HOST: str = None
    ig: str = None
    key: str = None
    token: str = None
    iid: str = None
    time_stamp: int = 0

    def __int__(self):
        pass

    def request_all_id(self):
        if self.HOST is None:
            self.HOST = self.get_bing_host()
        re_ig = re.compile('IG:"([A-Za-z0-9]+)"')
        re_tk = re.compile('var params_AbusePreventionHelper\s*=\s*\[([0-9]+),\s*"([^"]+)",[^\]]*\];')
        home_page = self.HOST + 'translator'
        rsp = requests.get(url=home_page, allow_redirects=False)
        if rsp.status_code == 200:
            all_text = str(rsp.content)
            find_ig = re_ig.findall(all_text)
            if find_ig is not None:
                self.ig = find_ig[0]

            find_tk = re_tk.findall(all_text)
            if find_tk is not None:
                self.key, self.token = find_tk[0]

            soup = BeautifulSoup(rsp.content, features="html.parser")
            rich_tta_elm = soup.find('div', {'id': 'rich_tta'})
            if rich_tta_elm is not None:
                self.iid = rich_tta_elm.get('data-iid')

        self.time_stamp = int(time.time())

    def check_all_id(self):
        now = int(time.time())
        if (now - self.time_stamp) > 600:
            print("bing id overtime, request_all_id again")
            self.request_all_id()

        if not self.do_check_all_id():
            print("bing id invalid, request_all_id again")
            self.request_all_id()

        if not self.do_check_all_id():
            raise RuntimeError('check bing id failed!')

    def do_check_all_id(self):
        if self.ig is None or self.key is None or self.iid is None:
            return False
        if len(self.ig) == 0 or len(self.key) == 0 or len(self.iid) == 0:
            return False
        return True

    def clear_all_id(self):
        self.ig = ''
        self.key = ''
        self.token = ''
        self.iid = ''

    def translator(self, text: str, src_lang: str, dst_lang: str):
        self.check_all_id()
        post_url = self.HOST + 'ttranslatev3?isVertical=1&&IG=' + self.ig + '&IID=' + self.iid
        data = '&fromLang=' + src_lang + '&to=' + dst_lang + '&text=' + urllib.parse.quote(
            text) + '&token=' + urllib.parse.quote(self.token) + '&key=' + urllib.parse.quote(
            self.key) + '&tryFetchingGenderDebiasedTranslations=true'
        head = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en;q=0.7',
            'content-type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
        }

        trans_rsp = requests.post(url=post_url, data=data, headers=head)
        if trans_rsp is not None and trans_rsp.status_code == 200:
            try:
                trans_json = json.loads(trans_rsp.text)
                if trans_json is not None and len(trans_json) > 0:
                    translations = trans_json[0]['translations']
                    if translations is not None and len(translations) > 0:
                        return translations[0]['text']
            except KeyError:
                print("error: get translation text failed!")

        # 失败了，置所有KeyID都为空，为下次准备
        self.clear_all_id()
        raise RuntimeError('bing translate failed!')

    def get_bing_host(self):
        """
       各地区访问www.bing.com后可能被重定向，如中国区会变为cn.bing.com，这里保证访问的域名是与当地域是匹配的
       :return: 当地准确的bing.com域名
       """
        default_host = 'https://www.bing.com/'
        host_rsp = requests.get(url=default_host, allow_redirects=False)
        if host_rsp.status_code == 302:
            host = host_rsp.headers.get('Location')
            if host is not None:
                return host

        return default_host


params = {
    "activate": True,
    "keep_eng": False,
    "language string": "zh-Hans",
}

language_codes = {'Chinese (Simplified)': 'zh-Hans', 'English': 'en', 'Japanese': 'ja'}

bing_translator = BingTranslator()

def input_modifier(string):
    """
    This function is applied to your text inputs before
    they are fed into the model.
    """
    if not params['activate']:
        return string

    return bing_translator.translator(text=string, src_lang=params['language string'], dst_lang='en')

def output_modifier(string):
    """
    This function is applied to the model outputs.
    """
    if not params['activate']:
        return string

    trans_str = bing_translator.translator(text=string, src_lang='en', dst_lang=params['language string'])
    if not params['keep_eng']:
        return trans_str
    else:
        return string +"\n----------\n" + trans_str


def bot_prefix_modifier(string):
    """
    This function is only applied in chat mode. It modifies
    the prefix text for the Bot and can be used to bias its
    behavior.
    """

    return string


def ui():
    # Finding the language name from the language code to use as the default value
    language_name = list(language_codes.keys())[list(language_codes.values()).index(params['language string'])]

    # Gradio elements
    with gr.Row():
        activate = gr.Checkbox(value=params['activate'], label='Activate translation')
        keep_eng  = gr.Checkbox(value=params['keep_eng'], label='Keep English')

    with gr.Row():
        language = gr.Dropdown(value=language_name, choices=[k for k in language_codes], label='Language')

    # Event functions to update the parameters in the backend
    activate.change(lambda x: params.update({"activate": x}), activate, None)
    language.change(lambda x: params.update({"language string": language_codes[x]}), language, None)
    keep_eng.change(lambda x: params.update({"keep_eng": x}), keep_eng, None)
