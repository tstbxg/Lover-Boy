# -*- coding: utf-8 -*-
"""
超甜情侣每日早安/晚安消息推送【优化版】
修复：无成功/失败反馈、异常捕获笼统、逻辑隐性问题
新增：精准日志、关键校验、心跳提示、错误强反馈
功能：天气+恋爱天数+农历生日倒计时+星座运势+暖心文案+定时发送
"""
import requests
import datetime
import random
import json
import time
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
    "DEFAULT_MINUTE": 0,
    # 新增：日志打印间隔（心跳提示，单位：秒）
    "HEARTBEAT_INTERVAL": 300
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

# ====================== 【工具函数】新增：精准日志打印 ======================
def print_log(level, content):
    """
    打印带级别、时间的精准日志
    level: INFO/WARN/ERROR/SUCCESS
    content: 日志内容
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    level_map = {
        "INFO": "[INFO]  ",
        "WARN": "[WARN]  ",
        "ERROR": "[ERROR] ",
        "SUCCESS": "[SUCCESS]"
    }
    print(f"{now} {level_map.get(level, '[INFO]  ')} {content}")

# ====================== 【核心功能函数】优化+精准校验 ======================
def get_access_token():
    """获取微信接口AccessToken | 优化：新增参数校验、精准错误日志"""
    # 前置校验
    if not CONFIG["WECHAT_APPID"] or not CONFIG["WECHAT_APPSECRET"]:
        print_log("ERROR", "微信APPID/APPSECRET未配置，获取Token失败")
        return None
    
    url = (f"https://api.weixin.qq.com/cgi-bin/token?"
           f"grant_type=client_credential&appid={CONFIG['WECHAT_APPID']}"
           f"&secret={CONFIG['WECHAT_APPSECRET']}")
    try:
        print_log("INFO", "开始请求微信接口获取AccessToken")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 抛出HTTP异常
        result = response.json()
        
        if "access_token" in result and "expires_in" in result:
            print_log("SUCCESS", f"AccessToken获取成功，有效期{result['expires_in']}秒")
            return result["access_token"]
        else:
            print_log("ERROR", f"微信接口返回无Token，响应内容：{result}")
            return None
    except requests.exceptions.ConnectTimeout:
        print_log("ERROR", "获取Token：微信接口连接超时")
        return None
    except requests.exceptions.HTTPError as e:
        print_log("ERROR", f"获取Token：微信接口HTTP错误，状态码{e.response.status_code}")
        return None
    except Exception as e:
        print_log("ERROR", f"获取Token：未知异常 - {str(e)}")
        return None

def get_weather():
    """获取今日天气 | 优化：新增参数校验、精准错误日志、返回值校验"""
    # 前置校验
    if not CONFIG["AMAP_KEY"] or not CONFIG["CITY_ADCODE"]:
        print_log("ERROR", "高德KEY/城市编码未配置，获取天气失败")
        return "天气获取失败：配置缺失 ❌"
    
    url = (f"https://restapi.amap.com/v3/weather/weatherInfo?"
           f"key={CONFIG['AMAP_KEY']}&city={CONFIG['CITY_ADCODE']}&extensions=all")
    try:
        print_log("INFO", "开始请求高德接口获取天气数据")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") != "1":
            print_log("ERROR", f"高德接口返回失败，错误信息：{result.get('info', '未知错误')}")
            return "天气获取失败：接口返回错误 ❌"
        if not result.get("forecasts") or not result["forecasts"][0].get("casts"):
            print_log("ERROR", "高德接口返回无天气数据，响应内容异常")
            return "天气获取失败：数据为空 ❌"
        
        forecast = result["forecasts"][0]["casts"][0]
        weather_info = f"{forecast['dayweather']} 最低{forecast['nighttemp']}℃ | 最高{forecast['daytemp']}℃"
        print_log("SUCCESS", f"天气数据获取成功：{weather_info}")
        return weather_info
    except requests.exceptions.ConnectTimeout:
        print_log("ERROR", "获取天气：高德接口连接超时")
        return "天气获取失败：连接超时 ❌"
    except requests.exceptions.HTTPError as e:
        print_log("ERROR", f"获取天气：高德接口HTTP错误，状态码{e.response.status_code}")
        return "天气获取失败：接口错误 ❌"
    except Exception as e:
        print_log("ERROR", f"获取天气：未知异常 - {str(e)}")
        return "天气获取失败：未知错误 ❌"

def lunar_to_solar(lunar_year, lunar_month, lunar_day):
    """农历转公历 | 优化：精准错误日志、参数校验"""
    try:
        if not all(isinstance(x, int) for x in [lunar_year, lunar_month, lunar_day]):
            raise ValueError("农历日期必须为整数")
        if lunar_month < 1 or lunar_month > 12 or lunar_day < 1 or lunar_day > 30:
            raise ValueError("农历日期范围无效")
        return lunardate.LunarDate(lunar_year, lunar_month, lunar_day).toSolarDate()
    except ValueError as e:
        print_log("ERROR", f"农历转公历：参数错误 - {str(e)}")
        return datetime.date.today()
    except Exception as e:
        print_log("ERROR", f"农历转公历：未知异常 - {str(e)}")
        return datetime.date.today()

def get_birthday_left_days(lunar_birth):
    """计算农历生日剩余天数 | 优化：修复逻辑、精准日志"""
    today = datetime.date.today()
    lunar_year, lunar_month, lunar_day = lunar_birth
    print_log("INFO", f"开始计算农历({lunar_year}年{lunar_month}月{lunar_day}日)生日剩余天数")
    
    # 计算今年的公历生日
    solar_birth = lunar_to_solar(today.year, lunar_month, lunar_day)
    # 如果今年生日已过，计算明年的
    if solar_birth < today:
        solar_birth = lunar_to_solar(today.year + 1, lunar_month, lunar_day)
        print_log("INFO", "今年生日已过，计算明年生日剩余天数")
    
    left_days = (solar_birth - today).days
    print_log("SUCCESS", f"生日剩余天数计算成功：{left_days}天（公历{solar_birth.strftime('%Y-%m-%d')}）")
    return left_days

def generate_love_message():
    """生成每日恋爱消息 | 优化：新增日志、异常防护"""
    try:
        print_log("INFO", "开始生成每日恋爱消息内容")
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
        print_log("SUCCESS", "每日恋爱消息生成成功")
        return message
    except Exception as e:
        print_log("ERROR", f"消息生成失败：未知异常 - {str(e)}")
        return "❤️ 今日甜蜜消息生成失败，宝贝我超想你 ❤️"

def send_wechat_message(openid, token, message):
    """发送微信客服消息 | 优化：精准校验、日志、编码防护"""
    # 前置强校验
    if not token:
        print_log("ERROR", f"发送消息给{openid}：Token为空，发送失败")
        return False, "Token为空"
    if not openid:
        print_log("ERROR", "发送消息：OpenID为空，发送失败")
        return False, "OpenID为空"
    if not message:
        print_log("ERROR", f"发送消息给{openid}：消息内容为空，发送失败")
        return False, "消息内容为空"
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    # 构造消息体
    data = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": message}
    }
    
    try:
        print_log("INFO", f"开始发送微信消息给OpenID：{openid}")
        # 手动序列化JSON，关闭ASCII转义
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
            print_log("ERROR", f"消息发送失败给{openid}：{err_msg}")
            return False, err_msg
    except requests.exceptions.ConnectTimeout:
        print_log("ERROR", f"发送消息给{openid}：微信接口连接超时")
        return False, "连接超时"
    except requests.exceptions.HTTPError as e:
        print_log("ERROR", f"发送消息给{openid}：HTTP错误{e.response.status_code}")
        return False, f"HTTP错误{e.response.status_code}"
    except Exception as e:
        print_log("ERROR", f"发送消息给{openid}：未知异常 - {str(e)}")
        return False, f"未知异常{str(e)}"

def send_daily_message():
    """发送每日消息给双方 | 优化：全流程日志、步骤拆分、结果汇总"""
    print_log("INFO", "="*50 + "开始执行每日消息发送任务" + "="*50)
    # 1. 获取AccessToken
    token = get_access_token()
    if not token:
        print_log("ERROR", "任务终止：无法获取有效的AccessToken")
        return
    # 2. 生成消息内容
    message = generate_love_message()
    if not message or "生成失败" in message:
        print_log("WARN", "消息内容生成异常，使用备用消息发送")
    # 3. 发送给女友
    girl_success, girl_msg = send_wechat_message(CONFIG["GIRL_OPENID"], token, message)
    # 4. 发送给自己
    my_success, my_msg = send_wechat_message(CONFIG["MY_OPENID"], token, message)
    # 5. 发送结果汇总
    print_log("INFO", "="*30 + "发送结果汇总" + "="*30)
    print_log("INFO", f"发送给女友：{'成功' if girl_success else '失败'} - {girl_msg}")
    print_log("INFO", f"发送给自己：{'成功' if my_success else '失败'} - {my_msg}")
    if girl_success and my_success:
        print_log("SUCCESS", "今日消息发送任务：全部成功 ✅")
    else:
        print_log("ERROR", "今日消息发送任务：部分/全部失败 ❌")
    print_log("INFO", "="*50 + "每日消息发送任务执行结束" + "="*50 + "\n")

def heartbeat_task():
    """新增：心跳任务，定时打印运行日志，确认程序未卡死"""
    print_log("INFO", f"程序正常运行中，下次心跳{CONFIG['HEARTBEAT_INTERVAL']}秒后 | 等待定时发送任务")

def setup_scheduler():
    """设置定时任务 | 优化：时间强校验、新增心跳任务、精准日志"""
    print_log("INFO", "开始初始化定时调度器")
    # 时间强校验
    hour, minute = CONFIG['DEFAULT_HOUR'], CONFIG['DEFAULT_MINUTE']
    if not (0 <= hour < 24 and 0 <= minute < 60):
        print_log("WARN", f"配置时间{hour}:{minute}不合法，强制使用默认时间9:00")
        hour, minute = 9, 0
    # 初始化调度器（指定时区，避免时间偏移）
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    
    # 添加每日定时发送任务
    scheduler.add_job(
        send_daily_message,
        "cron",
        hour=hour,
        minute=minute,
        name="情侣每日消息推送",
        id="love_message_task"
    )
    # 新增：心跳任务（默认5分钟一次，确认程序运行）
    scheduler.add_job(
        heartbeat_task,
        "interval",
        seconds=CONFIG["HEARTBEAT_INTERVAL"],
        name="程序心跳检测",
        id="heartbeat_task"
    )
    
    # 打印启动信息
    print_log("SUCCESS", "调度器初始化成功！")
    print_log("INFO", f"📅 每日 {hour:02d}:{minute:02d} 自动发送甜系消息")
    print_log("INFO", f"📍 发送城市：{CONFIG['CITY_NAME']}（编码{CONFIG['CITY_ADCODE']}）")
    print_log("INFO", f"💑 相恋起始日：{CONFIG['LOVE_START_DATE'].strftime('%Y年%m月%d日')}")
    print_log("INFO", f"❤️ 心跳检测：每{CONFIG['HEARTBEAT_INTERVAL']}秒打印一次运行日志")
    print_log("INFO", "💡 按 Ctrl+C 可手动停止程序\n")
    
    # 启动调度器
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print_log("INFO", "程序被手动终止（Ctrl+C），正在关闭调度器...")
        scheduler.shutdown()
        print_log("SUCCESS", "调度器已正常关闭，程序退出 ✅")
    except Exception as e:
        print_log("ERROR", f"调度器运行异常 - {str(e)}")
        scheduler.shutdown()
        print_log("ERROR", "调度器已强制关闭，程序退出 ❌")

# ====================== 【程序入口】优化：新增测试开关、配置校验 ======================
if __name__ == "__main__":
    print("🎊 超甜情侣每日消息推送【优化版】🎊\n")
    # 启动前全局配置校验
    print_log("INFO", "开始启动前全局配置校验")
    must_config = ["WECHAT_APPID", "WECHAT_APPSECRET", "GIRL_OPENID", "MY_OPENID", "AMAP_KEY", "CITY_ADCODE"]
    miss_config = [k for k in must_config if not CONFIG[k]]
    if miss_config:
        print_log("ERROR", f"启动失败：必填配置缺失 - {','.join(miss_config)}，请完善核心配置区！")
        exit(1)
    print_log("SUCCESS", "全局配置校验通过，无缺失项")
    
    # 测试开关：y=启动后立即发送一次（测试用），n=仅启动定时任务
    send_test = input("\n是否启动后立即发送测试消息？(y/n，默认n)：").strip().lower() or "n"
    if send_test == "y":
        print_log("INFO", "用户选择启动测试，立即执行一次消息发送任务")
        send_daily_message()
        print_log("INFO", "测试任务执行完毕，即将启动定时调度器...\n")
        time.sleep(3)
    
    # 启动定时调度器
    setup_scheduler()
