import os
import math
import random
import xmltodict
import base64
import pymysql
import datetime
import traceback
import csv
import requests
from PIL import Image, ImageFont, ImageDraw
from fuzzywuzzy import fuzz
from .config import apu_db, bot_db, mail_cfg
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from io import BytesIO
from hoshino import Service
from hoshino.service import sucmd
from hoshino.typing import CQEvent, CommandSession

nowdir = os.getcwd()

help_str='''PIGEON TECH 小助手
(英文命令需使用小写)
功能及其对应命令列表：
* 每日签到随机获取积分
- 签到
- /sdvx sign
* 5555积分兑换25游戏次数
- 积分兑换
* 根据用户名查询SDVX ID
- /sdvx user [用户名(必填)]
* 绑定SDVX账号[支持APU/GUGUGU网]
- /sdvx bind [SDVX ID(必填)]
* 查询账号VOLFORCE
- /sdvx b50 [SDVX ID(可选)]
- /sdvx vf [SDVX ID(可选)]
- vf [SDVX ID(可选)]
* 查询最近SDVX成绩
- /sdvx rc
- /sdvx recent
* SDVX随机抽歌
- /sdvx rd [等级(可选)]
- SDVX抽歌 [等级(可选)]
* 根据乐曲id查询SDVX曲目信息
- /sdvx id [乐曲ID(必填)]
* 设置SDVX机台游玩选项
  (类型:1-BGM,2-副屏背景,3-打歌面板,4-表情贴纸)
  (贴纸位置为1-8，分别为fxL/R按下时的btA-D)
- /sdvx set [类型] [位置(如果为表情时)] [ID]'''

sv = Service(
    name='SDVX小助手', 
    visible=True,
    bundle='娱乐',
    help_= help_str.strip())

from decimal import Decimal,ROUND_HALF_UP
#把处理格式的单独定义成一个函数
def round_dec(n,d):
  s = '0.' + '0' * d
  return float(Decimal(str(n)).quantize(Decimal(s),ROUND_HALF_UP).quantize(Decimal('0.0')))
# 获取列表的第二个元素
def takeSecond(elem):
    return elem[1]
    
def circle_corner(img, radii):  #把原图片变成圆角，这个函数是从网上找的，原址 https://www.pyget.cn/p/185266
    """
    圆角处理
    :param img: 源图象。
    :param radii: 半径，如：30。
    :return: 返回一个圆角处理后的图象。
    """
    # 画圆（用于分离4个角）
    circle = Image.new('L', (radii * 2, radii * 2), 0)  # 创建一个黑色背景的画布
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radii * 2, radii * 2), fill=255)  # 画白色圆形
    # 原图
    img = img.convert("RGBA")
    w, h = img.size
    # 画4个角（将整圆分离为4个部分）
    alpha = Image.new('L', img.size, 255)
    alpha.paste(circle.crop((0, 0, radii, radii)), (0, 0))  # 左上角
    alpha.paste(circle.crop((radii, 0, radii * 2, radii)), (w - radii, 0))  # 右上角
    alpha.paste(circle.crop((radii, radii, radii * 2, radii * 2)), (w - radii, h - radii))  # 右下角
    alpha.paste(circle.crop((0, radii, radii, radii * 2)), (0, h - radii))  # 左下角
    # alpha.show()
    img.putalpha(alpha)  # 白色区域透明可见，黑色区域不可见
    return img

async def get_usericon(user):
    """通过Q号获取QQ头像。"""
    p_icon = requests.get(f'https://q1.qlogo.cn/g?b=qq&nk={user}&s=640')
    return p_icon

# id找各种东西
def id_search_bgm(parem_id):
    """
    id找乐曲名称，返回值为名称
    """
    parem_id = str(parem_id)
    # 打开csv文件 
    with open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\bgm.csv", "r", encoding="utf-8") as f:
        # 使用csv模块读取文件内容
        reader = csv.reader(f)
        # 逐行遍历文件内容
        for row in reader:
            # 获取第二列数值和第三列名称
            num = row[0]
            name = row[1]
            # 判断数值是否匹配输入的parem_id
            if num == parem_id:
                return name
    # 如果未找到匹配项，则返回None
    f.close()
    return None

def id_search_touch(parem_id):
    """
    id找触摸板名称，返回值为名称
    """
    parem_id = str(parem_id)
    # 打开csv文件
    with open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\touch.csv", "r", encoding="utf-8") as f:
        # 使用csv模块读取文件内容
        reader = csv.reader(f)
        # 逐行遍历文件内容
        for row in reader:
            # 获取第二列数值和第三列名称
            num = row[0]
            name = row[1]
            # 判断数值是否匹配输入的parem_id
            if num == parem_id:
                return name
    # 如果未找到匹配项，则返回None
    f.close()
    return None

def id_search_panel(parem_id):
    """
    id找打歌面板名称，返回值为名称
    """
    parem_id = str(parem_id)
    # 打开csv文件
    with open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\panel.csv", "r", encoding="utf-8") as f:
        # 使用csv模块读取文件内容
        reader = csv.reader(f)
        # 逐行遍历文件内容
        for row in reader:
            # 获取第二列数值和第三列名称
            num = row[0]
            name = row[1]
            # 判断数值是否匹配输入的parem_id
            if num == parem_id:
                return name
    # 如果未找到匹配项，则返回None
    f.close()
    return None

def id_search_stamp(parem_id):
    """
    id找贴纸名称，返回值为名称
    """
    parem_id = str(parem_id)
    # 打开csv文件
    with open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\stamp.csv", "r", encoding="utf-8") as f:
        # 使用csv模块读取文件内容
        reader = csv.reader(f)
        # 逐行遍历文件内容
        for row in reader:
            # 获取第二列数值和第三列名称
            num = row[0]
            name = row[1]
            # 判断数值是否匹配输入的parem_id
            if num == parem_id:
                return name
    # 如果未找到匹配项，则返回None
    f.close()
    return None

# 缓存全部玩家数据
result_playername = []
def get_player_list_cache():
    """
    调用该函数可以从数据库中获取最新的全部玩家数据存储至result_playername全局变量\n

    """
    global result_playername
    db_apu = pymysql.connect(
                        host=apu_db.host,
                        port=apu_db.port,
                        user=apu_db.user,
                        password=apu_db.password,
                        database=apu_db.database
                        )
    apu_cursor = db_apu.cursor()
    apu_get_player_name = "SELECT f_id,f_name FROM m_user"
    try:
        apu_cursor.execute(apu_get_player_name)
        result_playername = apu_cursor.fetchall()
    except:
        print("err")
    db_apu.close()

# 初始化加载时先执行一次函数获取全局玩家缓存
get_player_list_cache()

# 获取玩家名称
def get_player_name(f_id):
    """
    通过SDVXID获取名称
    :param f_id: 玩家SDVX ID
    :return: 玩家名称
    """
    global result_playername
    for player in result_playername:
        if player[0] == f_id:
            player_name = player[1]
            return player_name
    return False

