import requests
from PIL import Image, ImageDraw
from decimal import Decimal,ROUND_HALF_UP
from .config import mail_cfg
from email.mime.text import MIMEText
from email.utils import formataddr
import smtplib
import traceback
from fuzzywuzzy import fuzz

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