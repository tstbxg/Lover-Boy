# -*- coding: utf-8 -*-
"""
超甜情侣每日早安/晚安消息推送【GitHub Actions 单次执行版】
修复：字符串未闭合、乱码、时区问题、环境变量读取、接口重试
"""
import requests
import datetime
import random
import json
import time
import lunardate
import os
import pytz

# ====================== 【核心配置区】从环境变量读取（优先）或默认值 ======================
# 设置默认时区为北京时间
TZ = pytz.timezone('Asia/Shanghai')

CONFIG = {
    # 微信公众号配置（必填，从GitHub Secrets读取）
    "WECHAT_APPID": os.getenv("WECHAT_APPID", ""),
    "WECHAT_APPSECRET": os.getenv("WECHAT_APPSECRET", ""),
    "GIRL_OPENID": os.getenv("GIRL_OPENID", ""),  # 女友的OpenID
    "MY_OPENID": os.getenv("MY_OPENID", ""),      # 自己的OpenID
    
    # 高德天气配置（必填，从GitHub Secrets读取）
    "AMAP_KEY": os.getenv("AMAP_KEY", ""),
    "CITY_NAME": "广州",          # 城市名称（可直接修改）
    "CITY_ADCODE": os.getenv("CITY_ADCODE", ""),  # 城市编码（高德地图查）
    
    # 恋爱/生日配置（必填，直接修改为自己的信息）
    "LOVE_START_DATE": datetime.date(2021, 12, 12),  # 相恋日期
    "GIRL_LUNAR_BIRTH": (2002, 3, 9),                # 女友农历生日(年,月,日)
    "MY_LUNAR_BIRTH": (2003, 3, 13),                  # 自己农历生日(年,月,日)
    
    # 星座配置（可选）
    "GIRL_CONSTELLATION": "金牛座",  # 女友星座
    "MY_CONSTELLATION": "白羊座",    # 自己星座
}

# ====================== 【文案库】可自定义修改 ======================
DAILY_ADVICE = [
    "宝贝，记得按时吃饭，不许挑食哦🍚",
    "乖乖，今天也要多喝水，照顾好自己💧",
    "亲爱的，工作再忙也要歇一歇，别太累🫂",
    "我的小宝，晚上早点睡，不许熬夜啦😴",
    "宝贝，不管多忙，都要记得我在想你💓",
    "乖乖，天气变化记得添减衣服🧥",
    "亲爱的，今天也要开开心心的，不许不开心🥳"
]
LOVE_JOKES = [
    "什么门永远关不上？是我想你的心门呀💘",
    "什么瓜最甜？你这个小傻瓜最甜啦🥰",
    "什么星星最亮？你眼睛里的光最亮✨",
    "什么海最深？对你的喜欢最深不见底🌊",
    "什么糖最甜？你甜甜的笑最甜🍬",
    "什么路最长？想陪你走的余生最长🛤️"
]
CONSTELLATION_TIPS = {
    "金牛座": [
        "今天适合吃点好吃的，好好犒劳自己🍰",
        "别太纠结小事，开心最重要啦🥳",
        "慢一点也没关系，我会一直陪着你🌿",
        "买个小礼物取悦自己，幸福感满满🎁",
        "今天的你温柔又迷人，超有魅力💖"
    ],
    "白羊座": [
        "保持元气满满，好运都会奔向你🍀",
        "勇敢一点，我永远是你的后盾🫂",
        "别太急躁，慢慢来会更顺利✨",
        "今天会有小惊喜在等你哦🎊",
        "你的热情和活力超有感染力💪"
    ],
    "其他星座": [
        "今天的你超棒的，继续闪闪发光✨",
        "保持好心情，万事都会顺顺利利🍀",
        "爱自己是终身浪漫的开始💖"
    ]
}
ENDING_WORDS = [
    "💓 我爱你，今天也超爱你",
    "💓 想你，时时刻刻都在想你",
    "💓 有你在，每一天都很甜",
    "💓 我的温柔与偏爱，全都给你",
    "💓 余生漫漫，我只喜欢你",
    "💓 你是我的满心欢喜与唯一"
]

# ====================== 【工具函数】精准日志打印 ======================
def print_log(level, content):
    now = datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    level_map = {
        "INFO": "[INFO]  ",
        "WARN": "[WARN]  ",
        "ERROR": "[ERROR] ",
        "SUCCESS": "[SUCCESS]"
    }
    print(f"{now} {level_map.get(level, '[INFO]  ')} {content}")