async def send_mail(user_name:str ,user_mail:str, title:str, message:str):
    '''
    使用阿里云的SMTP发送邮件
    :param user_name: 用户昵称
    :param user_mail: 电子邮箱账号
    :param title: 邮箱标题
    :param message: 要发送的内容
    :return: 是否发送成功
    '''
    ret=True
    try:
        my_sender = mail_cfg.adr    # 发件人邮箱账号
        my_pass = mail_cfg.pw              # 发件人邮箱密码
        msg = MIMEText(message,'plain','utf-8')
        msg['From'] = formataddr(["BEMALOW_TECH",my_sender])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
        msg['To'] = formataddr([user_name,user_mail])              # 括号里的对应收件人邮箱昵称、收件人邮箱账号
        msg['Subject']= title                # 邮件的主题，也可以说是标题
 
        server=smtplib.SMTP(mail_cfg.server, 25)  # 发件人邮箱中的SMTP服务器，端口是25
        server.login(my_sender, my_pass)  # 括号中对应的是发件人邮箱账号、邮箱密码
        server.sendmail(my_sender,[user_mail,],msg.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        server.quit()  # 关闭连接
    except Exception:  # 如果 try 中的语句没有执行，则会执行下面的 ret=False
        ret=False
        traceback.print_exc()
    return ret

# 查询积分
@sv.on_fullmatch(('积分','积分查询','查询积分'))
async def chaxun(bot, ev: CQEvent):
    db_bot = pymysql.connect(
        host=bot_db.host,
        port=bot_db.port,
        user=bot_db.user,
        password=bot_db.password,
        database=bot_db.database
    )
    apu_cursor = db_bot.cursor()
    qqid = ev.user_id
    # 获取Q号/积分/上次签到时间/连续签到天数/上次抽奖时间/单天抽奖次数
    apu_cx_sql = "SELECT QQ,jifei,scqdsj,lxqdts,sccjsj,dtcjcs FROM grxx WHERE QQ = %s" % (qqid)
    try:
        apu_cursor.execute(apu_cx_sql)
        result_cx = apu_cursor.fetchall()
        if not result_cx:
            await bot.send(ev, "查询结果为空", at_sender = True)
        else:
            point = result_cx[0][1]
            cx_qd_date = result_cx[0][2]
            cx_lianxu_date = result_cx[0][3]
            cx_choujiang_date = result_cx[0][4]
            cx_choujiang_lianxu_times = result_cx[0][5]
            today = datetime.date.today()
            today_str = "%s年%s月%s日" % (today.year, today.month, today.day)
            if today_str != cx_choujiang_date:
                cx_choujiang_lianxu_times = 0
            await bot.send(ev, "QQ: %s\n积分数量: %s\n上次签到时间: %s\n签到次数: %s\n当天已抽奖次数: %s" %(qqid, point, cx_qd_date, cx_lianxu_date, cx_choujiang_lianxu_times), at_sender = True)
    except Exception as e:
        print(str(e))
    db_bot.close()

@sv.on_fullmatch(('签到','簽到','/sdvx sign'))
async def qiandao(bot, ev: CQEvent):
    await bot.send(ev, '正在签到中...')
    db_bot = pymysql.connect(
        host=bot_db.host,
        port=bot_db.port,
        user=bot_db.user,
        password=bot_db.password,
        database=bot_db.database
    )
    apu_cursor = db_bot.cursor()
    qqid = ev.user_id
    groupid = ev.group_id
    # 获取Q号/积分/上次签到时间/连续签到天数/上次抽奖时间/单天抽奖次数
    apu_qd_sql = "SELECT QQ,jifei,scqdsj,lxqdts,sccjsj,dtcjcs FROM grxx WHERE QQ = %s" % (qqid)
    try:
        apu_cursor.execute(apu_qd_sql)
        result_qd = apu_cursor.fetchall()
        # 判断结果是否为空，若为空则插入新数据（新用户注册）
        if not result_qd:
            #插入新数据
            add_mem_sql = "INSERT INTO `grxx` (`Qqun`, `QQ`, `jifei`, `scqdsj`, `lxqdts`) VALUES ('%s', '%s', '0', '0', '0')" %(groupid, qqid)
            try:
                apu_cursor.execute(add_mem_sql)
                db_bot.commit()
                apu_cursor.execute(apu_qd_sql)
                result_qd = apu_cursor.fetchall()
            except Exception as e:
                await bot.send(ev, '错误:' + str(e))
                db_bot.rollback
        point = result_qd[0][1]
        qd_date = result_qd[0][2]
        qd_lianxu_date = result_qd[0][3]
        cj_date = result_qd[0][4]
        cj_times = result_qd[0][5]
        today = datetime.date.today()
        today_str = "%s年%s月%s日" % (today.year, today.month, today.day)
        if today_str == qd_date:
            await bot.send(ev, "您今天已经签到了噢，请不要再次签到了", at_sender=True)
        else:
            try:
                # UPDATE `grxx` SET `jifei`='5402', `lxqdts`='2' WHERE (`Qqun`='205194089') AND (`QQ`='1085636071')
                get_point = random.randint(1,100)
                point = point + get_point
                qd_lianxu_date += 1
                update_sql = "UPDATE `grxx` SET `jifei`='%s' ,`lxqdts`='%s' ,`scqdsj`='%s' WHERE `QQ`='%s'" % (point, qd_lianxu_date, today_str, qqid)
                apu_cursor.execute(update_sql)
                db_bot.commit()

                with Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\签到.png") as qd_bg:
                    font_main = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 12)
                    font_time = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 10)
                    draw = ImageDraw.Draw(qd_bg)
                    point_txt = f'总积分:{point}'
                    p_tl,tt,p_tr,tb = font_main.getbbox(point_txt)
                    p_x = 99 - (p_tr - p_tl) / 2
                    draw.text((p_x, 127), point_txt, 'black', font_main)
                    get_point_txt = f'+{get_point} 积分'
                    gp_tl,tt,gp_tr,tb = font_main.getbbox(get_point_txt)
                    gp_x = 99 - (gp_tr - gp_tl) / 2
                    draw.text((gp_x, 187), get_point_txt, 'black', font_main)
                    time_txt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    t_tl,tt,t_tr,tb = font_time.getbbox(time_txt)
                    t_x = 99 - (t_tr - t_tl) / 2
                    draw.text((t_x, 217), time_txt, 'black', font_time)
                    qq_img = Image.open(BytesIO((await get_usericon(f'{qqid}')).content)).resize((100,100)).convert("RGBA")
                    qd_bg.paste(qq_img,(49,15),qq_img)
                    qd_bg.save(nowdir + f'\\hoshino\\modules\\sdvx_helper\\qd\\{qqid}.png') # 保存图片
                    
                data = open(nowdir + f'\\hoshino\\modules\\sdvx_helper\\qd\\{qqid}.png', "rb")
                base64_str = base64.b64encode(data.read())
                img_b64 =  b'base64://' + base64_str
                img_b64 = str(img_b64, encoding = "utf-8")  
                await bot.send(ev, f'[CQ:image,file={img_b64}]', at_sender = True)
                # await bot.send(ev, "签到成功！获得 %s 积分\n您当前已签到 %s 天\n当前共有 %s 积分" %(get_point, qd_lianxu_date, point), at_sender=True)
            except Exception as e:
                await bot.send(ev, '错误:' + str(e))
                db_bot.rollback()
    except Exception as e:
        print(e.args)
        await bot.send(ev, '错误:' + str(e))
    db_bot.close()

@sv.on_fullmatch(('抽奖'))
async def choujiang(bot, ev:CQEvent):
    db_bot = pymysql.connect(
        host=bot_db.host,
        port=bot_db.port,
        user=bot_db.user,
        password=bot_db.password,
        database=bot_db.database
    )
    apu_cursor = db_bot.cursor()
    qqid = ev.user_id
    # 获取Q号/积分/上次抽奖时间/单天抽奖次数
    apu_cj_sql = "SELECT QQ,jifei,sccjsj,dtcjcs FROM grxx WHERE QQ = %s" % (qqid)
    try:
        apu_cursor.execute(apu_cj_sql)
        result_cx = apu_cursor.fetchall()
        if not result_cx:
            await bot.send(ev, "请至少签到一次再来进行抽奖", at_sender = True)
        else:
            point = result_cx[0][1]
            choujiang_date = result_cx[0][2]
            choujiang_lianxu_times = result_cx[0][3]
            today = datetime.date.today()
            today_str = "%s年%s月%s日" % (today.year, today.month, today.day)
            if today_str != choujiang_date:
                choujiang_date = today_str
                choujiang_lianxu_times = 0
            # 抽奖部分
            if choujiang_lianxu_times >= 5:
                await bot.send(ev, "小抽怡情，大抽伤身！\n您今天抽奖太多次了，请改天再来吧！", at_sender = True)
            else:
                try:
                    get_point = random.randint(1,100)
                    point = point - 50 + get_point
                    choujiang_lianxu_times += 1
                    update_sql = "UPDATE `grxx` SET `jifei`='%s' ,`dtcjcs`='%s' ,`sccjsj`='%s' WHERE `QQ`='%s'" % (point, choujiang_lianxu_times, today_str, qqid)
                    apu_cursor.execute(update_sql)
                    db_bot.commit()

                    image = Image.new('RGB', (400, 200), (255,255,255)) # 设置画布大小及背景色
                    iwidth, iheight = image.size # 获取画布高宽
                    draw = ImageDraw.Draw(image)
                    font_main = ImageFont.truetype(nowdir + f'\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf', 50)
                    draw.text((10, 5), '抽奖成功', 'black', font_main)
                    font = ImageFont.truetype(nowdir + f'\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf', 30) # 设置字体及字号
                    fontx = 10
                    fonty = 70
                    draw.text((fontx, fonty), f'获得 {get_point - 50} 金币', 'black', font)
                    fonty += 40
                    draw.text((fontx, fonty), f'您今日已抽奖 {choujiang_lianxu_times} 次', 'black', font)
                    fonty += 40
                    draw.text((fontx, fonty), f'当前共有 {point} 金币', 'black', font)
                    image.save(nowdir + f'\\hoshino\\modules\\sdvx_helper\\cj\\{qqid}.jpg') # 保存图片
                    data = open(nowdir + f'\\hoshino\\modules\\sdvx_helper\\cj\\{qqid}.jpg', "rb")
                    base64_str = base64.b64encode(data.read())
                    img_b64 =  b'base64://' + base64_str
                    img_b64 = str(img_b64, encoding = "utf-8")  
                    await bot.send(ev, f'[CQ:image,file={img_b64}]', at_sender = True)
                    # await bot.send(ev, "抽奖成功！获得 %s 积分\n您今天已抽奖 %s 次\n当前共有 %s 积分" %(get_point, choujiang_lianxu_times, point), at_sender = True)
                except Exception as e:
                    print(str(e))
                    db_bot.rollback()
    except Exception as e:
        print(str(e))
    db_bot.close()

