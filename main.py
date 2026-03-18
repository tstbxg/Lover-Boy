# -*- coding: utf-8 -*-
"""
情侣每日消息推送【Emoji优化版】
解决：微信消息拦截、缩进错误、格式异常问题
新增：适配风控的精美Emoji表情，视觉更温馨
"""
import requests
import datetime
import random
import json
import time
import lunardate
import os
import pytz

# ====================== 【基础配置】======================
# 时区配置（固定为北京时间）
TZ = pytz.timezone('Asia/Shanghai')

# 核心配置（优先从GitHub Secrets读取，本地测试可直接填写）
CONFIG = {
    # 微信公众号必填配置
    "WECHAT_APPID": os.getenv("WECHAT_APPID", ""),
    "WECHAT_APPSECRET": os.getenv("WECHAT_APPSECRET", ""),
    "GIRL_OPENID": os.getenv("GIRL_OPENID", ""),  # 女友OpenID
    "MY_OPENID": os.getenv("MY_OPENID", ""),      # 自己OpenID
    
    # 高德天气必填配置
    "AMAP_KEY": os.getenv("AMAP_KEY", ""),
    "CITY_NAME": "广州",          # 城市名称（可修改）
    "CITY_ADCODE": os.getenv("CITY_ADCODE", ""),  # 城市编码（高德查询）
    
    # 恋爱/生日配置（直接修改为自己的信息）
    "LOVE_START_DATE": datetime.date(2021, 12, 12),  # 相恋日期
    "GIRL_LUNAR_BIRTH": (2002, 3, 9),                # 女友农历生日(年,月,日)
    "MY_LUNAR_BIRTH": (2003, 3, 13),                  # 自己农历生日(年,月,日)
    
    # 星座配置（可选）
    "GIRL_CONSTELLATION": "金牛座",  # 女友星座
    "MY_CONSTELLATION": "白羊座",    # 自己星座
}

# ====================== 【自定义文案库】带Emoji ======================
DAILY_ADVICE = [
    "🥢 宝贝，记得按时吃饭，不许挑食哦",
    "💧 乖乖，今天也要多喝水，照顾好自己",
    "🫂 亲爱的，工作再忙也要歇一歇，别太累",
    "😴 我的小宝，晚上早点睡，不许熬夜啦",
    "💓 宝贝，不管多忙，都要记得我在想你",
    "🧥 乖乖，天气变化记得添减衣服",
    "🥳 亲爱的，今天也要开开心心的，不许不开心"
]

LOVE_JOKES = [
    "💘 什么门永远关不上？是我想你的心门呀",
    "🥰 什么瓜最甜？你这个小傻瓜最甜啦",
    "✨ 什么星星最亮？你眼睛里的光最亮",
    "🌊 什么海最深？对你的喜欢最深不见底",
    "🍬 什么糖最甜？你甜甜的笑最甜",
    "🛤️ 什么路最长？想陪你走的余生最长"
]

CONSTELLATION_TIPS = {
    "金牛座": [
        "🍰 今天适合吃点好吃的，好好犒劳自己",
        "🥳 别太纠结小事，开心最重要啦",
        "🌿 慢一点也没关系，我会一直陪着你",
        "🎁 买个小礼物取悦自己，幸福感满满",
        "💖 今天的你温柔又迷人，超有魅力"
    ],
    "白羊座": [
        "🍀 保持元气满满，好运都会奔向你",
        "🫂 勇敢一点，我永远是你的后盾",
        "✨ 别太急躁，慢慢来会更顺利",
        "🎊 今天会有小惊喜在等你哦",
        "💪 你的热情和活力超有感染力"
    ],
    "其他星座": [
        "✨ 今天的你超棒的，继续闪闪发光",
        "🍀 保持好心情，万事都会顺顺利利",
        "💖 爱自己是终身浪漫的开始"
    ]
}

ENDING_WORDS = [
    "💓 我爱你，今天也超爱你",
    "💭 想你，时时刻刻都在想你",
    "🍬 有你在，每一天都很甜",
    "💞 我的温柔与偏爱，全都给你",
    "💌 余生漫漫，我只喜欢你",
    "❤️ 你是我的满心欢喜与唯一"
]

# ====================== 【工具函数】======================
def print_log(level, content):
    """格式化日志输出"""
    now = datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    level_map = {"INFO": "[INFO]", "WARN": "[WARN]", "ERROR": "[ERROR]", "SUCCESS": "[SUCCESS]"}
    print(f"{now} {level_map.get(level, '[INFO]')} {content}")

def check_config():
    """校验必填配置"""
    must_config = ["WECHAT_APPID", "WECHAT_APPSECRET", "GIRL_OPENID", "MY_OPENID", "AMAP_KEY", "CITY_ADCODE"]
    miss = [k for k in must_config if not CONFIG[k]]
    if miss:
        print_log("ERROR", f"必填配置缺失：{','.join(miss)}")
        return False
    return True