# ====================== 【核心功能函数】（增加重试、时区适配） ======================
def get_access_token(retry=3):
    """获取微信AccessToken，增加重试机制"""
    if not CONFIG["WECHAT_APPID"] or not CONFIG["WECHAT_APPSECRET"]:
        print_log("ERROR", "微信APPID/APPSECRET未配置，获取Token失败")
        return None
    
    url = (f"https://api.weixin.qq.com/cgi-bin/token?"
           f"grant_type=client_credential&appid={CONFIG['WECHAT_APPID']}"
           f"&secret={CONFIG['WECHAT_APPSECRET']}")
    
    for i in range(retry):
        try:
            print_log("INFO", f"第{i+1}次请求微信接口获取AccessToken")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if "access_token" in result and "expires_in" in result:
                print_log("SUCCESS", f"AccessToken获取成功，有效期{result['expires_in']}秒")
                return result["access_token"]
            else:
                print_log("WARN", f"第{i+1}次获取Token失败：{result}")
                time.sleep(1)  # 重试前休眠1秒
        except Exception as e:
            print_log("WARN", f"第{i+1}次获取Token异常：{str(e)}")
            time.sleep(1)
    
    print_log("ERROR", "多次重试后仍无法获取Token")
    return None

def get_weather(retry=2):
    """获取高德天气，增加重试机制"""
    if not CONFIG["AMAP_KEY"] or not CONFIG["CITY_ADCODE"]:
        print_log("ERROR", "高德KEY/城市编码未配置，获取天气失败")
        return "天气获取失败：配置缺失 ❌"
    
    url = (f"https://restapi.amap.com/v3/weather/weatherInfo?"
           f"key={CONFIG['AMAP_KEY']}&city={CONFIG['CITY_ADCODE']}&extensions=all")
    
    for i in range(retry):
        try:
            print_log("INFO", f"第{i+1}次请求高德接口获取天气数据")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") != "1":
                print_log("WARN", f"第{i+1}次获取天气失败：{result.get('info', '未知错误')}")
                time.sleep(1)
                continue
            
            forecast = result["forecasts"][0]["casts"][0]
            weather_info = f"{forecast['dayweather']} 最低{forecast['nighttemp']}℃ | 最高{forecast['daytemp']}℃"
            print_log("SUCCESS", f"天气数据获取成功：{weather_info}")
            return weather_info
        except Exception as e:
            print_log("WARN", f"第{i+1}次获取天气异常：{str(e)}")
            time.sleep(1)
    
    print_log("ERROR", "多次重试后仍无法获取天气")
    return "天气获取失败：接口异常 ❌"

def lunar_to_solar(lunar_year, lunar_month, lunar_day):
    """农历转公历，兼容异常"""
    try:
        return lunardate.LunarDate(lunar_year, lunar_month, lunar_day).toSolarDate()
    except Exception as e:
        print_log("ERROR", f"农历转公历：{str(e)}")
        return datetime.datetime.now(TZ).date()

def get_birthday_left_days(lunar_birth):
    """计算生日倒计时（适配北京时间）"""
    today = datetime.datetime.now(TZ).date()
    lunar_year, lunar_month, lunar_day = lunar_birth
    
    # 计算今年的公历生日
    solar_birth = lunar_to_solar(today.year, lunar_month, lunar_day)
    if solar_birth < today:
        # 今年生日已过，计算明年的
        solar_birth = lunar_to_solar(today.year + 1, lunar_month, lunar_day)
    
    left_days = (solar_birth - today).days
    return left_days