@sv.on_fullmatch(('积分兑换'))
async def duihuan(bot, ev: CQEvent):
    db_bot = pymysql.connect(
        host=bot_db.host,
        port=bot_db.port,
        user=bot_db.user,
        password=bot_db.password,
        database=bot_db.database
    )
    apu_cursor = db_bot.cursor()
    qqid = ev.user_id
    groupid = ev.group_id
    # 获取Q号/积分/上次抽奖时间/单天抽奖次数
    apu_cj_sql = "SELECT QQ,jifei,sccjsj,dtcjcs FROM grxx WHERE QQ = %s" % (qqid)
    try:
        apu_cursor.execute(apu_cj_sql)
        result_cx = apu_cursor.fetchall()
        if not result_cx:
            await bot.send(ev, "都没有签到过，怎么兑换呢？", at_sender = True)
        else:
            point = result_cx[0][1]
            if point > 5555:
                get_dhm_sql = "SELECT * FROM `dhm` WHERE `dhqq` LIKE '%空%' ORDER BY `zj` LIMIT 1"
                apu_cursor.execute(get_dhm_sql)
                result_dhm = apu_cursor.fetchall()
                if not result_dhm:
                    await bot.send_private_msg(user_id=qqid, group_id=groupid, message=f'兑换码数量不足，请联系管理员补充。')
                else:
                    try:
                        zj = result_dhm[0][0]
                        dhm = result_dhm[0][4]
                        point -= 5555
                        update_dhm_sql = f"UPDATE `dhm` SET `dhqq`='{qqid}' WHERE (`zj`='{zj}')"
                        update_point_sql = f"UPDATE `grxx` SET `jifei`='{point}' WHERE `QQ`='{qqid}'"
                        apu_cursor.execute(update_dhm_sql)
                        apu_cursor.execute(update_point_sql)
                        db_bot.commit()
                        success = 1
                    except:
                        db_bot.rollback()
            else:
                await bot.send(ev, message='您的积分不够5555点，暂时无法兑换噢~', at_sender=True)
    except:
        await bot.send(ev, '兑换失败...')
    db_bot.close()
    if success == 1:
        if await send_mail("user",f"{qqid}@qq.com","[BEMALOW_TECH]您的广西卡游戏次数兑换码",f"您的25次游戏次数兑换码为:{dhm}\n请妥善保管"):
            await bot.send(ev, message='兑换成功！请在您的QQ邮箱查看您兑换的卡号数据~', at_sender=True)
        else:
            await bot.send(ev, messgae='兑换成功，但是邮件无法正常发送，请联系管理员处理~', at_sender=True)

# music_db
music_db_dict = {}
music_db_merged_dict = {}
def update_music_db():
    """更新乐曲数据库dict"""
    global music_db_dict, music_db_merged_dict
    # 使用xmltodict读取music_db中的歌曲数据
    with open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\music_db.xml", encoding = 'CP932') as f:
        music_db_dict = xmltodict.parse(f.read())

    with open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\music_db.merged.xml", encoding = 'CP932') as f:
        music_db_merged_dict = xmltodict.parse(f.read())
update_music_db()

# 将全部乐曲的ID、名称、难度、艺术家、更新日期缓存至list
song_name_lst = []
def cache_songname():
    """
    调用此函数可以将全部乐曲的ID、名称、难度、艺术家、更新日期缓存至list
    """
    global song_name_lst
    song_name_lst = []
    for music in music_db_dict['mdb']['music']:
        songname = music['info']['title_name']
        songid = music['@id']
        s_artist = music['info']['artist_name']
        s_update_time = music['info']['distribution_date']['#text']
        s_difficulty_nov = music['difficulty']['novice']['difnum']['#text']
        s_difficulty_adv = music['difficulty']['advanced']['difnum']['#text']
        s_difficulty_ext = music['difficulty']['exhaust']['difnum']['#text']
        s_difficulty_inf = music['difficulty']['infinite']['difnum']['#text']
        if 'maximum' in music['difficulty']:
            s_difficulty_mxm = music['difficulty']['maximum']['difnum']['#text']
        else: s_difficulty_mxm = '-'
        if s_difficulty_nov == '0':
            s_difficulty_nov = '-'
        if s_difficulty_adv == '0':
            s_difficulty_adv = '-'
        if s_difficulty_ext == '0':
            s_difficulty_ext = '-'
        if s_difficulty_inf == '0':
            s_difficulty_inf = '-'
        song_difficulties = [s_difficulty_nov,s_difficulty_adv,s_difficulty_ext,s_difficulty_inf,s_difficulty_mxm]
        song_name_lst.append([songid,songname,song_difficulties,s_artist,s_update_time])
    for music in music_db_merged_dict['mdb']['music']:
        songname = music['info']['title_name']
        songid = music['@id']
        s_artist = music['info']['artist_name']
        s_update_time = music['info']['distribution_date']['#text']
        s_difficulty_nov = music['difficulty']['novice']['difnum']['#text']
        s_difficulty_adv = music['difficulty']['advanced']['difnum']['#text']
        s_difficulty_ext = music['difficulty']['exhaust']['difnum']['#text']
        s_difficulty_inf = music['difficulty']['infinite']['difnum']['#text']
        if 'maximum' in music['difficulty']:
            s_difficulty_mxm = music['difficulty']['maximum']['difnum']['#text']
        else: s_difficulty_mxm = '-'
        if s_difficulty_nov == '0':
            s_difficulty_nov = '-'
        if s_difficulty_adv == '0':
            s_difficulty_adv = '-'
        if s_difficulty_ext == '0':
            s_difficulty_ext = '-'
        if s_difficulty_inf == '0':
            s_difficulty_inf = '-'
        song_difficulties = [s_difficulty_nov,s_difficulty_adv,s_difficulty_ext,s_difficulty_inf,s_difficulty_mxm]
        song_name_lst.append([songid,songname,song_difficulties,s_artist,s_update_time])
cache_songname()

# 刷新缓存功能，新增刷新songlist(?)
@sucmd('/sdvx refresh cache',aliases=('更新SDVX数据'))
async def refresh_cache(session: CommandSession):
    try:
        get_player_list_cache()
        await session.send("已刷新全局玩家缓存")
    except Exception as e:
        await session.send("玩家缓存刷新错误。")
        print(f"玩家缓存刷新错误: {e}")
    try:
        update_music_db()
        cache_songname()
        await session.send("已更新songlist缓存")
    except Exception as e:
        await session.send("乐曲songlist缓存更新错误。")
        print(f"乐曲songlist缓存更新错误: {e}")

def getsonginfo(f_music_id):
    """
    通过乐曲ID返回乐曲名称和难度
    :param f_music_id: 乐曲ID
    :return: [乐曲名,难度,艺术家,更新时间]
    """
    for music in music_db_dict['mdb']['music']:
        if music['@id'] == '%s' % (f_music_id):
            music_name = music['info']['title_name']
            music_difficulty = music['difficulty']
            music_artist = music['info']['artist_name']
            music_update_time = music['info']['distribution_date']['#text']
            return music_name, music_difficulty, music_artist, music_update_time
        else:
            music_name = "无法找到"
    for music in music_db_merged_dict['mdb']['music']:
        if music['@id'] == '%s' % (f_music_id):
            music_name = music['info']['title_name']
            music_difficulty = music['difficulty']
            music_artist = music['info']['artist_name']
            music_update_time = music['info']['distribution_date']['#text']
            return music_name, music_difficulty, music_artist, music_update_time
        else:
            music_name = "无法找到"
    return music_name

