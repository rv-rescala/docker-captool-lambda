import time
from catswalk.scraping.types.type_webdriver import *
import boto3
import os
import json
import csv
import os
from regoogle.drive import *

from lark import Lark, Transformer
from catswalk.scraping.types.type_webdriver import *
import os
import time

import logging
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from catswalk.scraping.request import CWRequest
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import os
from catswalk.scraping.types.type_webdriver import EXECUTION_ENV, DEVICE, DEVICE_MODE
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from PIL import Image
from io import BytesIO
from catswalk.scraping.driverfunc.wait import wait_until_images_loaded
from catswalk.scraping.driverfunc.jquery import import_jquer


logger = logging.getLogger()

class CWWebDriver:
    def __init__(self, binary_location: str = None, executable_path: str = None, execution_env: EXECUTION_ENV = EXECUTION_ENV.LOCAL, device = DEVICE.DESKTOP_GENERAL, proxy: str = None, implicitly_wait = 5.0, debug:bool = False):
        """[summary]

        Args:
            binary_location (str): [description]
            executable_path (str): [description]
            execution_env (str, optional): [local, local_headless, aws]. Defaults to "local".
            proxy (str, optional): [description]. Defaults to None.
        """
        self.binary_location = binary_location
        self.executable_path = executable_path
        self.execution_env = execution_env
        self.proxy = proxy
        self.device = device
        self.debug = debug
        self.scrolled = False
        self.prev_class = None

        print(f"device: {device}")

        options = Options()
        options.add_argument('--incognito')          # シークレットモードの設定を付与

        if self.execution_env == EXECUTION_ENV.LOCAL_HEADLESS:
            options.binary_location = self.binary_location
            options.add_argument('--headless') # https://www.ytyng.com/blog/ubuntu-chromedriver/
            options.add_argument("--disable-dev-shm-usage")  # overcome limited resource problems
            #options.add_argument("start-maximized")  # open Browser in maximized mode
            options.add_argument("--window-size=1280x651")
            options.add_argument("disable-infobars")  # disabling infobars
            options.add_argument("--disable-extensions")  # disabling extensions
            options.add_argument("--disable-gpu")  # applicable to windows os only
            options.add_argument("--no-sandbox")  # Bypass OS security model
        elif self.execution_env == EXECUTION_ENV.AWS_LAMBDA:
            self.executable_path = "/opt/browser/chromedriver"
            options.binary_location = "/opt/browser/chrome-linux/chrome"
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--single-process")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1280x651")
            options.add_argument("--disable-application-cache")
            options.add_argument("--disable-infobars")
            options.add_argument("--hide-scrollbars")
            options.add_argument("--enable-logging")
            options.add_argument("--log-level=0")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--homedir=/tmp")
            options.add_argument('--disable-dev-shm-usage')
            # --no-zygote, https://qiita.com/grainrigi/items/3f13b949310b669d08bb
            options.add_argument('--no-zygote')
        else:
            options.binary_location = self.binary_location
        if self.proxy:
            logging.info("WebDriverSession proxy on")
            options.add_argument(f"proxy-server={self.proxy}")


        if device.value.mode == DEVICE_MODE.MOBILE:
            device_name = device.value.agent
            # https://chromium.googlesource.com/chromium/src/+/167a7f5e03f8b9bd297d2663ec35affa0edd5076/third_party/WebKit/Source/devtools/front_end/emulated_devices/module.json
            #device_name = "Galaxy S5"
            print(device_name)
            mobile_emulation = { "deviceName": device_name }
            options.add_experimental_option("mobileEmulation", mobile_emulation)

        caps = DesiredCapabilities.CHROME
        caps['loggingPrefs'] = {'performance': 'INFO'}
        #logging.info(f"WebDriverSession.__init__ : {binary_location}, {executable_path}, {proxy}, {execution_env}")
        self.driver = webdriver.Chrome(options=options, executable_path=self.executable_path, desired_capabilities=caps)
        self.driver.implicitly_wait(implicitly_wait)

        if device.value.mode == DEVICE_MODE.DESKTOP:
            self.driver.maximize_window()

    def __enter__(self):
        """

        :return:
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """

        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        self.close()

    def close(self):
        """[Close WebDriverSession, if chromewebdriver dosen't kill, plsease execute "killall chromedriver"]
        
        """
        self.driver.close()
        self.driver.quit()

    def reload(self):
        self.driver.refresh()

    @property
    def cookies(self):
        """[Get cookie info]

        Returns:
            [type]: [description]
        """
        return self.driver.get_cookies()

    def to_request_session(self) -> CWRequest:
        """[summary]
        
        Returns:
            Request -- [description]
        """
        session = CWRequest()
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie["name"], cookie["value"])
        return session

    def wait_rendering_by_id(self, id, timeout=20):
        """[summary]
        
        Arguments:
            id {[type]} -- [description]
        
        Keyword Arguments:
            timeout {int} -- [description] (default: {20})
        """
        WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.ID, id)))

    def wait_rendering_by_class(self, _class, by_css_selector: bool, timeout=20):
        """[summary]
        
        Arguments:
            _class {[type]} -- [description]
        
        Keyword Arguments:
            timeout {int} -- [description] (default: {20})
        """
        print(f"wait_rendering_by_class: {_class}")
        if by_css_selector:
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, _class)))
        else:
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, _class)))

    def transition(self, url: str):
        """[summary]

        Args:
            url (str): [description]
        """
        self.driver.get(url)
        self.scrolled = False

    def get(self, url: str):
        self.transition(url=url)
        #WebDriverWait(self.driver, 10).until(EC.url_changes(url))
        soup = self.html
        self.driver.maximize_window()
        return soup

    def __wait_print(self):
        # ページが読み込まれるまで待機
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.presence_of_all_elements_located)
        wait_until_images_loaded(driver=self.driver)
        
    
        self.scroll_by_offset(offset=1)
        self.scroll_by_offset(offset=-1)
        self.scroll_by_offset(offset=-1)
        self.scroll_by_offset(offset=1)
        
        time.sleep(3)

    def print_screen_by_class_name(self, class_name:str, output_path: str, filename:str) -> str:
        """[summary]

        Args:
            class_name (str): [description]
            output_path (str): [description]
            filename (str): [description]
        """
        # Get Screen Shot
        fullpath = f"{output_path}/{filename}.png"
        self.__wait_print()
        png = self.driver.find_element_by_class_name(class_name).screenshot_as_png
        # ファイルに保存
        with open(fullpath, 'wb') as f:
            f.write(png)
        return fullpath


    def print_screen_by_size(self, w, h, path, filename, start_w: int = 0, start_h: int = 0):
        """
        hw = self.driver.get_window_size()
        w = hw["width"]
        h = hw["height"]
        """
        self.__wait_print()
        print(f"print_screen_by_size: {start_w}, {start_h}, {w}, {h}")
        
        img_binary = self.driver.get_screenshot_as_png()
        img = Image.open(BytesIO(img_binary))
        print(f"print_screen_by_size, {start_w}, {start_h}, {w}, {h}")
        crop_dim = (start_w, start_h, w, h) # left top right bottom
        img = img.crop(crop_dim)
        fullpath = f"{path}/{filename}.png"
        img.save(fullpath)
        
        return fullpath

    def print_screen_by_hight(self, h, path, filename, scale: int = 1, index:int = 1):
        # htmlタグからクライアントのwindowサイズを抜き出す
        html = self.driver.find_element_by_tag_name('html')
        inner_width = int(html.get_attribute("clientWidth"))
        inner_height = int(html.get_attribute("clientHeight"))
        print(f"inner_width: {inner_width}, inner_height:{inner_height}")

        if self.execution_env == EXECUTION_ENV.LOCAL:
            if self.device == DEVICE.MOBILE_iPad_Pro or self.device == DEVICE.DESKTOP_GENERAL:
                scale = 2
            else:
                scale = 3
            w = inner_width * scale
            #scaled_h = h * scale
        elif self.execution_env == EXECUTION_ENV.AWS_LAMBDA:
            if self.device == DEVICE.MOBILE_iPad_Pro or self.device == DEVICE.DESKTOP_GENERAL:
                scale = 1
                h = int(h) / 2
            else:
                scale = 3
            w = inner_width * scale
        else:
            if self.device == DEVICE.MOBILE_iPad_Pro or self.device == DEVICE.DESKTOP_GENERAL:
                scale = 2
            else:
                scale = 3
            w = inner_width * scale
            #scaled_h = h * scale
        fullpath = self.print_screen_by_size(w=int(w), h=int(h), path=path, filename=filename)
        return fullpath

    def print_screen_by_class_hight(self, class_name, path, filename, index:int = 1):
        current_e = self.get_elem_by_class(class_name=class_name, index = index)
        current_location = current_e.location
        current_size = current_e.size
        window_hw = self.driver.get_window_size()
        print(f"print_screen_by_class_hight: location: {current_location}, size: {current_size}, window_hw: {window_hw}")

        # htmlタグからクライアントのwindowサイズを抜き出す
        html = self.driver.find_element_by_tag_name('html')
        inner_width = int(html.get_attribute("clientWidth"))
        inner_height = int(html.get_attribute("clientHeight"))
        print(f"inner_width: {inner_width}, inner_height:{inner_height}")

        # prev_class info
        # TBD: Desktop & Lamdaの時の横のscaleを正す
        prev_e = None
        if self.prev_class:
            print(f"prev_class: {self.prev_class}")
            prev_e = self.get_elem_by_class(class_name=self.prev_class["class_name"], index = self.prev_class["index"])
            prev_location = prev_e.location
        if self.execution_env == EXECUTION_ENV.LOCAL:
            if self.device == DEVICE.MOBILE_iPad_Pro or self.device == DEVICE.DESKTOP_GENERAL:
                scale = 2
            else:
                scale = 3
            w = inner_width * scale
            if prev_e:
                print(f'current_location_y {current_location["y"]}, prev_location_y: {prev_location["y"]}, current_size_height_: {current_size["height"]}')
                h = (current_location["y"] - prev_location["y"]) * scale - (current_size["height"] / 2)
            else:
                h = current_location["y"] * scale
        else:
            if self.device == DEVICE.MOBILE_iPad_Pro or self.device == DEVICE.DESKTOP_GENERAL:
                scale = 2
            else:
                scale = 3
            w = inner_width * scale
            if prev_e:
                print(f'current_location_y {current_location["y"]}, prev_location_y: {prev_location["y"]}, current_size_height_: {current_size["height"]}')
                h = (current_location["y"] - prev_location["y"]) * scale - (current_size["height"] / 2)
            else:
                h = current_location["y"] * scale
        print(f"w: {w}")
        print(f"h: {h}")

        fullpath = self.print_screen_by_size(w=w, h=h, path=path, filename=filename)

        return fullpath

    def print_screen_by_window(self, path, filename):
        """[summary]

        Args:
            path ([type]): [description]
            filename ([type]): [description]

        Returns:
            [type]: [description]
        """
        # Get Screen Shot
        fullpath = f"{path}/{filename}.png"
        self.__wait_print()
        self.driver.save_screenshot(fullpath)
        return fullpath

    def get_elem_by_class(self, class_name:str, index:int = 1):
        if len(class_name.split(" ")) > 1:
            _class_name = "." + ".".join(class_name.split(" "))
            self.wait_rendering_by_class(_class_name, True)
            elems = self.driver.find_elements_by_css_selector(_class_name)
        else:
            self.wait_rendering_by_class(class_name, False)
            elems = self.driver.find_elements_by_class_name(class_name)
        print(f"get_elem_by_class len:{len(elems)}")

        e = elems[index - 1]
        """
        location = e.location
        size = e.size
        #w, h = size['width'], size['height']
        window_hw = self.driver.get_window_size()
        print(f"get_elem_by_class: class_name: {class_name}, location: {location}, size: {size}, window_hw: {window_hw}")
        """
        return e

    def click_by_class_name(self, class_name:str, check_exist:bool = False, index:int = 1) -> str:
        """[summary]

        Args:
            class_name (str): [description]

        Returns:
            str: [description]
        """
        # Get Screen Shot
        if check_exist:
            if not self.is_exist_class(class_name=class_name):
                return f"{class_name} not found"
        elem = self.get_elem_by_class(class_name, index = index)
        elem.click()
        if self.debug:
            time.sleep(5)


    def scroll_by_offset(self, offset = 0):
        script = "window.scrollTo(0, window.pageYOffset + " + str(offset) + ");"
        self.driver.execute_script(script)

    def scroll_to_bottom(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_by_key(self, element, scroll_time):
        for num in range(0, scroll_time):
            element.send_keys(Keys.PAGE_DOWN)

    def smooth_scroll_to_bottom(self, scroll_pause_time = 0.5):
        # lazy対応
        # https://stackoverflow.com/questions/62600288/how-to-handle-lazy-loaded-images-in-selenium
        print("smooth_scroll_to_bottom")
        i = 0
        time.sleep(scroll_pause_time)
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            print(f"smooth_scroll_to_bottom: {new_height}")
            if new_height == last_height:
                break
            last_height = new_height
            i += 1
            if i == 5:
                break

    def move_to_element_by_class_name(self, class_name:str, index:int = 1) -> str:
        """[summary]

        Args:
            class_name (str): [description]

        Returns:
            str: [description]
        """
        if not self.scrolled:
            self.smooth_scroll_to_bottom()
        element = self.get_elem_by_class(class_name=class_name, index=index)
        element.location_once_scrolled_into_view
        self.scrolled = True
        self.prev_class = {"class_name": class_name, "index": index}
        if self.debug:
            time.sleep(5)

    def is_exist_class(self, class_name: str) -> bool:
        """[summary]

        Args:
            class_name (str): [description]

        Returns:
            bool: [description]
        """
        html = self.html
        _class_name = "." + ".".join(class_name.split(" "))
        if html.select(_class_name):
            logger.debug(f"is_exist_class, {class_name} is found")
            return True
        else:
            logger.debug(f"is_exist_class, {class_name} not found")
            return False
        
    @property
    def position_height(self):
        hight = self.driver.execute_script("return document.body.scrollHeight")
        print(f"position_height: {hight}")
        return hight

    @property
    def html(self):
        html = self.driver.page_source.encode('utf-8')
        return BeautifulSoup(html, "lxml")

    @property
    def log(self):
        result = []
        for entry in self.driver.get_log('performance'):
            result.append(entry['message'])
        return result


def execute(request: CWWebDriver, order_name: str, grammar_path: str, order_path: str, url:str, output_path:str, filename:str) -> str:
    class Main(Transformer):
        def __init__(self):
            self._functions = {}
        
        def open_call(self, token):
            print(f"open: {url}")
            if request:
                request.get(url=url)

        def transition(self, token):
            _url = token[0]
            if _url == "URL":
                _url = url
            print(f"open: {_url}")
            if request:
                request.get(url=_url)

        def move_by_class(self, token):
            class_name = token[0]
            print(f"move_by_class: {class_name}")
            if request:
                request.move_to_element_by_class_name(class_name=class_name)

        # move_by_class_index
        def move_by_class_index(self, token):
            class_name = token[0]
            index = int(token[1])
            print(f"move_by_class_index: {class_name}, {index}")
            if request:
                request.move_to_element_by_class_name(class_name=class_name, index=index)

        def click_by_class(self, token):
            class_name = token[0]
            print(f"click_by_class: {class_name}")
            if request:
                request.click_by_class_name(class_name=class_name)


        def click_by_class_when_exist(self, token):
            class_name = token[0]
            print(f"click_by_class_when_exist: {class_name}")
            if request:
                request.click_by_class_name(class_name=class_name, check_exist=True)


        def capture_by_screen(self, token):
            __output_path = f"{output_path}/{order_name}"
            print(f"capture_by_screen: {__output_path}, {filename}")
            if request:
                # mkdirs
                os.makedirs(__output_path, exist_ok=True)
                fullpath = request.print_screen_by_window(__output_path, filename)
                return fullpath
        
        def capture_by_hight(self, token):
            hight = token[0]
            __output_path = f"{output_path}/{order_name}"
            print(f"capture_by_screen: {__output_path}, {filename}, {hight}")
            if request:
                # mkdirs
                os.makedirs(__output_path, exist_ok=True)
                fullpath = request.print_screen_by_hight(hight, __output_path, filename)
                return fullpath

        def capture_by_class_hight(self, token):
            class_name = token[0]
            __output_path = f"{output_path}/{order_name}"
            print(f"capture_by_class_hight: {__output_path}, {filename}, {class_name}")
            if request:
                # mkdirs
                os.makedirs(__output_path, exist_ok=True)
                fullpath = request.print_screen_by_class_hight(class_name, __output_path, filename)
                return fullpath

        # capture_by_class_hight_index
        def capture_by_class_hight_index(self, token):
            class_name = token[0]
            index = int(token[1])
            __output_path = f"{output_path}/{order_name}"
            print(f"capture_by_class_hight_index: {__output_path}, {filename}, {class_name}, {index}")
            if request:
                # mkdirs
                os.makedirs(__output_path, exist_ok=True)
                fullpath = request.print_screen_by_class_hight(class_name=class_name, path=__output_path, filename=filename, index=index)
                return fullpath

        def wait_by_class(self, token):
            class_name = token[0]
            print(f"wait_by_class: {class_name}")
            if request:
                request.get_elem_by_class(class_name)

        def wait_by_time(self, token):
            _time = int(token[0])
            print(f"wait_by_time: {_time}")
            time.sleep(_time)

        def symbol(self, token):
            return token[0].value

        def string(self, token):
            return token[0][1:-1]

    rule = open(grammar_path).read()
    parser = Lark(rule, parser='lalr', transformer=Main())
    program = open(order_path).read()
    r = parser.parse(program)
    fullpath = list(r.children)[-1]
    print(r)
    return fullpath


BUKET = "captool-gatsby"
ORDER = "ebook_top_pc"
KEY_S3_PATH = "conf/google/test_rv_key.json"
G_PARENTS = "1OCApnIcgg7AmT5qstq-xjiGmcVs9GpLY"

def s3_upload(local_fullpath):
    filename = local_fullpath.split("/")[-1]
    s3_client = boto3.client('s3')
    s3_client.upload_file(local_fullpath, BUKET, f"dataset/output/{ORDER}/test_{filename}")
    os.remove(local_fullpath)
    return f"s3://{BUKET}/dataset/output/{ORDER}/test_{filename}"

def gdrive_upload(gdrive, local_fullpath, parents=None):
    filename = local_fullpath.split("/")[-1]
    gdrive.upload_file(filename=filename, local_path=local_fullpath, parents=parents)
    os.remove(local_fullpath)
    return f"s3://{BUKET}/dataset/output/{ORDER}/{filename}"
    
def get_input_list() -> str:
    s3_client = boto3.client('s3')
    tmp_path = f"/tmp/test_{ORDER}.csv"
    # get csv
    s3_client.download_file(BUKET, f"dataset/input/{ORDER}.csv", tmp_path)
    with open(tmp_path, "r") as f:
        reader = csv.reader(f)
        input_list =  [row for row in reader]
    print(input_list)
    return input_list
    
def grammar_path() -> str:
    s3_client = boto3.client('s3')
    tmp_path = f"/tmp/grammar.lark"
    s3_client.download_file(BUKET, f"conf/common/grammar.lark", tmp_path)
    return tmp_path
    
def order_path() -> str:
    s3_client = boto3.client('s3')
    tmp_path = f"/tmp/{ORDER}_command.od"
    s3_client.download_file(BUKET, f"conf/order/{ORDER}/command.od", tmp_path)
    return tmp_path
    
def device() -> str:
    s3_client = boto3.client('s3')
    tmp_path = f"/tmp/{ORDER}_browser.json"
    s3_client.download_file(BUKET, f"conf/order/{ORDER}/browser.json", tmp_path)
    # order specific setting
    with open(tmp_path, "r") as f:
        j = json.load(f)
        device = DEVICE.str_to_enum(j["device"])
    return device
    
def gdrive_init(parents):
    local_key = "/tmp/gdrive_key.json"
    s3_client = boto3.client('s3')
    s3_client.download_file(BUKET, KEY_S3_PATH, "/tmp/gdrive_key.json")
    return GoogleDrive(local_key, parents)

def get_id_by_key(gdrive, key: str):
    kis = gdrive.list_key_id()
    print(kis)
    for ki in kis:
        _key = ki["name"]
        id = ki["id"]
        if key == _key:
            return id
    return None
    
def gdrive_folder_init(gdrive, key):
    folder_id = get_id_by_key(gdrive, key)
    print(f"folder_id: {folder_id}")
    if folder_id:
        gdrive.delete(folder_id)
    parents = gdrive.create_folder(key)
    return parents
    
def handler(event, context):
    request = CWWebDriver(execution_env=EXECUTION_ENV.AWS_LAMBDA, device = device())
    output_path = f"/tmp"
    os.makedirs(output_path, exist_ok=True)
    #gdrive = gdrive_init(G_PARENTS)
    path_list = [execute(request=request, order_name=ORDER, grammar_path=grammar_path(), order_path=order_path(), url=i[1],output_path=output_path, filename=i[2]) for i in get_input_list()]
    print(path_list)
    #parents = gdrive_folder_init(gdrive, ORDER)
    #gdrive_c = gdrive_init(parents)
    #gdrive.create_folder(ORDER)
    print([s3_upload(i) for i in path_list])
    request.close()
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