def generate_love_message():
    """生成每日恋爱消息（适配北京时间）"""
    try:
        print_log("INFO", "开始生成每日恋爱消息内容")
        today = datetime.datetime.now(TZ).date()
        love_days = (today - CONFIG["LOVE_START_DATE"]).days
        girl_birth_left = get_birthday_left_days(CONFIG["GIRL_LUNAR_BIRTH"])
        my_birth_left = get_birthday_left_days(CONFIG["MY_LUNAR_BIRTH"])
        weather = get_weather()
        
        # 随机选择文案
        advice = random.choice(DAILY_ADVICE)
        joke = random.choice(LOVE_JOKES)
        girl_const_tip = random.choice(CONSTELLATION_TIPS.get(CONFIG["GIRL_CONSTELLATION"], CONSTELLATION_TIPS["其他星座"]))
        my_const_tip = random.choice(CONSTELLATION_TIPS.get(CONFIG["MY_CONSTELLATION"], CONSTELLATION_TIPS["其他星座"]))
        ending = random.choice(ENDING_WORDS)
        
        # 生日提示文案
        def get_birth_tip(name, days):
            if days == 0:
                return f"🎂 {name}今天生日啦！生日快乐🥳"
            elif 1 <= days <= 7:
                return f"🎂 距离{name}生日还有 {days} 天 🎉 快要过生日啦！"
            else:
                return f"🎂 距离{name}生日还有 {days} 天"
        
        girl_birth_tip = get_birth_tip("宝贝", girl_birth_left)
        my_birth_tip = get_birth_tip("我的", my_birth_left)
        
        # 拼接消息
        message = f"""
🏙️ 城市：{CONFIG['CITY_NAME']}
🌤️ 天气：{weather}
💌 今日叮嘱：{advice}
💑 我们相恋的第 {love_days} 天
{girl_birth_tip}
{my_birth_tip}
😂 专属小情话：{joke}
✨ {CONFIG['GIRL_CONSTELLATION']}：{girl_const_tip}
✨ {CONFIG['MY_CONSTELLATION']}：{my_const_tip}
{ending}
""".strip()
        print_log("SUCCESS", "每日恋爱消息生成成功")
        return message
    except Exception as e:
        print_log("ERROR", f"消息生成失败：{str(e)}")
        return "❤️ 今日甜蜜消息生成失败，宝贝我超想你 ❤️"

def send_wechat_message(openid, token, message, retry=2):
    """发送微信消息，增加重试机制"""
    if not token:
        print_log("ERROR", f"发送消息给{openid}：Token为空")
        return False, "Token为空"
    if not openid:
        print_log("ERROR", "发送消息：OpenID为空")
        return False, "OpenID为空"
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    data = {"touser": openid, "msgtype": "text", "text": {"content": message}}
    
    for i in range(retry):
        try:
            print_log("INFO", f"第{i+1}次发送微信消息给OpenID：{openid}")
            json_data = json.dumps(data, ensure_ascii=False)
            headers = {"Content-Type": "application/json; charset=utf-8"}
            response = requests.post(
                url, 
                data=json_data.encode("utf-8"), 
                headers=headers, 
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("errcode") == 0:
                print_log("SUCCESS", f"消息发送成功给OpenID：{openid}")
                return True, "发送成功"
            else:
                err_msg = f"errcode={result.get('errcode')}, errmsg={result.get('errmsg')}"
                print_log("WARN", f"第{i+1}次发送消息失败给{openid}：{err_msg}")
                time.sleep(1)
        except Exception as e:
            print_log("WARN", f"第{i+1}次发送消息异常给{openid}：{str(e)}")
            time.sleep(1)
    
    print_log("ERROR", f"多次重试后消息发送失败给{openid}")
    return False, "多次重试失败"

def send_daily_message():
    """主执行函数"""
    print_log("INFO", "="*50 + "开始执行每日消息推送任务" + "="*50)
    token = get_access_token()
    if not token:
        print_log("ERROR", "任务终止：无法获取有效的AccessToken")
        return
    
    message = generate_love_message()
    # 发送给女友
    girl_success, girl_msg = send_wechat_message(CONFIG["GIRL_OPENID"], token, message)
    # 发送给自己
    my_success, my_msg = send_wechat_message(CONFIG["MY_OPENID"], token, message)
    
    # 结果汇总
    print_log("INFO", "="*30 + "发送结果汇总" + "="*30)
    print_log("INFO", f"发送给女友：{'成功' if girl_success else '失败'} - {girl_msg}")
    print_log("INFO", f"发送给自己：{'成功' if my_success else '失败'} - {my_msg}")
    
    if girl_success and my_success:
        print_log("SUCCESS", "今日消息推送任务：全部成功 ✅")
    else:
        print_log("ERROR", "今日消息推送任务：部分/全部失败 ❌")
    print_log("INFO", "="*50 + "消息推送任务执行结束" + "="*50 + "\n")

# ====================== 【程序入口：单次执行】 ======================
if __name__ == "__main__":
    print("🎊 超甜情侣每日消息推送【GitHub Actions 单次执行版】🎊\n")
    print_log("INFO", "开始启动前全局配置校验")
    
    # 校验必填配置
    must_config = ["WECHAT_APPID", "WECHAT_APPSECRET", "GIRL_OPENID", "MY_OPENID", "AMAP_KEY", "CITY_ADCODE"]
    miss_config = [k for k in must_config if not CONFIG[k]]
    
    if miss_config:
        print_log("ERROR", f"启动失败：必填配置缺失 - {','.join(miss_config)}")
        exit(1)
    
    print_log("SUCCESS", "全局配置校验通过")
    send_daily_message()
    print_log("INFO", "✅ 单次消息推送任务执行完毕，程序正常退出")
