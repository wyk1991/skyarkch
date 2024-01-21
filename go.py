# coding=utf-8
#from dotenv import load_dotenv
import sys,os
sys.path.append(os.path.join(sys.path[0], '../'))

from wx import grid
import wx
from pubsub import pub
import threading
import time
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3, HTTPProvider
from pyuseragents import random as random_ua
from functools import wraps
import json

def retry(max_retries=3, wait_time=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:  
                    return func(*args, **kwargs)
                except Exception as e:
                    e_msg = f"错误 {e}, {wait_time} 秒后重试"
                    pub.sendMessage("update_log", msg=e_msg)
                    print(f"{e_msg}")
                    retries += 1
                    time.sleep(wait_time)        
            raise Exception(f"到达最大重试次数 ({max_retries})，跳过")

        return wrapper
    return decorator

class Skygate():

    log_file_name = 'checkin_account.txt'
    
    def __init__(self, pk, jwt='', is_daily=False, proxy={}):
        self.web3 = Web3(HTTPProvider('https://opbnb.publicnode.com'))
        self.host = 'https://apisky.ntoken.bwtechnology.net/api/{}'
        self.pk = pk # 签到账号私钥
        self.account:Account = self.web3.eth.account.from_key(pk)
        self.sign_str = 'skygate' # personal_sign 签名字符串
        self.jwt = jwt # jwt
        self.is_daily = is_daily
        self.proxy = proxy
        self.block_scan_tx_url = 'https://opbnbscan.com/tx/{}' # 区块浏览器
        
    
    def check_balance(self):
        opbnb_balance = self.web3.eth.get_balance(self.account.address)
        return opbnb_balance
    
    def check_has_slime_nft(self):
        nft_contract_address = Web3.to_checksum_address('0x961a98999f14e8c5e69bdd4ee0826d6e0c556a0d')
        nft_contract = self.web3.eth.contract(address=nft_contract_address, abi=self.load_abi('erc721.json'))
        return nft_contract.functions.balanceOf(owner=self.account.address).call()
    
    def dispatch_squead(self, data):
        address = Web3.to_checksum_address('0x9465fe0e8cdf4e425e0c59b7caeccc1777dc6695')
        tx = self.web3.eth.contract(address=address, abi=self.load_abi('abi.json')).functions.signin(data)
        tx_hash = self.make_tx(tx)
        return tx_hash
    
    def adventure(self):
        data = 2
        tx_hash = self.dispatch_squead(data)
        self.pop_log(f'{self.account.address} 冒险成功 ! | Tx: {self.block_scan_tx_url.format(tx_hash)}')

    def treasure(self):
        data = 1
        tx_hash = self.dispatch_squead(data)
        self.pop_log(f'{self.account.address} 寻宝成功 ! | Tx: {self.block_scan_tx_url.format(tx_hash)}')
    
    def explore(self):
        address = Web3.to_checksum_address('0xd42126d46813472f83104811533c03c807e65435')
        tx = self.web3.eth.contract(address=address, abi=self.load_abi('abi.json')).functions.signin(1)
        tx_hash = self.make_tx(tx)
        self.pop_log(f'{self.account.address} 探索成功 ! | Tx: {self.block_scan_tx_url.format(tx_hash)}')
        
    def make_tx(self, tx):
        tx = tx.build_transaction({
            'value': 0,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'from': self.account.address,
            'gas': 0,
            'maxFeePerGas': 0,
            'maxPriorityFeePerGas': 0
        })
        tx.update({'maxFeePerGas': self.web3.eth.gas_price})
        tx.update({'maxPriorityFeePerGas': self.web3.eth.gas_price})
        tx.update({'gas': self.web3.eth.estimate_gas(tx)})
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        while tx_receipt is None or tx_receipt['status'] is None:
            time.sleep(1)
            tx_receipt = self.web3.eth.get_transaction_receipt(tx_hash)

        tx_hash = Web3.to_hex(tx_hash)
        return tx_hash

        
    def load_abi(self, abi_name):
        with open(abi_name, 'r') as f:
            json_data = json.load(f)
            return json_data

    @retry(max_retries=30, wait_time=5)
    def get_info(self):
        # 根据jwt获取账号信息
        url = self.host.format('get_skyGate_coin.php')
        payload = {
            'api_id': 'skyark_react_api',
            'api_token': '3C2D36F79AFB3D5374A49BE767A17C6A3AEF91635BF7A3FB25CEA8D4DD',
            'jwt': self.login()
        }
        res = requests.post(url=url, data=payload, timeout=30, proxies=self.proxy, headers=self.get_headers())
        if res.status_code != 200:
            raise Exception(f'get_info error, status code {res.status_code}')
        
        res = res.json()
     
        if res['err'] != 0:
            raise Exception(f'get_info error, error code {res["err"]}, error message {res["0"]}')

        # {"err":0,"uName":"0x1ad453068d1808e213b46ce415a51d38b8419e57","gateWalletAddr":"9aPW9RhQ9c9eWBK","uWalletAddr":"0x1ad453068d1808e213b46ce415a51d38b8419e57","coin":"100","participationTime":"","week":"","scheduleStart":1700179200,"scheduleEnd":1734393599,"joinAmount":"100","additionalCost":"0","winAnnDate":1702857600,"advName":"31thadvanture","inviteCode":"9aPW9","uId":"21244085","userLevel":"1"}
        return res
    
    def get_headers(self):
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
            'Origin': 'https://skygate.skyarkchronicles.com',
            'Referer': 'https://skygate.skyarkchronicles.com/',
            'User-Agent': random_ua(),
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
        }

        return headers

    @retry(max_retries=30, wait_time=3)
    def login(self):
        # 获取登录态jwt
        if self.jwt:
            return self.jwt
        
        msghash = encode_defunct(text=self.sign_str)
        sign = Account.sign_message(msghash, self.pk)
       
        url = self.host.format('wallet_signin.php')
        payload = {
            'api_id': 'skyark_react_api',
            'api_token': '3C2D36F79AFB3D5374A49BE767A17C6A3AEF91635BF7A3FB25CEA8D4DD',
            'uWalletAddr': str(self.account.address),
            'sign': str(sign.signature.hex())
        }

        res = requests.post(url=url, data=payload, timeout=30, proxies=self.proxy, headers=self.get_headers())
        if res.status_code != 200:
            raise Exception(f'登录错误, 错误状态码 {res.status_code}')
        
        res = res.json()
        if res['err'] != 0:
            raise Exception(f'登录错误, 错误状态码 {res["err"]}, 错误信息 {res["0"]}')
        
        self.jwt = res['jwt']
        if not self.is_daily:
            self.save()
        #{"err":0,"msg":"verify_success","jwt":"eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1SWQiOiIyMTI0NDA4NSIsInVXYWxsZXRBZGRyIjoiMHgxYWQ0NTMwNjhkMTgwOGUyMTNiNDZjZTQxNWE1MWQzOGI4NDE5ZTU3In0.shwMdrnWwqQJy3taJxhT2_mIsPsCF3e8CsWsmm_oTG4xhZsh_WOEqQlWC7AULffc1hj3xrx6btwEcXBO_MXu8yPqkDF6LN1rPtVNLEK3ISOCpbzfHMcMOpodZgmsPsd3YkDkqAnklQIO6rW3wAKhWgbZO1HHW5fhQM8sN-7cWXo","uWalletAddr":"0x1ad453068d1808e213b46ce415a51d38b8419e57"}
        return self.jwt
    
    @retry(max_retries=30, wait_time=3)


    def save(self):
        # 保存账号到当前文件夹的checkin_account.txt文件, 格式： 地址----私钥----jwt----邀请人地址（邀请码）
        log_str = f'{self.account.address}----{self.pk}----{self.jwt}\n'
        self.pop_log(f'{self.account.address} 注册账号成功，保存在 {self.log_file_name} 中')
        with open(self.log_file_name, 'a') as f:
            f.write(log_str)

    @staticmethod
    def iter_file(file_name):
        # 迭代文件
        with open(file_name, encoding='utf-8') as f:
            for line in f:
                the_line = line.strip()
                yield the_line

    def pop_log(self, log_str):
        pub.sendMessage(topicName=f'update_log', msg=log_str)
            
    @staticmethod
    @retry(max_retries=30, wait_time=5)
    def daily_explore_treasure_adventure():
        # 每日冒险和收集宝藏可以获得积分的次数，各6次
        daily_treasure_adventure_times = 6
        for log_str in Skygate.iter_file(Skygate.log_file_name):
            tmp = log_str.split('----')
            _, pk, jwt=tmp[1], tmp[1], tmp[2]
            sg = Skygate(pk=pk, jwt=jwt, is_daily=True, proxy={})
            if not sg.check_balance():
                sg.pop_log(f'{sg.account.address} 在opbnb链没有bnb余额作为gas, 跳过gas任务')
                continue
            
            sg.pop_log(f'========================={sg.account.address} 日常gas任务开始============================')
            # 每日探索1次，10积分
            sg.explore()
            # 检查账户是否有史莱姆nft
            slime_nft_num = sg.check_has_slime_nft()
            if not slime_nft_num:
                sg.pop_log(f'{sg.account.address} 没有史莱姆nft，跳过探险和寻宝')
                sg.pop_log(f'========================={sg.account.address} 日常探险寻宝结束============================')
                continue
            else:
                sg.pop_log(f'{sg.account.address} 有 {slime_nft_num} 史莱姆 nft, 开始日常探险寻宝')

            
            # 每日探险6次，每次获得积分随机              
            for i in range(daily_treasure_adventure_times):
                sg.pop_log(f'{sg.account.address}第 {str(i+1)} 次探险开始')
                try:
                    sg.adventure()
                except Exception as e:
                    sg.pop_log(f'{sg.account.address} 探险错误 , 原因 {e}, 跳过探险')
                    break
                
            # 每日收集宝藏6次，每次获得积分随机
            for i in range(daily_treasure_adventure_times):
                sg.pop_log(f'{sg.account.address}第 {str(i+1)} 次寻宝开始')
                try:
                    sg.treasure()
                except Exception as e:
                    sg.pop_log(f'{sg.account.address} 寻宝错误, 原因 {e}, 跳过寻宝')
                    break
            sg.pop_log(f'========================={sg.account.address} 日常探险寻宝结束============================')

 
 
    @staticmethod
    def get_random_account_pk(): 
        # 随机生成以太坊地址私钥
        return Account.create().key.hex()
    


