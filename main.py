# -*- coding: utf-8 -*-
"""
超甜情侣每日早安/晚安消息推送
功能：天气+恋爱天数+农历生日倒计时+星座运势+暖心文案+定时发送
"""
import requests
import datetime
import random
import json
from apscheduler.schedulers.blocking import BlockingScheduler
import lunardate

# ====================== 【核心配置区】请修改为自己的信息 ======================
CONFIG = {
    # 微信公众号配置（必填）
    "WECHAT_APPID": "wx527b9473371af8fd",
    "WECHAT_APPSECRET": "3a9dea7c2da6be5b036672b45882f3d5",
    "GIRL_OPENID": "ohNC759FgSfc_DqfePQhxPBg1klk",  # 女友的OpenID
    "MY_OPENID": "ohNC7502wcmBzkSGxzxF1vOVuuGg",    # 自己的OpenID
    
    # 高德天气配置（必填）
    "AMAP_KEY": "cb324fe1361f796a101534ec0fc14d51",
    "CITY_NAME": "广州",          # 城市名称
    "CITY_ADCODE": "440100",      # 城市编码（高德地图查）
    
    # 恋爱/生日配置（必填）
    "LOVE_START_DATE": datetime.date(2021, 12, 12),  # 相恋日期
    "GIRL_LUNAR_BIRTH": (2002, 3, 9),                # 女友农历生日(年,月,日)
    "MY_LUNAR_BIRTH": (2003, 3, 13),                  # 自己农历生日(年,月,日)
    
    # 星座配置（可选）
    "GIRL_CONSTELLATION": "金牛座",  # 女友星座
    "MY_CONSTELLATION": "白羊座",    # 自己星座
    
    # 默认发送时间（可运行时修改）
    "DEFAULT_HOUR": 9,
    "DEFAULT_MINUTE": 0
}

# ====================== 【文案库】可自定义修改 ======================
# 每日暖心叮嘱
DAILY_ADVICE = [
    "宝贝，记得按时吃饭，不许挑食哦🍚",
    "乖乖，今天也要多喝水，照顾好自己💧",
    "亲爱的，工作再忙也要歇一歇，别太累🫂",
    "我的小宝，晚上早点睡，不许熬夜啦😴",
    "宝贝，不管多忙，都要记得我在想你💓",
    "乖乖，天气变化记得添减衣服🧥",
    "亲爱的，今天也要开开心心的，不许不开心🥳"
]

# 专属小情话/冷笑话
LOVE_JOKES = [
    "什么门永远关不上？是我想你的心门呀💘",
    "什么瓜最甜？你这个小傻瓜最甜啦🥰",
    "什么星星最亮？你眼睛里的光最亮✨",
    "什么海最深？对你的喜欢最深不见底🌊",
    "什么糖最甜？你甜甜的笑最甜🍬",
    "什么路最长？想陪你走的余生最长🛤️"
]

# 星座运势
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

# 结尾情话
ENDING_WORDS = [
    "💓 我爱你，今天也超爱你",
    "💓 想你，时时刻刻都在想你",
    "💓 有你在，每一天都很甜",
    "💓 我的温柔与偏爱，全都给你",
    "💓 余生漫漫，我只喜欢你",
    "💓 你是我的满心欢喜与唯一"
]

