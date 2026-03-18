# -*- coding: utf-8 -*-
"""
情侣每日消息推送【测试号专用-客服消息版】
特性：测试号100%支持+甜系Emoji+分段排版+星座/生日/天气
适配：GitHub Actions定时执行、北京时间、农历生日、高德天气
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
TZ = pytz.timezone('Asia/Shanghai')

CONFIG = {
    # 微信测试号必填配置
    "WECHAT_APPID": os.getenv("WECHAT_APPID", ""),
    "WECHAT_APPSECRET": os.getenv("WECHAT_APPSECRET", ""),
    "GIRL_OPENID": os.getenv("GIRL_OPENID", ""),  # 女友OpenID（测试号用户列表复制）
    "MY_OPENID": os.getenv("MY_OPENID", ""),      # 自己OpenID（测试号用户列表复制）
    
    # 高德天气必填配置
    "AMAP_KEY": os.getenv("AMAP_KEY", ""),
    "CITY_NAME": "广州",          # 城市名称（可修改）
    "CITY_ADCODE": os.getenv("CITY_ADCODE", ""),  # 城市编码（高德查询）
    
    # 恋爱/生日配置
    "LOVE_START_DATE": datetime.date(2021, 12, 12),  # 相恋日期（改自己的）
    "GIRL_LUNAR_BIRTH": (2002, 3, 9),                # 女友农历生日(年,月,日)
    "MY_LUNAR_BIRTH": (2003, 3, 13),                  # 自己农历生日(年,月,日)
    
    # 星座配置
    "GIRL_CONSTELLATION": "金牛座",  
    "MY_CONSTELLATION": "白羊座",    
}

# ====================== 【自定义文案库】甜系Emoji版 ======================
DAILY_ADVICE = [
    "🥢 宝贝，记得按时吃饭，不许挑食哦～",
    "💧 乖乖，今天也要多喝水，照顾好自己呀",
    "🫂 亲爱的，工作再忙也要歇一歇，别太累啦",
    "😴 我的小宝，晚上早点睡，不许熬夜啦",
    "💓 宝贝，不管多忙，都要记得我在想你",
    "🧥 乖乖，天气变化记得添减衣服哦",
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
    "双子座": [
        "💬 今天适合和喜欢的人聊聊天",
        "🌟 你的有趣会吸引更多美好哦",
        "☕ 忙里偷闲，给自己放个小假吧"
    ],
    "巨蟹座": [
        "🏠 宅家陪陪自己，享受温馨时光",
        "❤️ 你的温柔值得被好好珍惜",
        "🍲 煮一碗热汤，温暖自己呀"
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
    now = datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    level_map = {"INFO": "[INFO]", "WARN": "[WARN]", "ERROR": "[ERROR]", "SUCCESS": "[SUCCESS]"}
    print(f"{now} {level_map.get(level, '[INFO]')} {content}")

def check_config():
    """校验必填配置"""
    must_config = ["WECHAT_APPID", "WECHAT_APPSECRET", "GIRL_OPENID", "MY_OPENID", 
                   "AMAP_KEY", "CITY_ADCODE"]
    miss = [k for k in must_config if not CONFIG[k]]
    if miss:
        print_log("ERROR", f"必填配置缺失：{','.join(miss)}")
        return False
    # 校验OpenID长度
    if len(CONFIG["GIRL_OPENID"]) < 20 or len(CONFIG["MY_OPENID"]) < 20:
        print_log("ERROR", "OpenID格式异常（长度过短），请核对测试号用户列表")
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
    """获取高德天气"""
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
    """计算生日倒计时"""
    today = datetime.datetime.now(TZ).date()
    lunar_year, lunar_month, lunar_day = lunar_birth
    
    try:
        solar_birth = lunardate.LunarDate(today.year, lunar_month, lunar_day).toSolarDate()
        if solar_birth < today:
            solar_birth = lunardate.LunarDate(today.year + 1, lunar_month, lunar_day).toSolarDate()
        return (solar_birth - today).days
    except Exception as e:
        print_log("ERROR", f"计算生日失败：{str(e)}")
        return 0

def generate_love_message():
    """生成接近卡片样式的甜系文本消息"""
    try:
        # 基础数据
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
        
        # 生日提示
        def birth_tip(name, days):
            if days == 0:
                return f"🎂 {name}今天生日啦！生日快乐🥳"
            elif 1 <= days <= 7:
                return f"🎂 距离{name}生日还有 {days} 天 🎉"
            else:
                return f"🎂 距离{name}生日还有 {days} 天"
        
        girl_birth_text = birth_tip("小宝", girl_birth_left)
        my_birth_text = birth_tip("我", my_birth_left)
        
        # 星座建议整合
        const_text = f"🌟 小宝({CONFIG['GIRL_CONSTELLATION']})：{girl_const_tip}\n🌟 我({CONFIG['MY_CONSTELLATION']})：{my_const_tip}"
        
        # 模拟卡片排版（分段+Emoji，测试号100%能显示）
        message = (
            "💌 给小臭屁的每日甜蜜提醒\n"
            "——————————————\n"  # 分割线模拟卡片边框
            f"🏙️ 城市：{CONFIG['CITY_NAME']}\n"
            f"{weather}\n"
            f"💡 今日建议：{advice}\n"
            f"❤️ 恋爱天数：我们相恋的第 {love_days} 天\n"
            f"{girl_birth_text}\n"
            f"{my_birth_text}\n"
            f"{const_text}\n"
            "——————————————\n"
            f"{joke}\n"
            f"{ending}"
        )
        print_log("SUCCESS", "消息生成成功")
        return message
    except Exception as e:
        print_log("ERROR", f"生成消息失败：{str(e)}")
        return "❤️ 今日甜蜜消息生成失败，宝贝我超想你 ❤️"

def send_wechat_msg(openid, token, message):
    """发送客服消息（测试号100%支持）"""
    print_log("INFO", f"准备发送消息至OpenID：{openid[:8]}****")
    
    if not token:
        print_log("ERROR", "❌ Token为空，无法发送")
        return False
    if not openid or len(openid) < 20:
        print_log("ERROR", "❌ OpenID无效（请核对测试号用户列表）")
        return False
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    payload = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": message}
    }
    
    try:
        resp = requests.post(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=15
        )
        print_log("INFO", f"微信客服接口返回：{resp.text}")
        
        result = resp.json()
        if result.get("errcode") == 0:
            print_log("SUCCESS", f"✅ 消息发送成功至{openid[:8]}****")
            return True
        else:
            print_log("ERROR", f"❌ 发送失败：错误码{result['errcode']}，原因{result['errmsg']}")
            return False
    except Exception as e:
        print_log("ERROR", f"❌ 发送异常：{str(e)}")
        return False

# ====================== 【主执行函数】======================
def main():
    print_log("INFO", "========== 开始执行情侣消息推送 ==========")
    
    # 1. 校验配置
    if not check_config():
        return
    
    # 2. 获取Token
    token = get_access_token()
    if not token:
        print_log("ERROR", "获取Token失败，任务终止")
        return
    
    # 3. 生成甜系消息
    love_message = generate_love_message()
    
    # 4. 发送消息（你+女友）
    send_girl = send_wechat_msg(CONFIG["GIRL_OPENID"], token, love_message)
    send_my = send_wechat_msg(CONFIG["MY_OPENID"], token, love_message)
    
    # 5. 结果汇总
    if send_girl and send_my:
        print_log("SUCCESS", "✅ 全部消息发送成功，去公众号聊天框查看！")
    else:
        print_log("ERROR", "❌ 部分/全部消息发送失败，请核对OpenID和用户互动状态")
    
    print_log("INFO", "========== 消息推送任务结束 ==========")

if __name__ == "__main__":
    main()