def get_grade_fx(f_score):
    """
    通过分数计算GRADE系数
    (S/AAA+/AAA/AA+/AA/A+/A/B/C/D)
    :param f_score: 单曲分数
    :return: GRADE加成系数
    """
    if f_score >= 9900000:
        grade_fx = 1.05
    elif 9900000 > f_score >= 9800000:
        grade_fx = 1.02
    elif 9800000 > f_score >= 9700000:
        grade_fx = 1
    elif 9700000 > f_score >= 9500000:
        grade_fx = 0.97
    elif 9500000 > f_score >= 9300000:
        grade_fx = 0.94
    elif 9300000 > f_score >= 9000000:
        grade_fx = 0.91
    elif 9000000 > f_score >= 8700000:
        grade_fx = 0.88
    elif 8700000 > f_score >= 7500000:
        grade_fx = 0.85
    elif 7500000 > f_score >= 6500000:
        grade_fx = 0.82
    else:
        grade_fx = 0.80
    return grade_fx

def grade_fx_2_name(s_grade_fx):
    """将Grade系数转换为具体Grade评分名称"""
    if s_grade_fx == 1.05:
        s_grade = 'S'
    elif s_grade_fx == 1.02:
        s_grade = 'AAA+'
    elif s_grade_fx == 1:
        s_grade = 'AAA'
    elif s_grade_fx == 0.97:
        s_grade = 'AA+'
    elif s_grade_fx == 0.94:
        s_grade = 'AA'
    elif s_grade_fx == 0.91:
        s_grade = 'A+'
    elif s_grade_fx == 0.88:
        s_grade = 'A'
    elif s_grade_fx == 0.85:
        s_grade = 'B'
    elif s_grade_fx == 0.82:
        s_grade = 'C'
    else:
        s_grade = 'D'
    return s_grade

# TODO:添加ID搜索贴纸、打歌面板、副屏面板、背景音乐的功能,暂定命令修改为 "/sdvxid [类型] [ID]" ,其中类型为song(0)/bgm(1)/screen(2)/panel(3)/sticker(4)
@sv.on_prefix(('/sdvxid','/sdvx id','sdvx搜歌'))
async def id_search_song(bot, ev: CQEvent):
    input_raw = ev.message.extract_plain_text().split() #list
    if len(input_raw) != 2:
        await bot.send(ev, '查询格式错误，使用以下命令格式进行查询：“/sdvxid [类型] [ID]”(类型:0-歌曲,1-主题BGM,2-副屏背景,3-打歌面板,4-表情贴纸)')
        return
    input_type_raw = input_raw[0]
    input_id_raw = input_raw[1]
    # ID找歌
    if input_type_raw == "0":
        try:
            input_id = int(input_id_raw)
            if isinstance(input_id,int):
                song_id = input_id
                song = getsonginfo(song_id)
                song_name = song[0]
                if song != "无法找到":
                    song_diff_nov = song[1]['novice']['difnum']['#text']
                    song_diff_adv = song[1]['advanced']['difnum']['#text']
                    song_diff_ext = song[1]['exhaust']['difnum']['#text']
                    song_diff_inf = song[1]['infinite']['difnum']['#text']
                    if 'maximum' in song[1]:
                        song_diff_mxm = song[1]['maximum']['difnum']['#text']
                    else: song_diff_mxm = 0
                    song_artist = song[2]
                    song_update_time = song[3]
                    try:
                        data = open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\sdvx_jackets\\jk_{input_id_raw.zfill(4)}_1.png", "rb")
                    except:
                        data = open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\meitu.png", "rb")
                    base64_str = base64.b64encode(data.read())
                    jacket =  b'base64://' + base64_str
                    jacket = str(jacket, encoding = "utf-8")  
                    await bot.send(ev, f'[CQ:image,file={jacket}]id.{song_id}\n乐曲名:{song_name}\n艺术家:{song_artist}\n更新日期:{song_update_time}\n{song_diff_nov}/{song_diff_adv}/{song_diff_ext}/{song_diff_inf}/{song_diff_mxm}')
                else:
                    await bot.send(ev, '无法找到ID为此值的曲目')
        except Exception as e:
            await bot.send(ev, '输入错误:%s' %e)
    # ID找BGM
    elif input_type_raw == "1":
        #TODO: 查询bgm
        bgm_name = id_search_bgm(input_id_raw)
        return
    elif input_type_raw == "2":
        #TODO: 查询副屏
        screen_name = id_search_touch(input_id_raw)
        return
    elif input_type_raw == "3":
        #TODO: 查询面板
        panel_name = id_search_panel(input_id_raw)
        return
    elif input_type_raw == "4":
        #TODO: 查询表情
        stamp_name = id_search_stamp(input_id_raw)
        return
    else:
        await bot.send(ev, '查询类型错误，请输入0-4之间的整数。(类型:0-歌曲,1-主题BGM,2-副屏背景,3-打歌面板,4-表情贴纸)')


@sv.on_prefix(('sdvx抽歌','/sdvx rd','SDVX抽歌'))
async def chat_rd_sdvx(bot, ev: CQEvent):
    input_difficulty_raw = ev.message.extract_plain_text().strip()
    # 检查是否输入值
    if len(input_difficulty_raw) == 0:
        songs_total = len(song_name_lst)
        song_rd_num = random.randint(0,songs_total - 1)
        song = song_name_lst[song_rd_num]
        s_id = song[0]
        s_title = song[1]
        s_difficulties = song[2]
        s_artist = song[3]
        s_update_time = song[4]

        try:
            data = open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\sdvx_jackets\\jk_{s_id.zfill(4)}_1.png", "rb")
        except:
            data = open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\meitu.png", "rb")
        base64_str = base64.b64encode(data.read())
        jacket =  b'base64://' + base64_str
        jacket = str(jacket, encoding = "utf-8")  

        s_difficulty_nov = s_difficulties[0]
        s_difficulty_adv = s_difficulties[1]
        s_difficulty_ext = s_difficulties[2]
        s_difficulty_inf = s_difficulties[3]
        s_difficulty_mxm = s_difficulties[4]
    
        await bot.send(ev, f'[CQ:image,file={jacket}]id.{s_id}\n乐曲名:{s_title}\n艺术家:{s_artist}\n更新日期:{s_update_time}\n{s_difficulty_nov}/{s_difficulty_adv}/{s_difficulty_ext}/{s_difficulty_inf}/{s_difficulty_mxm}')
    else:
        try:
            input_difficulty = int(input_difficulty_raw)
            # 将输入字符串转为整数并进入判定流程
            if isinstance(input_difficulty,int) and input_difficulty <= 20 and input_difficulty > 0:
                s_difficulty_nov = 0
                s_difficulty_adv = 0
                s_difficulty_ext = 0
                s_difficulty_inf = 0
                s_difficulty_mxm = 0
                diff_str = str(input_difficulty)
                # 重复抽歌直到抽出对应等级
                while s_difficulty_nov != diff_str and s_difficulty_adv != diff_str and s_difficulty_ext != diff_str and s_difficulty_mxm != diff_str and s_difficulty_inf != diff_str :
                    songs_total = len(song_name_lst)
                    song_rd_num = random.randint(0,songs_total - 1)
                    song = song_name_lst[song_rd_num]
                    s_id = song[0]
                    s_title = song[1]
                    s_difficulties = song[2]
                    s_artist = song[3]
                    s_update_time = song[4]

                    s_difficulty_nov = s_difficulties[0]
                    s_difficulty_adv = s_difficulties[1]
                    s_difficulty_ext = s_difficulties[2]
                    s_difficulty_inf = s_difficulties[3]
                    s_difficulty_mxm = s_difficulties[4]

                try:
                    data = open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\sdvx_jackets\\jk_{s_id.zfill(4)}_1.png", "rb")
                except:
                    data = open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\meitu.png", "rb")
                base64_str = base64.b64encode(data.read())
                jacket =  b'base64://' + base64_str
                jacket = str(jacket, encoding = "utf-8")  
                await bot.send(ev, f'[CQ:image,file={jacket}]id.{s_id}\n乐曲名:{s_title}\n艺术家:{s_artist}\n更新日期:{s_update_time}\n{s_difficulty_nov}/{s_difficulty_adv}/{s_difficulty_ext}/{s_difficulty_inf}/{s_difficulty_mxm}')
            else:
                await bot.send(ev, '输入范围不在正常难易度中')
        except Exception as e:
            print(f"错误:{e}")
            await bot.send(ev, '输入值错误，请输入1~20间的整数')
            traceback.print_exc()