# ====================== 【核心功能函数】 ======================
def get_access_token():
    """获取微信接口AccessToken"""
    url = (f"https://api.weixin.qq.com/cgi-bin/token?"
           f"grant_type=client_credential&appid={CONFIG['WECHAT_APPID']}"
           f"&secret={CONFIG['WECHAT_APPSECRET']}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 抛出HTTP异常
        result = response.json()
        if "access_token" in result:
            return result["access_token"]
        else:
            print(f"❌ 获取Token失败：{result}")
            return None
    except Exception as e:
        print(f"❌ 获取Token异常：{str(e)}")
        return None

def get_weather():
    """获取今日天气"""
    url = (f"https://restapi.amap.com/v3/weather/weatherInfo?"
           f"key={CONFIG['AMAP_KEY']}&city={CONFIG['CITY_ADCODE']}&extensions=all")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == "1" and result.get("forecasts"):
            forecast = result["forecasts"][0]["casts"][0]
            return (f"{forecast['dayweather']} "
                    f"最低{forecast['nighttemp']}℃ | 最高{forecast['daytemp']}℃")
        else:
            return "天气数据获取成功 ☁️"
    except Exception as e:
        print(f"❌ 获取天气异常：{str(e)}")
        return "天气数据获取中 ☁️"

def lunar_to_solar(lunar_year, lunar_month, lunar_day):
    """农历转公历"""
    try:
        return lunardate.LunarDate(lunar_year, lunar_month, lunar_day).toSolarDate()
    except Exception as e:
        print(f"❌ 农历转换异常：{str(e)}")
        return datetime.date.today()

def get_birthday_left_days(lunar_birth):
    """计算农历生日剩余天数"""
    today = datetime.date.today()
    lunar_year, lunar_month, lunar_day = lunar_birth
    
    # 计算今年的公历生日
    try:
        solar_birth = lunar_to_solar(today.year, lunar_month, lunar_day)
    except:
        solar_birth = lunar_to_solar(today.year + 1, lunar_month, lunar_day)
    
    # 如果今年生日已过，计算明年的
    if solar_birth < today:
        solar_birth = lunar_to_solar(today.year + 1, lunar_month, lunar_day)
    
    return (solar_birth - today).days

def generate_love_message():
    """生成每日恋爱消息"""
    # 基础数据
    today = datetime.date.today()
    love_days = (today - CONFIG["LOVE_START_DATE"]).days
    girl_birth_left = get_birthday_left_days(CONFIG["GIRL_LUNAR_BIRTH"])
    my_birth_left = get_birthday_left_days(CONFIG["MY_LUNAR_BIRTH"])
    weather = get_weather()
    
    # 文案随机选择
    advice = random.choice(DAILY_ADVICE)
    joke = random.choice(LOVE_JOKES)
    girl_const_tip = random.choice(CONSTELLATION_TIPS.get(
        CONFIG["GIRL_CONSTELLATION"], CONSTELLATION_TIPS["其他星座"]))
    my_const_tip = random.choice(CONSTELLATION_TIPS.get(
        CONFIG["MY_CONSTELLATION"], CONSTELLATION_TIPS["其他星座"]))
    ending = random.choice(ENDING_WORDS)
    
    # 生日提示（带特殊标记）
    def get_birth_tip(name, days):
        if days == 0:
            return f"🎂 {name}今天生日啦！生日快乐🥳"
        elif 1 <= days <= 7:
            return f"🎂 距离{name}生日还有 {days} 天 🎉 快要过生日啦！"
        else:
            return f"🎂 距离{name}生日还有 {days} 天"
    
    girl_birth_tip = get_birth_tip("宝贝", girl_birth_left)
    my_birth_tip = get_birth_tip("我的", my_birth_left)
    
    # 拼接最终消息
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
    
    return message

def send_wechat_message(openid, token, message):
    """发送微信客服消息（支持emoji不乱码）"""
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    
    # 构造消息体，确保emoji和中文正常
    data = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": message}
    }
    
    # 手动序列化JSON，关闭ASCII转义
    json_data = json.dumps(data, ensure_ascii=False)
    headers = {"Content-Type": "application/json; charset=utf-8"}
    
    try:
        response = requests.post(
            url,
            data=json_data.encode("utf-8"),
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("errcode") == 0:
            return True, "发送成功"
        else:
            return False, f"发送失败：{result}"
    except Exception as e:
        return False, f"发送异常：{str(e)}"

def send_daily_message():
    """发送每日消息给双方"""
    print("\n===== 开始发送每日消息 =====")
    
    # 1. 获取AccessToken
    token = get_access_token()
    if not token:
        print("❌ 无法获取AccessToken，发送终止")
        return
    
    # 2. 生成消息内容
    message = generate_love_message()
    print(f"📝 今日消息内容：\n{message}\n")
    
    # 3. 发送给女友
    girl_success, girl_msg = send_wechat_message(CONFIG["GIRL_OPENID"], token, message)
    print(f"👩❤️👨 发送给女友：{girl_msg}")
    
    # 4. 发送给自己
    my_success, my_msg = send_wechat_message(CONFIG["MY_OPENID"], token, message)
    print(f"💏 发送给自己：{my_msg}")
    
    # 5. 发送结果汇总
    if girl_success and my_success:
        print("✅ 今日消息发送全部成功！")
    else:
        print("❌ 部分消息发送失败，请检查配置！")

def setup_scheduler():
    """设置定时任务"""
    # 使用配置默认时间（适配自动化环境）
hour, minute = CONFIG['DEFAULT_HOUR'], CONFIG['DEFAULT_MINUTE']
    
    # 初始化调度器
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    
    # 添加每日定时任务
    scheduler.add_job(
        send_daily_message,
        "cron",
        hour=hour,
        minute=minute,
        name="情侣每日消息推送"
    )
    
    print(f"\n🚀 程序启动成功！")
    print(f"📅 每日 {hour:02d}:{minute:02d} 自动发送甜系消息")
    print(f"📍 发送城市：{CONFIG['CITY_NAME']}")
    print(f"💑 相恋起始日：{CONFIG['LOVE_START_DATE'].strftime('%Y年%m月%d日')}")
    print("💡 按 Ctrl+C 可停止程序\n")
    
    # 启动调度器
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n🛑 程序已手动停止")
        scheduler.shutdown()
    except Exception as e:
        print(f"\n❌ 调度器异常：{str(e)}")
        scheduler.shutdown()

# ====================== 【程序入口】 ======================
if __name__ == "__main__":
    print("🎊 超甜情侣每日消息推送程序 🎊")
    print("=" * 40)
    
    # 启动定时任务

    setup_scheduler()