# ====================== 【核心功能函数】======================
def get_access_token(retry=3):
    """获取微信AccessToken（带重试）"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={CONFIG['WECHAT_APPID']}&secret={CONFIG['WECHAT_APPSECRET']}"
    
    for i in range(retry):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            if "access_token" in result:
                print_log("SUCCESS", "获取AccessToken成功")
                return result["access_token"]
            print_log("WARN", f"获取Token失败({i+1}/{retry})：{result}")
            time.sleep(1)
        except Exception as e:
            print_log("WARN", f"获取Token异常({i+1}/{retry})：{str(e)}")
            time.sleep(1)
    return None

def get_weather():
    """获取高德天气（简化版）"""
    try:
        url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={CONFIG['AMAP_KEY']}&city={CONFIG['CITY_ADCODE']}&extensions=all"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        
        if result.get("status") != "1":
            return "🌤️ 天气获取失败"
        
        forecast = result["forecasts"][0]["casts"][0]
        return f"🌤️ {forecast['dayweather']} 最低{forecast['nighttemp']}℃ | 最高{forecast['daytemp']}℃"
    except Exception as e:
        print_log("ERROR", f"获取天气失败：{str(e)}")
        return "🌤️ 天气获取失败"

def get_birthday_left_days(lunar_birth):
    """计算生日倒计时（农历转公历）"""
    today = datetime.datetime.now(TZ).date()
    lunar_year, lunar_month, lunar_day = lunar_birth
    
    try:
        # 计算今年公历生日
        solar_birth = lunardate.LunarDate(today.year, lunar_month, lunar_day).toSolarDate()
        if solar_birth < today:
            # 今年已过，算明年
            solar_birth = lunardate.LunarDate(today.year + 1, lunar_month, lunar_day).toSolarDate()
        return (solar_birth - today).days
    except Exception as e:
        print_log("ERROR", f"计算生日失败：{str(e)}")
        return 0

def generate_love_message():
    """生成消息（带Emoji，规避风控）"""
    try:
        # 基础数据计算
        love_days = (datetime.datetime.now(TZ).date() - CONFIG["LOVE_START_DATE"]).days
        girl_birth_left = get_birthday_left_days(CONFIG["GIRL_LUNAR_BIRTH"])
        my_birth_left = get_birthday_left_days(CONFIG["MY_LUNAR_BIRTH"])
        weather = get_weather()
        
        # 随机文案
        advice = random.choice(DAILY_ADVICE)
        joke = random.choice(LOVE_JOKES)
        girl_const_tip = random.choice(CONSTELLATION_TIPS.get(CONFIG["GIRL_CONSTELLATION"], CONSTELLATION_TIPS["其他星座"]))
        my_const_tip = random.choice(CONSTELLATION_TIPS.get(CONFIG["MY_CONSTELLATION"], CONSTELLATION_TIPS["其他星座"]))
        ending = random.choice(ENDING_WORDS)
        
        # 生日提示（带Emoji）
        def birth_tip(name, days):
            if days == 0:
                return f"🎂 {name}今天生日啦！生日快乐🥳"
            elif 1 <= days <= 7:
                return f"🎂 距离{name}生日还有 {days} 天 🎉 快要过生日啦！"
            else:
                return f"🎂 距离{name}生日还有 {days} 天"
        
        # 核心：带Emoji的消息格式（数量适中，避免风控）
        message = (
            "💌 给宝宝的每日甜蜜提醒\n"  
            f"🏙️ 城市：{CONFIG['CITY_NAME']}\n"
            f"{weather}\n"
            f"{advice}\n"
            f"💑 我们相恋的第 {love_days} 天\n"
            f"{birth_tip('宝贝', girl_birth_left)}\n"
            f"{birth_tip('我的', my_birth_left)}\n"
            f"{joke}\n"
            f"✨ {CONFIG['GIRL_CONSTELLATION']}：{girl_const_tip}\n"
            f"✨ {CONFIG['MY_CONSTELLATION']}：{my_const_tip}\n"
            f"{ending}"
        )
        print_log("SUCCESS", "消息生成成功")
        return message
    except Exception as e:
        print_log("ERROR", f"生成消息失败：{str(e)}")
        return "❤️ 今日甜蜜消息生成失败，宝贝我超想你 ❤️"

def send_wechat_msg(openid, token, message):
    """发送微信消息（适配Emoji+风控）"""
    if not token or not openid:
        return False
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    data = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": message}
    }
    
    try:
        resp = requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=15
        )
        result = resp.json()
        if result.get("errcode") == 0:
            print_log("SUCCESS", f"消息发送成功至{openid[:8]}****")
            return True
        print_log("ERROR", f"发送失败：{result}")
        return False
    except Exception as e:
        print_log("ERROR", f"发送异常：{str(e)}")
        return False

# ====================== 【主执行函数】======================
def main():
    """程序主入口"""
    print_log("INFO", "========== 开始执行每日消息推送 ==========")
    
    # 1. 校验配置
    if not check_config():
        return
    
    # 2. 获取Token
    token = get_access_token()
    if not token:
        print_log("ERROR", "获取Token失败，任务终止")
        return
    
    # 3. 生成消息
    message = generate_love_message()
    
    # 4. 发送消息
    send_girl = send_wechat_msg(CONFIG["GIRL_OPENID"], token, message)
    send_my = send_wechat_msg(CONFIG["MY_OPENID"], token, message)
    
    # 5. 结果汇总
    if send_girl and send_my:
        print_log("SUCCESS", "全部消息发送成功 ✅")
    else:
        print_log("ERROR", "部分/全部消息发送失败 ❌")
    
    print_log("INFO", "========== 消息推送任务结束 ==========")

if __name__ == "__main__":
    main()