def getplayerplaylog(playerid):
    """
    获取玩家全部最高分记录
    :param playerid: 玩家SDVX ID
    :return: 玩家全曲记录(最高分的一次)
    """
    db_apu = pymysql.connect(
                        host=apu_db.host,
                        port=apu_db.port,
                        user=apu_db.user,
                        password=apu_db.password,
                        database=apu_db.database
                        )
    apu_cursor = db_apu.cursor()
    get_playlog_sql = "SELECT * FROM `d_user_playdata` WHERE `f_id` = '%s'" % (playerid)
    try:
        apu_cursor.execute(get_playlog_sql)
        playlog = apu_cursor.fetchall()
    except Exception as e:
        print(str(e))
    db_apu.close()
    return playlog

def getmusictype(f_music_type:int):
    '''
    获取难度名称
    :param f_music_type: 从数据库获取的原始难度类型
    :return: [[难度缩写],[难度全称]]
    '''
    if f_music_type == 0:
        type_name = 'NOV'
        type_raw = 'novice'
    elif f_music_type == 1:
        type_name = 'ADV'
        type_raw = 'advanced'
    elif f_music_type == 2:
        type_name = 'EXT'
        type_raw = 'exhaust'
    elif f_music_type == 3:
        type_name = 'INF'
        type_raw = 'infinite'
    elif f_music_type == 4:
        type_name = 'MXM'
        type_raw = 'maximum'
    return type_name, type_raw
    
def volforce(single_player_playlog):
    '''
    VF计算函数，输入玩家全部游玩分数记录，计算VF值，返回VF与B50
    :param single_player_playlog: 由 getplayerplaylog 函数返回的全曲最高分
    :return: [vf,[[乐曲ID,单曲vf,乐曲类型,乐曲难度,GRADE系数,通关系数,得分],...]]
    '''
    single_vf_list = []
    # 获取单曲记录并计算单曲VF
    for single_play in single_player_playlog:
        f_music_id = single_play[1]
        f_music_type = single_play[2]
        f_score = int(single_play[3])
        musictypeinfo = getmusictype(f_music_type)
        try:
            music_difnum = int(getsonginfo(f_music_id)[1][f'{musictypeinfo[1]}']['difnum']['#text'])
        except:
            music_difnum = 1
        f_clear_type = single_play[5]
        # 通过分数计算GRADE系数(S/AAA+/AAA/AA+/AA/A+/A/B/C/D)
        grade_fx = get_grade_fx(f_score)
        # 通关类型系数(PUC/UC/EXCESSIVE RATE通关/EFFECTIVE RATE通关/未通关)
        if f_clear_type == '5':
            clearType_fx = 1.1
        elif f_clear_type == '4':
            clearType_fx = 1.05
        elif f_clear_type == '3':
            clearType_fx = 1.02
        elif f_clear_type == '2':
            clearType_fx = 1
        else:
            clearType_fx = 0.5
        # 单曲VF计算公式：Lv x（分数÷1000万）x（GRADE系数）x（通关类型系数）x 2（计算到小数点后一位，去尾）
        single_vf = math.floor(music_difnum * (f_score / 10000000) * grade_fx * clearType_fx * 2 * 10) / 10
        single_vf_list.append([f_music_id,single_vf,f_music_type,music_difnum,grade_fx,clearType_fx,f_score])
    # 降序排序单曲VF并取前五十项计算VF
    single_vf_list.sort(key=takeSecond,reverse=True)
    single_vf_total = 0
    for single_vf_num in single_vf_list[:50]:
        single_vf_total = single_vf_num[1] + single_vf_total
    vf_total = single_vf_total / 100
    return round(vf_total, 3),single_vf_list[:50]