class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, handle):
        super().__init__()
        self.handle: BaseBatchWx = handle

    def OnDropFiles(self, x, y, filenames):
        self.handle.file_drop_handle(filenames)




class BaseBatchWx():

    def __init__(self):
        self.loads_tks = []
        self.scale = 1  # 比例尺，改变这个，就能等比放大/缩小gui的尺寸
        self.border = 7 * self.scale
        self.height = 0
       
        icon = 'favicon.ico'
        self.icon_type = wx.BITMAP_TYPE_ICO
        self.icon = f'{icon}'
        self.wx_config = {
            'title': '交互脚本-skyark',
            'size': (600*self.scale, 200*self.scale) # 第一个是控件宽度，第二个是日志控件的高度
        }
        self.app: wx.App = wx.App()
        self.wx: wx = wx

        self.frame = self.wx.Frame(None, title=self.wx_config['title'], style=self.wx.DEFAULT_FRAME_STYLE)
        self.frame.Centre()

        icon = self.wx.Icon(self.icon, self.icon_type)
        self.frame.SetIcon(icon)
        self.panel = self.wx.Panel(self.frame)
        # 动态高度控件
        self.sizer = self.wx.GridBagSizer(10, 10)
        # 日志控件
        self.log_box = self.wx.TextCtrl(self.panel, size=(-1, self.wx_config['size'][1]),  value='', style=self.wx.TE_MULTILINE|self.wx.HSCROLL)
        self.sizer.Add(self.log_box, pos=(self.height, 0), span=(0, 11), flag=self.wx.EXPAND | self.wx.ALL, border=7*self.scale)
        self.height += 1
        self.frame.SetDropTarget(MyFileDropTarget(self))
        self.log_box.SetDropTarget(MyFileDropTarget(self))

        # 初始化日志
        self.topic_name = 'update_log'
        pub.subscribe(self.log_add, self.topic_name)
        for msg in self.init_log():
            pub.sendMessage(self.topic_name, msg=msg)
        #pub.sendMessage(self.topic_name, msg=f'----------------------------------------------------------')
            
    
    def get_now_time(self, format='%Y-%m-%d %H:%M:%S'):
        return time.strftime(format, time.localtime(time.time()))


    def init_log(self)->list:
        return [
            '开始使用工具',
        ]

    def file_drop_handle(self, filenames):
        for file in filenames:
            self.log_add(f'读取文件：{file}')
        return True

    # 具体的组件
    def init(self):
        self.labelName = self.wx.StaticText(self.panel, label="大号邀请码（evm钱包地址）")  # Name
        self.sizer.Add(self.labelName, pos=(self.height, 0), flag=self.wx.LEFT, border=self.border)
        
        self.tcName = self.wx.TextCtrl(self.panel)
        self.sizer.Add(self.tcName, pos=(self.height, 1), span=(1, 9), flag=self.wx.EXPAND | self.wx.LEFT, border=self.border)
        self.height += 1


    def task1(self, *args):
        value = self.tcName.GetValue()
        self.wx.CallAfter(pub.sendMessage, self.topic_name, msg=f'大号邀请码:{value}')
        proxy = {}
        #创建钱包的数量
        main_account_num = 2

        for i in range(main_account_num):
            main_account_pk = Skygate.get_random_account_pk()
            main_sg = Skygate(pk=main_account_pk, proxy=proxy)
            try:
                main_sg.login()
            except Exception as e:
                self.wx.CallAfter(pub.sendMessage, self.topic_name, msg=f'{e}')
                continue

    def task3(self, *args):
        Skygate.daily_explore_treasure_adventure()

    def get_args(self):
        return ()

    def start_button_click(self, event):
        self.wx.CallAfter(pub.sendMessage, self.topic_name, msg='第一次跑')
        threading.Thread(target=self.task1, args=self.get_args(), daemon=False).start()

    def gas_button_click(self, event):
        self.wx.CallAfter(pub.sendMessage, self.topic_name, msg='gas任务')
        threading.Thread(target=self.task3, args=self.get_args(), daemon=False).start()

    def log_add(self, msg):
        self.log_box.AppendText(f'[{self.get_now_time(format="%H:%M:%S")}]{msg}\n')


    def run(self):

        # labelName = self.wx.StaticText(self.panel, label="名称")  # Name
        # self.sizer.Add(labelName, pos=(self.height, 0), flag=self.wx.LEFT, border=7*self.scale)
        #
        # tcName = self.wx.TextCtrl(self.panel)
        # self.sizer.Add(tcName, pos=(self.height, 1), span=(1, 9), flag=self.wx.EXPAND | self.wx.LEFT, border=2*self.scale)
        # self.height += 1

        # line = self.wx.StaticLine(self.panel)
        # self.sizer.Add(line, pos=(self.height, 0), span=(1, 9), flag=self.wx.EXPAND | self.wx.BOTTOM,
        #                border=7 * self.scale)
        # self.height += 1

        #================ 下面是通用按钮的处理 ================#
        # 开始按钮
        self.start_button = self.wx.Button(self.panel, label='第一次跑', name='button')
        self.start_button.Bind(self.wx.EVT_BUTTON, self.start_button_click)
        self.sizer.Add(self.start_button, pos=(self.height, 7), flag=self.wx.LEFT, border=self.border)

        # 停止按钮
        self.stop_button = self.wx.Button(self.panel, label='gas任务', name='button')
        self.stop_button.Bind(self.wx.EVT_BUTTON, self.gas_button_click)
        self.sizer.Add(self.stop_button, pos=(self.height, 9), flag=self.wx.LEFT, border=self.border)
        self.height += 1

        # 最后 加一条线，仅做美观用
        # line = self.wx.StaticLine(self.panel)
        # self.sizer.Add(line, pos=(self.height, 0), span=(0, 10), flag=self.wx.EXPAND | self.wx.BOTTOM,
        #                border=0)
        # self.height += 1

        self.sizer.AddGrowableCol(2)

        self.panel.SetSizer(self.sizer)

        self.sizer.Fit(self.frame)

        # 自适应高度后，限制死控件宽高，防止用户拖拽resize控件大小
        height = self.frame.GetSize()[1] + self.border
        self.frame.SetSizeHints(self.wx_config['size'][0], height, self.wx_config['size'][0], height)  # 设置最小和最大宽度为 300，高度为自适应
        self.frame.SetSize(self.wx_config['size'][0], height)
        # 展示控件
        self.frame.Show()
        self.app.MainLoop()

class BatchSkygate(BaseBatchWx):
    def __init__(self) -> None:
        BaseBatchWx.__init__(self)

    def init(self):
        super().init()

        line = self.wx.StaticLine(self.panel)
        self.sizer.Add(line, pos=(self.height, 0), span=(0, 10), flag=self.wx.EXPAND | self.wx.BOTTOM,
                       border=0)
        self.height += 1

    def task(self, *args):
        pass
        
        
        
        # async for data in asyncio.run(ah.wss_block_data()):
        #     print(data)

if __name__ == '__main__':
    wx = BatchSkygate()
    wx.init()
    wx.run()
