import os
import csv

nowdir = os.getcwd()

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

def id_search_theme(parem_id):
    """
    id找主题名称，返回值为名称
    """
    parem_id = str(parem_id)
    # 打开csv文件
    with open(nowdir + f"\\hoshino\\modules\\sdvx_helper\\theme.csv", "r", encoding="utf-8") as f:
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