# B50绘图函数，从vf函数返回结果传入包含乐曲id、单曲force、难度类型、lv值、grade、通关类型、分数的b50结果list后
# 使用PIL库制作包含单曲封面，名称、等级、通关类型、grade与单曲Force的图片
@sv.on_prefix(('/sdvx b50','/sdvx vf','vf'))
async def b50_pic(bot, ev: CQEvent):
    # 支持根据输入的SDVX ID查询B50
    input_id_raw = ev.message.extract_plain_text().strip()
    if len(input_id_raw) == 0:
        #从数据库直接获取QQ绑定的对应UID
        db_bot = pymysql.connect(
            host=bot_db.host,
            port=bot_db.port,
            user=bot_db.user,
            password=bot_db.password,
            database=bot_db.database
        )
        apu_cursor = db_bot.cursor()
        qqid = ev.user_id
        apu_getuid_sql = "SELECT QQ,gx_uid FROM grxx WHERE QQ = %s" % (qqid)
        try:
            apu_cursor.execute(apu_getuid_sql)
            result_cx = apu_cursor.fetchall()
            if not result_cx:
                await bot.send(ev, "无法查询到您的数据，请检查是否通过签到功能注册bot功能", at_sender = True)
            elif result_cx[0][1] == None:
                await bot.send(ev, "您还没有绑定您的SDVX ID，请先使用 /sdvx bind 进行绑定", at_sender = True)
            else:
                u_id = result_cx[0][1]
        except:
            await bot.send(ev, "获取SDVXID时出错，请稍后重试")
        db_bot.close()
    elif input_id_raw.isdigit() == True:
        if 0 < int(input_id_raw) < 100000000:
            u_id = int(input_id_raw)
    if len(input_id_raw) == 0 or (input_id_raw.isdigit() == True and 0 < int(input_id_raw) < 100000000):
        u_name = get_player_name(int(u_id))
        vf_func_return = volforce(getplayerplaylog(u_id))
        vf = vf_func_return[0]
        b50 = vf_func_return[1]
        rdid = random.randint(0,2)
        print(rdid)
        with Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\00{rdid}_1.png") as vf_bg:
            NOV_BG = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\NOV.png").resize((253,156))
            ADV_BG = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\ADV.png").resize((253,156))
            EXT_BG = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\EXT.png").resize((253,156))
            INF_BG = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\INF.png").resize((253,156))
            MXM_BG = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\MXM.png").resize((253,156))
            NOINFO_BG = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\NO_INFO.png").resize((253,156))
            MARK_COMP = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\mark_comp.tga").resize((50,44))
            MARK_COMP_EX = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\mark_comp_ex.tga").resize((50,44))
            MARK_UC = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\mark_uc.tga").resize((50,44))
            MARK_PUC = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\mark_puc.tga").resize((50,44))
            MARK_CRASH = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\mark_crash.tga").resize((50,44))
            GRADE_S = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_s.tga").resize((50,44))
            GRADE_AAA_PLUS = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_aaa_plus.tga").resize((50,44))
            GRADE_AAA = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_aaa.tga").resize((50,44))
            GRADE_A = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_a.tga").resize((50,44))
            GRADE_A_PLUS = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_a_plus.tga").resize((50,44))
            GRADE_AA = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_aa.tga").resize((50,44))
            GRADE_AA_PLUS = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_aa_plus.tga").resize((50,44))
            GRADE_B = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_b.tga").resize((50,44))
            GRADE_C = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_c.tga").resize((50,44))
            GRADE_D = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\grade_d.tga").resize((50,44))
            x_pos = 81
            y_pos = 331
            i = 0
            draw = ImageDraw.Draw(vf_bg)
            # 名字
            font_name = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\DIGITAL-REGULAR.TTF", 80)
            draw.text((835,70), f'{u_name}', 'white', font_name, stroke_width=2, stroke_fill='black')
            # VF数值
            font_vf = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\DIGITAL-REGULAR.TTF", 40)
            draw.text((835,170),str(vf),"yellow",font_vf, stroke_width=1, stroke_fill="black")
            # 日期
            nowtime = datetime.datetime.today().isoformat(timespec='seconds')
            draw.text((835,206),str(nowtime),"white",font_vf, stroke_width=1, stroke_fill="black")
            try:
                qq_img = Image.open(BytesIO((await get_usericon(f'{qqid}')).content)).resize((190,190)).convert("RGBA")
            except:
                qq_img = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\meitu.png").resize((190,190)).convert("RGBA")
            vf_bg.paste(qq_img,(574,63),qq_img)
            for single_force in b50:
                s_id = single_force[0] #乐曲ID
                s_name = getsonginfo(s_id)[0] #从id获取乐曲名用于展示
                s_force = single_force[1] #获取单曲VF用于展示
                s_music_type_fx = single_force[2] #获取难度类型(用于判断对应难度封面是否存在，若存在则取该难度封面，否则取1难度封面)
                s_music_type = getmusictype(s_music_type_fx)[0]
                if s_music_type_fx == 0:
                    s_bg = NOV_BG
                elif s_music_type_fx == 1:
                    s_bg = ADV_BG
                elif s_music_type_fx == 2:
                    s_bg = EXT_BG
                elif s_music_type_fx == 3:
                    s_bg = INF_BG
                elif s_music_type_fx == 4:
                    s_bg = MXM_BG
                s_difficulty = single_force[3] #获取难度等级用于展示
                s_grade_fx = single_force[4] #获取得分等级GRADE系数，处理后获得GRADE进行展示
                s_score = single_force[6]
                vf_bg.paste(s_bg,(x_pos,y_pos),s_bg)
                x_diff_title = 24
                y_diff_title = -1
                font_difficulty = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\DIGITAL-REGULAR.TTF", 20)
                draw.text((x_pos + x_diff_title, y_pos + y_diff_title), f'{s_music_type} {s_difficulty}', 'white', font_difficulty)
                try:
                    jackets = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\sdvx_jackets\\jk_{str(s_id).zfill(4)}_{s_music_type_fx}.png").resize((120,120))
                except:
                    try:
                        jackets = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\sdvx_jackets\\jk_{str(s_id).zfill(4)}_1.png").resize((120,120))
                    except:
                        jackets = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\meitu.png").resize((120,120))
                jackets = circle_corner(jackets,15)
                x_jacket = 10
                y_jacket = 26
                vf_bg.paste(jackets,(x_pos+x_jacket,y_pos+y_jacket),jackets)
                s_name_bool = 0
                for single_charter in s_name:
                    if not(single_charter.isascii() or single_charter == "："):
                        s_name_bool = 1
                # 不带日文/中文
                if s_name_bool == 0:
                    font_title = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 18)
                    if len(s_name) < 11:
                        draw.text((x_pos+140, y_pos+30), s_name, 'white', font_title, stroke_width=1, stroke_fill='black')
                    else:
                        font_title = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 16)
                        draw.text((x_pos+140, y_pos+30), s_name[0:10] + "...", 'white', font_title, stroke_width=1, stroke_fill='black')
                else: # 带日文/中文
                    font_title = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 18)
                    if len(s_name) < 6:
                        draw.text((x_pos+140, y_pos+30), s_name, 'white', font_title, stroke_width=1, stroke_fill='black')
                    else:
                        font_title = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 16)
                        draw.text((x_pos+140, y_pos+30), s_name[0:5] + "...", 'white', font_title, stroke_width=1, stroke_fill='black')
                # 乐曲ID
                font_id = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\DIGITAL-REGULAR.TTF", 20)
                draw.text((x_pos+140,y_pos+53), "SDVXID: "+str(s_id), 'white', font_id, stroke_width=1, stroke_fill='black')
                # 得分
                font_score = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\DIGITAL-REGULAR.TTF", 25)
                draw.text((x_pos+140, y_pos+72), str(s_score).zfill(8), 'white', font_score, stroke_width=1, stroke_fill='black')
                # 等级
                if s_grade_fx == 1.05:
                    grade_pic = GRADE_S
                elif s_grade_fx == 1.02:
                    grade_pic = GRADE_AAA_PLUS
                elif s_grade_fx == 1:
                    grade_pic = GRADE_AAA
                elif s_grade_fx == 0.97:
                    grade_pic = GRADE_AA_PLUS
                elif s_grade_fx == 0.94:
                    grade_pic = GRADE_AA
                elif s_grade_fx == 0.91:
                    grade_pic = GRADE_A_PLUS
                elif s_grade_fx == 0.88:
                    grade_pic = GRADE_A
                elif s_grade_fx == 0.85:
                    grade_pic = GRADE_B
                elif s_grade_fx == 0.82:
                    grade_pic = GRADE_C
                else:
                    grade_pic = GRADE_D
                vf_bg.paste(grade_pic,(x_pos+140,y_pos+102),grade_pic)
                # 获取通关类型系数，处理后获得通关类型进行展示
                s_clear_type_fx = single_force[5]
                if s_clear_type_fx == 1.1:
                    mark = MARK_PUC
                elif s_clear_type_fx == 1.05:
                    mark = MARK_UC
                elif s_clear_type_fx == 1.02:
                    mark = MARK_COMP_EX
                elif s_clear_type_fx == 1:
                    mark = MARK_COMP
                else:
                    mark = MARK_CRASH
                x_mark = 195
                vf_bg.paste(mark,(x_pos+x_mark,y_pos+102),mark)
                i+=1
                if i == 5:
                    x_pos = 81
                    y_pos += 166
                    i = 0
                else:
                    x_pos += 260
            vf_bg.save(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\{u_id}.png") # 保存图片
            data = open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\{u_id}.png", "rb")
            base64_str = base64.b64encode(data.read())
            img_b64 =  b'base64://' + base64_str
            img_b64 = str(img_b64, encoding = "utf-8")  
            await bot.send(ev, f'[CQ:image,file={img_b64}]')
    else:
        await bot.send(ev,'输入值错误，请输入八位纯数字的SDVX ID')

@sv.on_prefix(('/sdvx bind'))
async def sdvx_bind(bot, ev: CQEvent):
    get_player_list_cache() # 获取最新的玩家列表至缓存
    await bot.send(ev, '绑定功能已移至WEBUI，请通过WEBUI进行绑定QQ操作。')
    return
    #绑定SDVX ID到QQ上（使用本地数据库）
    input_id_raw = ev.message.extract_plain_text().strip()
    if len(input_id_raw) == 0:
        await bot.send(ev, '请输入您的SDVX ID！')
    elif input_id_raw.isdigit() == True:
        if 0 < int(input_id_raw) < 100000000:
            input_id = int(input_id_raw)
            player_name = get_player_name(input_id)
            if player_name:
                db_bot = pymysql.connect(
                    host=bot_db.host,
                    port=bot_db.port,
                    user=bot_db.user,
                    password=bot_db.password,
                    database=bot_db.database
                )
                apu_cursor = db_bot.cursor()
                qqid = ev.user_id
                apu_getuid_sql = "SELECT QQ,gx_uid FROM grxx WHERE QQ = %s" % (qqid)
                # 先执行一次查询，查询是否已经签到注册过
                try:
                    apu_cursor.execute(apu_getuid_sql)
                    result_cx = apu_cursor.fetchall()
                    apu_bind_sql = "UPDATE `grxx` SET `gx_uid`='%s' WHERE `QQ`='%s'" % (input_id, qqid)
                    if not result_cx:
                        await bot.send(ev, "无法查询到您的数据，请检查是否通过签到功能注册bot功能", at_sender = True)
                    elif result_cx[0][1] == None:
                        # 在此后进行绑定语句编程
                        try:
                            apu_cursor.execute(apu_bind_sql)
                            db_bot.commit()
                            await bot.send(ev, f'已为您绑定成功以下ID:{input_id}')
                        except Exception as e:
                            await bot.send(ev, f'查询过程中发生错误:{e}')
                    else:
                        await bot.send(ev, f'您已经绑定过了，即将为您重新绑定')
                        try:
                            apu_cursor.execute(apu_bind_sql)
                            db_bot.commit()
                            await bot.send(ev, f'已为您绑定成功以下账号:\nSDVX_ID:{input_id}\n昵称:{player_name}')
                        except Exception as e:
                            await bot.send(ev, f'查询过程中发生错误:{e}')
                except Exception as e:
                    await bot.send(ev, f'查询过程中发生错误:{e}')
                db_bot.close()
            else:
                await bot.send(ev, '没有查询到此SDVX_ID对应的玩家，请检查后重新输入')
        else:
            await bot.send(ev, '请输入有效的SDVX_ID范围(0~99999999)')
    else:
        await bot.send(ev, '请输入纯数字的SDVX_ID')

@sv.on_prefix(('/sdvx help'))
async def sdvx_help(bot, ev: CQEvent):
    await bot.send(ev, help_str)

# 搜索用户名对应的SDVXID
@sv.on_prefix(('/sdvx user'))
async def search_usr(bot, ev: CQEvent):
    username = ev.message.extract_plain_text().strip()
    try:
        db_apu = pymysql.connect(
                            host=apu_db.host,
                            port=apu_db.port,
                            user=apu_db.user,
                            password=apu_db.password,
                            database=apu_db.database
                            )
        apu_cursor = db_apu.cursor()
        search_usr_sql = "SELECT * FROM `m_user` WHERE `f_name` LIKE %s ORDER BY `f_play_count` DESC LIMIT 0,10"
        params = ['%' + username + '%']
        apu_cursor.execute(search_usr_sql, params)
        userlist = apu_cursor.fetchall()
        search_result_str = '为您找到以下结果:\n========\n'
        pic_height = 68
        for user in userlist:
            if user[0] == 0:
                break
            search_result_str = search_result_str + f'SDVX ID:{user[0]}\n用户名:{user[3]}\n注册日期:{user[4]}\n游玩次数:{user[1]}\n========\n'
            pic_height += 120
        image = Image.new('RGB', (300, pic_height + 20), (0,0,0)) # 设置画布大小及背景色
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 20)
        # draw.text((10,10), search_result_str, 'white', font)

        # 分行写入，避免换行时每行高度无法确认
        text_list = search_result_str.split('\n')
        for i in range(len(text_list)):
            text = text_list[i]
            draw.text((10, 10 + i * 24), text, 'white', font)

        image.save(nowdir + f'\\hoshino\\modules\\sdvx_helper\\searchusr.jpg') # 保存图片
        data = open(nowdir + f'\\hoshino\\modules\\sdvx_helper\\searchusr.jpg', "rb")
        base64_str = base64.b64encode(data.read())
        img_b64 =  b'base64://' + base64_str
        img_b64 = str(img_b64, encoding = "utf-8")  
        await bot.send(ev, f'[CQ:image,file={img_b64}]')
        # await bot.send(ev, search_result_str)
    except Exception as e:
        print(f'查询过程中发生错误:{e}')
        await bot.send(ev, '查询过程中发生错误')
    db_apu.close()

