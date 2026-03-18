# -*- coding: utf-8 -*-
"""
情侣每日消息推送【最终完整版】
特性：微信模板消息卡片+甜系Emoji+星座建议+容错性强+日志清晰
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
    # 微信公众号必填配置
    "WECHAT_APPID": os.getenv("WECHAT_APPID", ""),
    "WECHAT_APPSECRET": os.getenv("WECHAT_APPSECRET", ""),
    "GIRL_OPENID": os.getenv("GIRL_OPENID", ""),  # 女友OpenID
    "MY_OPENID": os.getenv("MY_OPENID", ""),      # 自己OpenID
    "TEMPLATE_ID": os.getenv("TEMPLATE_ID", ""),  # 模板消息ID（必填！从公众号后台复制）
    
    # 高德天气必填配置
    "AMAP_KEY": os.getenv("AMAP_KEY", ""),
    "CITY_NAME": "广州",          # 城市名称（可修改）
    "CITY_ADCODE": os.getenv("CITY_ADCODE", ""),  # 城市编码（高德查询）
    
    # 恋爱/生日配置
    "LOVE_START_DATE": datetime.date(2021, 12, 12),  # 相恋日期
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
    """校验必填配置（新增模板ID校验）"""
    must_config = ["WECHAT_APPID", "WECHAT_APPSECRET", "GIRL_OPENID", "MY_OPENID", 
                   "AMAP_KEY", "CITY_ADCODE", "TEMPLATE_ID"]
    miss = [k for k in must_config if not CONFIG[k]]
    if miss:
        print_log("ERROR", f"必填配置缺失：{','.join(miss)}")
        return False
    # 校验OpenID长度
    if len(CONFIG["GIRL_OPENID"]) < 20 or len(CONFIG["MY_OPENID"]) < 20:
        print_log("ERROR", "OpenID格式异常（长度过短），请核对")
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

def generate_template_data():
    """生成模板消息所需的字段数据（含星座建议+甜系Emoji）"""
    try:
        # 基础数据
        love_days = (datetime.datetime.now(TZ).date() - CONFIG["LOVE_START_DATE"]).days
        girl_birth_left = get_birthday_left_days(CONFIG["GIRL_LUNAR_BIRTH"])
        my_birth_left = get_birthday_left_days(CONFIG["MY_LUNAR_BIRTH"])
        weather = get_weather()
        
        # 随机文案（含星座建议）
        advice = random.choice(DAILY_ADVICE)
        joke = random.choice(LOVE_JOKES)
        # 读取对应星座的建议，没有则用默认
        girl_const_tip = random.choice(CONSTELLATION_TIPS.get(CONFIG["GIRL_CONSTELLATION"], CONSTELLATION_TIPS["其他星座"]))
        my_const_tip = random.choice(CONSTELLATION_TIPS.get(CONFIG["MY_CONSTELLATION"], CONSTELLATION_TIPS["其他星座"]))
        ending = random.choice(ENDING_WORDS)
        
        # 生日提示（带Emoji）
        def birth_tip(name, days):
            if days == 0:
                return f"🎂 {name}今天生日啦！生日快乐🥳"
            elif 1 <= days <= 7:
                return f"🎂 距离{name}生日还有 {days} 天 🎉"
            else:
                return f"🎂 距离{name}生日还有 {days} 天"
        
        girl_birth_text = birth_tip("小宝", girl_birth_left)
        my_birth_text = birth_tip("我", my_birth_left)
        
        # 整合星座建议
        const_text = f"🌟 小宝({CONFIG['GIRL_CONSTELLATION']})：{girl_const_tip}\n🌟 我({CONFIG['MY_CONSTELLATION']})：{my_const_tip}"
        
        # 模板消息字段（带Emoji，和公众号模板一一对应！）
        template_data = {
            "first": {
                "value": "💌 给小臭屁的每日甜蜜提醒",
                "color": "#173177"
            },
            "keyword1": {  # 城市
                "value": f"🏙️ {CONFIG['CITY_NAME']}",
                "color": "#173177"
            },
            "keyword2": {  # 天气
                "value": weather,  # 天气函数里已经带了🌤️
                "color": "#173177"
            },
            "keyword3": {  # 今日建议
                "value": f"💡 {advice}",
                "color": "#173177"
            },
            "keyword4": {  # 恋爱天数
                "value": f"❤️ 我们相恋的第 {love_days} 天",
                "color": "#173177"
            },
            "keyword5": {  # 生日+星座
                "value": f"{girl_birth_text}\n{my_birth_text}\n{const_text}",
                "color": "#173177"
            },
            "remark": {  # 寄语/结尾
                "value": f"{joke}\n{ending}",
                "color": "#FF69B4"  # 粉色，突出结尾
            }
        }
        print_log("SUCCESS", "模板消息数据生成成功")
        return template_data
    except Exception as e:
        print_log("ERROR", f"生成模板数据失败：{str(e)}")
        # 兜底数据
        return {
            "first": {"value": "💌 每日甜蜜提醒", "color": "#173177"},
            "remark": {"value": "❤️ 宝贝我超想你", "color": "#FF69B4"}
        }

def send_template_msg(openid, token, template_id, data):
    """发送模板消息（核心：卡片样式）"""
    print_log("INFO", f"准备发送模板消息至OpenID：{openid[:8]}****")
    
    if not token:
        print_log("ERROR", "❌ Token为空，无法发送")
        return False
    if not openid or len(openid) < 20:
        print_log("ERROR", "❌ OpenID无效")
        return False
    if not template_id:
        print_log("ERROR", "❌ 模板ID为空")
        return False
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": openid,
        "template_id": template_id,
        "data": data,
        "url": ""  # 点击卡片跳转的链接（可选，留空则不跳转）
    }
    
    try:
        resp = requests.post(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=15
        )
        print_log("INFO", f"微信模板接口返回：{resp.text}")
        
        result = resp.json()
        if result.get("errcode") == 0:
            print_log("SUCCESS", f"✅ 模板消息发送成功至{openid[:8]}****")
            return True
        else:
            print_log("ERROR", f"❌ 发送失败：错误码{result['errcode']}，原因{result['errmsg']}")
            return False
    except Exception as e:
        print_log("ERROR", f"❌ 发送异常：{str(e)}")
        return False

# ====================== 【主执行函数】======================
def main():
    print_log("INFO", "========== 开始执行模板消息推送 ==========")
    
    # 1. 校验配置
    if not check_config():
        return
    
    # 2. 获取Token
    token = get_access_token()
    if not token:
        print_log("ERROR", "获取Token失败，任务终止")
        return
    
    # 3. 生成模板数据
    template_data = generate_template_data()
    
    # 4. 发送模板消息
    send_girl = send_template_msg(CONFIG["GIRL_OPENID"], token, CONFIG["TEMPLATE_ID"], template_data)
    send_my = send_template_msg(CONFIG["MY_OPENID"], token, CONFIG["TEMPLATE_ID"], template_data)
    
    # 5. 结果汇总
    if send_girl and send_my:
        print_log("SUCCESS", "全部模板消息发送成功 ✅")
    else:
        print_log("ERROR", "部分/全部模板消息发送失败 ❌")
    
    print_log("INFO", "========== 模板消息推送任务结束 ==========")

if __name__ == "__main__":
    main()