# 查询最近十次游玩成绩
@sv.on_prefix(('/sdvx rc','/sdvx recent'))
async def recent(bot, ev:CQEvent):
    input_id_raw = ev.message.extract_plain_text().strip()
    if len(input_id_raw) == 0:
        #从数据库直接获取QQ绑定的对应UID
        db_bot = pymysql.connect(
            host=bot_db.host,
            port=bot_db.port,
            user=bot_db.user,
            password=bot_db.password,
            database=bot_db.database
        )
        apu_cursor = db_bot.cursor()
        qqid = ev.user_id
        apu_getuid_sql = "SELECT QQ,gx_uid FROM grxx WHERE QQ = %s" % (qqid)
        try:
            apu_cursor.execute(apu_getuid_sql)
            result_cx = apu_cursor.fetchall()
            if not result_cx:
                await bot.send(ev, "无法查询到您的数据，请检查是否通过签到功能注册bot功能", at_sender = True)
            elif result_cx[0][1] == None:
                await bot.send(ev, "您还没有绑定您的SDVX ID，请先使用 /sdvx bind 进行绑定", at_sender = True)
            else:
                u_id = result_cx[0][1]
        except:
            await bot.send(ev, "获取SDVXID时出错，请稍后重试")
        db_bot.close()
    elif input_id_raw.isdigit() == True:
        if 0 < int(input_id_raw) < 100000000:
            u_id = int(input_id_raw)
    if len(input_id_raw) == 0 or (input_id_raw.isdigit() == True and 0 < int(input_id_raw) < 100000000):
        db_apu = pymysql.connect(
                            host=apu_db.host,
                            port=apu_db.port,
                            user=apu_db.user,
                            password=apu_db.password,
                            database=apu_db.database_6
                            )
        apu_cursor = db_apu.cursor()
        try:
            recent_playlog_sql = "SELECT * FROM `d_all_playdata` WHERE `f_uid` = '%s' ORDER BY `f_updateDtm` DESC LIMIT 0, 10" % (u_id)
            apu_cursor.execute(recent_playlog_sql)
            recent_playlog = apu_cursor.fetchall()
            print(recent_playlog)
            i = 0

            u_name = get_player_name(int(u_id))
            image = Image.new('RGB', (1200, 400), (0,0,0)) # 设置画布大小及背景色
            iwidth, iheight = image.size # 获取画布高宽
            draw = ImageDraw.Draw(image)
            font_main = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 30)
            draw.text((10, 5), f'Player: {u_name}', 'white', font_main)
            font = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 20)
            fontx = 10
            draw.text((fontx, 50), f'[ 难度 | 通关类型 | 评级 | 分数 | 单曲VF ] 乐曲id.乐曲名称（游玩时间）', 'white', font)
            fonty = 80
            for single_play in recent_playlog:
                i += 1
                s_id = single_play[4]
                s_name = getsonginfo(s_id)[0]
                s_score = int(single_play[6])
                s_time = single_play[34]
                s_music_type = int(single_play[5]) #乐曲难度（数值）
                musictypeinfo = getmusictype(s_music_type) #难度由数值转换为具体难度名字[简写,全程]
                s_difficulty = musictypeinfo[0] + ' ' + getsonginfo(s_id)[1][f'{musictypeinfo[1]}']['difnum']['#text'] #难度名 + 具体数难度值
                f_clear_type = single_play[8]

                # 通过分数计算GRADE系数(S/AAA+/AAA/AA+/AA/A+/A/B/C/D)
                grade_fx = get_grade_fx(s_score)
                s_grade_name = grade_fx_2_name(grade_fx)
                music_difnum = int(getsonginfo(s_id)[1][f'{musictypeinfo[1]}']['difnum']['#text'])
                # 通关类型系数(PUC/UC/EXCESSIVE RATE通关/EFFECTIVE RATE通关/未通关)
                if f_clear_type == '5':
                    clearType_fx = 1.1
                    clearType_str = "PUC"
                elif f_clear_type == '4':
                    clearType_fx = 1.05
                    clearType_str = "UC"
                elif f_clear_type == '3':
                    clearType_fx = 1.02
                    clearType_str = "紫灯"
                elif f_clear_type == '2':
                    clearType_fx = 1
                    clearType_str = "绿灯"
                else:
                    clearType_fx = 0.5
                    clearType_str = "Failed"
                # 单曲VF计算公式：Lv x（分数÷1000万）x（GRADE系数）x（通关类型系数）x 2（计算到小数点后一位，去尾）
                single_vf = math.floor(music_difnum * (s_score / 10000000) * grade_fx * clearType_fx * 2 * 5) / 10 
                draw.text((fontx, fonty), f'No.{i}:[ {s_difficulty} | {clearType_str} | {s_grade_name} | {s_score} | {single_vf} ] {s_id}.{s_name} ({s_time})', 'white', font)

                fonty = fonty + 30
            image.save(nowdir + f"\\hoshino\\modules\\sdvx_helper\\sdvx_rcs\\{u_id}.jpg") # 保存图片
            data = open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\sdvx_rcs\\{u_id}.jpg", "rb")
            base64_str = base64.b64encode(data.read())
            img_b64 =  b'base64://' + base64_str
            img_b64 = str(img_b64, encoding = "utf-8")  
            await bot.send(ev, f'[CQ:image,file={img_b64}]')
        except Exception as e:
            print(f'Error:{e}')
            traceback.print_exc()
        db_apu.close()
    else:
        await bot.send(ev,'输入值错误，请输入八位纯数字的SDVX ID')

@sv.on_prefix(("/sdvx set"))
async def set_data(bot, ev: CQEvent):
    type_list = ["BGM","副屏背景","打歌面板","表情贴纸"]
    # 解析命令
    command_parts = ev.message.extract_plain_text().split()
    if not(len(command_parts) == 2 or len(command_parts) == 3):
        await bot.send(ev, "请根据正确的格式输入命令。")
        return
    try:
        type_parem = int(command_parts[0])
        if type_parem == 4:
            type_parem = int(command_parts[1]) + 3
            type_str = "贴纸表情"
            id_parem = int(command_parts[2])
        elif type_parem <= 3 and type_parem >= 1:
            id_parem = int(command_parts[1])
            type_str = type_list[type_parem-1]
        else:
            await bot.send(ev, "输入类型值错误，请输入1-4之间的整数。(类型:1-BGM,2-副屏背景,3-打歌面板,4-表情贴纸)")
            return
    except ValueError:
        await bot.send(ev, "ID必须为整数，请输入正确的命令。")
        return
    except IndexError:
        await bot.send(ev, "请根据正确的格式输入命令。")
        return
    if type_parem == 1:
        name = id_search_bgm(id_parem)
    elif type_parem == 2:
        name = id_search_touch(id_parem)
    elif type_parem == 3:
        name = id_search_panel(id_parem)
    elif type_str == "贴纸表情":
        name = id_search_stamp(id_parem)
    if name == None:
        # TODO: 添加对默认ID(0)的支持
        await bot.send(ev, f"无法找到对应ID的 {type_str}，请检查输入ID是否存在")
        return
    #从数据库直接获取QQ绑定的对应UID
    db_bot = pymysql.connect(
        host=bot_db.host,
        port=bot_db.port,
        user=bot_db.user,
        password=bot_db.password,
        database=bot_db.database
    )
    apu_cursor = db_bot.cursor()
    qqid = ev.user_id
    apu_getuid_sql = "SELECT QQ,gx_uid FROM grxx WHERE QQ = %s" % (qqid)
    try:
        apu_cursor.execute(apu_getuid_sql)
        result_cx = apu_cursor.fetchall()
        if not result_cx:
            await bot.send(ev, "无法查询到您的数据，请检查是否通过签到功能注册bot功能", at_sender = True)
            db_bot.close()
            return
        elif result_cx[0][1] == None:
            await bot.send(ev, "您还没有绑定您的SDVX ID，请先使用 /sdvx bind 进行绑定", at_sender = True)
            db_bot.close()
            return
        else:
            f_id = result_cx[0][1]
    except:
        await bot.send(ev, "获取SDVXID时出错，请稍后重试")
        db_bot.close()
        traceback.print_exc()
        return
    db_bot.close()
    # 更新数据列表
    db_apu = pymysql.connect(
                        host=apu_db.host,
                        port=apu_db.port,
                        user=apu_db.user,
                        password=apu_db.password,
                        database=apu_db.database_6
                        )
    apu_cursor = db_apu.cursor()
    try:
        get_parems_setting_sql = f"SELECT f_param FROM `d_user_params` WHERE `f_id` = '{f_id}' AND `f_param_id` = '2' AND `f_param_type` = '2' LIMIT 0, 1000"
        apu_cursor.execute(get_parems_setting_sql)
        data_list_raw = apu_cursor.fetchall()
        if not data_list_raw:
            await bot.send(ev, "未查询到玩家配置项，正在进行玩家设置初始化。")
            player_name = get_player_name(f_id)
            if player_name:
                await bot.send(ev, f"正在为玩家 {player_name} 执行初始化过程...")
                insert_parems_setting_sql = f"INSERT INTO `d_user_params` (`f_id`, `f_param_id`, `f_param_type`, `f_param`) VALUES ('{f_id}', '2', '2', '0')"
                apu_cursor.execute(insert_parems_setting_sql)
                db_apu.commit()
                await bot.send(ev, "初始化完成，即将进行参数设置...")
                data_list = "0 0 0 0 0 0 0 0 0 0 0"
            else:
                await bot.send(ev, "您所绑定的 SDVX ID 为空号，请重新绑定或联系管理员处理", at_sender = True)
                db_apu.close()
                return
        else:
            data_list = data_list_raw[0][0]
        if data_list == "0":
            data_list = "0 0 0 0 0 0 0 0 0 0 0"
        data_parts = data_list.split()
        data_parts[type_parem-1] = str(id_parem)
        data_list = " ".join(data_parts)
        update_params_sql = f"UPDATE `d_user_params` SET `f_param`='{data_list}' WHERE (`f_id`='{f_id}') AND (`f_param_id`='2') AND (`f_param_type`='2')"
        apu_cursor.execute(update_params_sql)
        db_apu.commit()
        # 输出更新后的数据
        if type_str == "贴纸表情":
            await bot.send(ev, f"已经成功将您位置在 {type_parem-3} 的表情贴纸设置为 {name}", at_sender = True)
        else:
            await bot.send(ev, f"已经成功将您的 {type_str} 设置为 {name}", at_sender = True)
    except Exception as e:
        db_apu.rollback()
        print(f"Error：{e}")
        await bot.send(ev, "设置失败，请联系管理员查询解决方案。")
        traceback.print_exc()
    db_apu.close()

# 名称模糊搜索曲名
def fuzzy_search(query, choices, threshold=50):
    """
    使用FuzzyWuzzy库中的“fuzz.token_set_ratio”算法比较查询字符串和选择字符串，
    并返回所有匹配相似度阈值的字符串列表。
    :param query: 需要查询的字符串
    :param choices: 字符串列表(乐曲列表)
    :param threshold: 阈值
    :return: 相似的乐曲名列表
    """
    results = []
    for string in choices:
        ratio = fuzz.token_set_ratio(query, string[1])
        if ratio >= threshold:
            results.append((string, ratio))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[0:10]


@sv.on_prefix(('/sdvx search'))
async def search_usr(bot, ev: CQEvent):
    inputname = ev.message.extract_plain_text().strip()
    result = fuzzy_search(inputname, song_name_lst)
    str_slst = ""
    for song in result:
        s_id = song[0][0]
        s_name = song[0][1]
        str_slst += f"<{s_id}> {s_name}\n"
    await bot.send(ev, f"{str_slst}")

@sv.on_prefix(('/sdvx daisuki','/sdvx dsk'))
async def favourite_songs(bot, ev:CQEvent):
    '''最喜欢的10首乐曲(游玩次数最多的乐曲)'''
    # 支持根据输入的SDVX ID查询B50
    input_id_raw = ev.message.extract_plain_text().strip()
    if len(input_id_raw) == 0:
        #从数据库直接获取QQ绑定的对应UID
        db_bot = pymysql.connect(
            host=bot_db.host,
            port=bot_db.port,
            user=bot_db.user,
            password=bot_db.password,
            database=bot_db.database
        )
        apu_cursor = db_bot.cursor()
        qqid = ev.user_id
        apu_getuid_sql = "SELECT QQ,gx_uid FROM grxx WHERE QQ = %s" % (qqid)
        try:
            apu_cursor.execute(apu_getuid_sql)
            result_cx = apu_cursor.fetchall()
            if not result_cx:
                await bot.send(ev, "无法查询到您的数据，请检查是否通过签到功能注册bot功能", at_sender = True)
            elif result_cx[0][1] == None:
                await bot.send(ev, "您还没有绑定您的SDVX ID，请先使用 /sdvx bind 进行绑定", at_sender = True)
            else:
                u_id = result_cx[0][1]
        except:
            await bot.send(ev, "获取SDVXID时出错，请稍后重试")
        db_bot.close()
    elif input_id_raw.isdigit() == True:
        if 0 < int(input_id_raw) < 100000000:
            u_id = int(input_id_raw)
    if len(input_id_raw) == 0 or (input_id_raw.isdigit() == True and 0 < int(input_id_raw) < 100000000):
        u_name = get_player_name(int(u_id))
        playlog = list(getplayerplaylog(u_id))
        def takeCount(elem):
            return elem[7]
        playlog.sort(key = takeCount, reverse = True)
        image = Image.new('RGB', (1920, 1080), (33,33,33)) # 设置画布大小及背景色
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 72)
        font_count = ImageFont.truetype(nowdir + f"\\hoshino\\modules\\sdvx_helper\\NotoSansSC-Regular.otf", 20)
        draw.text((816, 74), f'个人最爱', 'white', font)
        i = 0
        x_pos = 70
        y_pos = 240
        for single in playlog[:10]:
            if i == 5:
                i = 0
                y_pos = 660
            x_jacket = 370 * i
            s_id = single[1]
            s_music_type = single[2]
            s_music_type_fx = getmusictype(s_music_type)
            s_info = getsonginfo(s_id)
            s_name = s_info[0]
            s_difficulty = s_info[1]
            s_play_count = single[7]
            # TODO:优化排版，并完善上面的参数
            # draw.text((x_pos+x_jacket+65, y_pos-30), f'游玩次数: {s_play_count} 次', 'white', font_count)
            try:
                jackets = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\sdvx_jackets\\jk_{str(s_id).zfill(4)}_{s_music_type_fx}.png").resize((300,300))
            except:
                try:
                    jackets = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\sdvx_jackets\\jk_{str(s_id).zfill(4)}_1.png").resize((300,300))
                except:
                    jackets = Image.open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\pics\\meitu.png").resize((300,300))
            jackets = circle_corner(jackets,30)
            image.paste(jackets,(x_pos+x_jacket,y_pos),jackets)
            i += 1
        buf = BytesIO()
        image.save(buf, format='PNG')
        base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}' #通过BytesIO发送图片，无需生成本地文件
        await bot.send(ev,f'[CQ:image,file={base64_str}]',at_sender = True)
    else:
        await bot.send(ev,'输入值错误，请输入八位纯数字的SDVX ID')