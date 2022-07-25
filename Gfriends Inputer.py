# -*- coding:utf-8 -*-
# Gfriends Inputer / 女友头像仓库导入工具
# Licensed under the MIT license.
# Designed by xinxin8816, many thanks for junerain123, ddd354, moyy996.
version = 'v3.0.0'

import requests, os, io, sys, time, re, threading, argparse
from alive_progress import alive_bar
from configparser import RawConfigParser
from traceback import format_exc
from hashlib import md5
from cv2dnn import find_faces
from base64 import b64encode
from json import loads
from PIL import Image, ImageFilter
from aip import AipBodyAnalysis

def fix_size(type, path):
    try:
        pic = Image.open(path)
        if pic.mode != "RGB": pic = pic.convert('RGB')  # 有些图片有P通道，base64编码后会出问题
        (wf, hf) = pic.size
        if not 2 / 3 - 0.02 <= wf / hf <= 2 / 3 + 0.02:  # 仅处理会过度拉伸的图片
            if type == '1':
                fixed_pic = pic.resize((int(wf), int(3 / 2 * wf)))  # 拉伸图片
                fixed_pic = fixed_pic.filter(ImageFilter.GaussianBlur(radius=50))  # 高斯平滑滤镜
                fixed_pic.paste(pic, (0, int((3 / 2 * wf - hf) / 2)))  # 粘贴原图
                fixed_pic.save(path, quality=95)
            elif type == '2':
                fixed_pic = pic.crop((int(wf / 2 - 1 / 3 * hf), 0, int(wf / 2 + 1 / 3 * hf), int(hf)))  # 像素中线向两边扩展
                fixed_pic.save(path, quality=95)
            elif type == '3' or type == '4':
                try:
                    if type == '3':
                        x_nose, y_nose = find_faces(path)  # 传递二进制RGB图像，返回鼻子横、纵坐标
                    else:
                        with open(path, 'rb') as fp:
                            x_nose = int(BD_AI_client.bodyAnalysis(fp.read())["person_info"][0]['body_parts']['nose']['x'])  # 返回鼻子横坐标
                        if BD_VIP == '否':
                            time.sleep(0.2)  # 免费用户QPS≈2，排除网络延迟及性能损耗时间，此值可以稍降低
                        else:
                            time.sleep(1 / int(1.1 * BD_VIP))
                    if x_nose + 1 / 3 * hf > wf:  # 判断鼻子在图整体的位置
                        x_left = wf - 2 / 3 * hf  # 以右为边
                    elif x_nose - 1 / 3 * hf < 0:
                        x_left = 0  # 以左为边
                    else:
                        x_left = x_nose - 1 / 3 * hf  # 以鼻子为中线向两边扩展
                    fixed_pic = pic.crop((x_left, 0, x_left + 2 / 3 * hf, hf))
                    fixed_pic.save(path, quality=95)
                except KeyboardInterrupt:
                    sys.exit()
                except:
                    print('!! ' + path + ' AI 分析失败，跳过 AI 直接裁剪')
                    fix_size('2', path)
            else:
                print('× 头像处理功能配置错误，没有此选项：' + str(type))
                sys.exit()
        return True
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
    except:
        if 'pic' in vars(): del pic  # 如果图片已打开，则关闭
        if 'fixed_pic' in vars(): del fixed_pic
        print('!! ' + path + ' 可能已损坏，跳过。')

        # 创建一个 Failed 文件夹并把失败头像移动进去
        failed_dir = re.sub(r'(.*/)(.*)', r'\1Failed/', path)
        failed_path = re.sub(r'(.*/)(.*)', r'\1Failed/\2', path)
        if not os.path.exists(failed_dir): os.makedirs(failed_dir)
        if os.path.exists(failed_path): os.remove(failed_path)
        os.rename(path, failed_path)
        return False


def get_gfriends_map(repository_url):
    rewriteable_word('>> 连接 Gfriends 女友头像仓库...')

    # 定义变量
    if repository_url == '默认/': repository_url = 'https://raw.githubusercontent.com/gfriends/gfriends/master/'
    gfriends_template = repository_url + '{}/{}/{}'
    filetree_url = repository_url + 'Filetree.json'

    # 检查文件树缓存
    keep_tree = False
    if os.path.exists('./Getter/Filetree.json'):
        # 加 deflate 请求以防压缩无法获取真实大小
        gfriends_response = session.head(filetree_url, proxies=proxies, timeout=1, headers={'Accept-Encoding':'deflate'})
        if os.path.getsize('./Getter/Filetree.json') == int(gfriends_response.headers['Content-Length']):
            keep_tree = True

    if keep_tree:
        with open('./Getter/Filetree.json', 'r', encoding='utf-8') as json_file:
            if aifix:
                map_json = loads(json_file.read())
            else:
                map_json = loads(json_file.read().replace('AI-Fix-', ''))
        print('√ 使用 Gfriends 女友头像仓库缓存')
    else:
        try:
            response = session.get(filetree_url, proxies=proxies, timeout=15)
            # 修复部分服务端返回 header 未指明编码使后续解析错误
            response.encoding = 'utf-8'
        except requests.exceptions.RequestException:
            print('× 连接 Gfriends 女友头像仓库超时，请检查网络连接\n')
            sys.exit()
        except:
            if debug: print(format_exc())
            print('× 网络连接异常且重试 ' + str(max_retries) + ' 次失败')
            print('× 请尝试开启全局代理或配置 HTTP 局部代理；若已开启代理，请检查其可用性')
            sys.exit()
        if response.status_code == 429:
            print('× 女友仓库返回了一个错误：429 请求过于频繁，请稍后再试')
            sys.exit()
        elif response.status_code != 200:
            print('× 女友仓库返回了一个错误：' + str(response.status_code))
            sys.exit()

        # 应用 AI 修复
        if aifix:
            map_json = loads(response.text)
        else:
            map_json = loads(response.text.replace('AI-Fix-', ''))

        # 写入文件树缓存
        with open('./Getter/Filetree.json', "wb") as json_file:
            json_file.write(response.content)
        print('√ 连接 Gfriends 女友头像仓库成功')

    # 生成下载地址字典
    output = {}
    for second in map_json['Content'].keys():
        for k, v in map_json['Content'][second].items():
            output[k[:-4]] = gfriends_template.format('Content', second, v)
    print('   库存头像：' + str(map_json['Information']['TotalNum']) + '枚\n')
    return output


def asyncc(f):
    def wrapper(*args, **kwargs):
        thr = threading.Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper


@asyncc
def check_avatar(url, actor_name, proc_md5):
    try:
        if actor_name in exist_list:  # 没有头像的演员跳过检测
            actor_md5 = md5(actor_name.encode('UTF-8')).hexdigest()[12:-12]
            if actor_md5 in inputed_dict:  # 没有下载过的演员跳过检测
                gfriends_response = session.head(url, proxies=proxies, timeout=1)
                if inputed_dict[actor_md5] == gfriends_response.headers['Content-Length']:
                    del link_dict[actor_name]
        # else:
        # inputed_dict[actor_md5] = gfriends_response.headers['Content-Length']
        # else: # 有头像的演员先不保存日志，避免二次请求
        # inputed_dict[actor_md5] = gfriends_response.headers['Content-Length']
        proc_log.write(proc_md5 + '\n')
    except requests.exceptions.ConnectTimeout:
        print('!! ' + actor_name + ' 头像更新检查超时，可能是网络不稳定。')
    except:
        print('!! ' + actor_name + ' 头像更新检查失败。')


@asyncc
def download_avatar(url, actor_name, proc_md5):
    gfriends_response = session.get(url, proxies=proxies)
    pic_path = download_path + actor_name + ".jpg"
    if gfriends_response.status_code == 429:
        print('!! ' + pic_path + ' 下载失败，女友仓库返回：429 请求过快，请稍后再试')
        return False
    try:
        Image.open(io.BytesIO(gfriends_response.content)).verify()  # 校验下载的图片
    except:
        print('!! ' + pic_path + ' 校验失败，可能下载的头像不完整。')
    with open(pic_path, "wb") as code:
        code.write(gfriends_response.content)
    actor_md5 = md5(actor_name.encode('UTF-8')).hexdigest()[12:-12]
    inputed_dict[actor_md5] = gfriends_response.headers['Content-Length']  # 写入图片版本日志
    proc_log.write(proc_md5 + '\n')


@asyncc
def input_avatar(url, data):
    try:
        session.post(url, data=data, headers={"Content-Type": 'image/jpeg',
                                                  "User-Agent": 'Gfriends_Inputer/' + version.replace('v', '')},
                         proxies=proxies)
    except:
        print('!! ' + url.replace(host_url, '').replace(api_key, '***') + ' 导入失败，可能是与媒体服务器连接不稳定，请尝试降低导入线程数。')


@asyncc
def del_avatar(url_post_img):
    session.delete(url=url_post_img, proxies=proxies)


def get_gfriends_link(name):
    if name in gfriends_map:
        output = gfriends_map[name]
        return output
    else:
        return None


def argparse_function(ver: str) -> [str, str, bool]:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default='config.ini', nargs='?', help="The config file Path.")
    parser.add_argument("-q", "--quiet", dest='quietflag', action="store_true",
                        help="Assume Yes on all queries and Print logs to file.")
    parser.add_argument("-v", "--version", action="version", version=ver)
    args = parser.parse_args()
    return args.config, args.quietflag


def read_config(config_file):
    global config_settings
    rewriteable_word('>> 读取配置...')
    if os.path.exists(config_file):
        config_settings = RawConfigParser()
        try:
            config_settings.read('config.ini', encoding='UTF-8-SIG')  # UTF-8-SIG 适配 Windows 记事本
            repository_url = config_settings.get("下载设置", "Repository_Url")
            host_url = config_settings.get("媒体服务器", "Host_Url")
            api_key = config_settings.get("媒体服务器", "Host_API")
            max_download_connect = config_settings.getint("下载设置", "MAX_DL")
            max_retries = config_settings.getint("下载设置", "MAX_Retry")
            Proxy = config_settings.get("下载设置", "Proxy")
            download_path = config_settings.get("下载设置", "Download_Path")
            max_upload_connect = config_settings.getint("导入设置", "MAX_UL")
            local_path = config_settings.get("导入设置", "Local_Path")
            BD_App_ID = config_settings.get("导入设置", "BD_App_ID")
            BD_API_Key = config_settings.get("导入设置", "BD_API_Key")
            BD_Secret_Key = config_settings.get("导入设置", "BD_Secret_Key")
            BD_VIP = config_settings.get("导入设置", "BD_VIP")
            overwrite = config_settings.get("导入设置", "OverWrite")
            aifix = True if config_settings.get("下载设置", "AI_Fix") == '是' else False
            debug = True if config_settings.get("调试功能", "DeBug") == '是' else False
            deleteall = True if config_settings.get("调试功能", "DEL_ALL") == '是' else False
            fixsize = config_settings.get("导入设置", "Size_Fix")
            '''
            # 弃用代理选项
            if Proxy_Range not in ['ALL', 'REPO', 'HOST', 'NO']:
                print('!! 局部代理范围 Proxy_Range 填写错误，自动关闭局部代理')
                Proxy_Range = 'NO'
                time.sleep(3)
            if '127.0.0.1' in host_url or 'localhost' in host_url or '192.168' in host_url:
                if Proxy_Range == 'ALL':
                    print('>> 媒体服务器位于局域网或本地，自动仅代理女友仓库')
                    Proxy_Range = 'REPO'
                if Proxy_Range == 'HOST':
                    print('>> 媒体服务器位于局域网或本地，自动关闭局部代理')
                    Proxy_Range = 'NO'
                time.sleep(1)
            
            # 修正旧版覆盖选项
            if overwrite == '是' or overwrite == '否':
                with open("config.ini", encoding = 'UTF-8-SIG') as file:
                    content = file.read()
                if '### 覆盖已有头像 ###' in content:
                    print('!! 发现旧版本的配置文件。\n   自动将 “头像导入方式” 选项升级为 2 - 增量更新（头像有更新时覆盖） ', end = '')
                    time.sleep(5)
                    content = re.sub(r'OverWrite.*\n','OverWrite = 2\n',content,re.M)
                    content = content.replace('### 覆盖已有头像 ###','### 头像导入方式 ###\n# 0 - 不覆盖\n# 1 - 全部覆盖\n# 2 - 头像有更新时覆盖')
                    os.remove("config.ini")
                    write_txt("config.ini", '### Gfriends Inputer 配置文件 ###\n\n' + content + '\n\n### 配置文件版本号，请勿修改 ###\nVersion = '+ version)
                    overwrite == '2'
                    print('ok')
                else:
                    print('!! 发现旧版本的配置文件，且无法自动升级。\n')
                    sys.exit()
            '''
            # 修正用户的URL
            if not host_url.endswith('/'): host_url += '/'
            if not repository_url.endswith('/'): repository_url += '/'
            # 创建文件夹
            if not os.path.exists('./Getter/'):
                os.makedirs('./Getter/')
                write_txt("./Getter/README.txt", '本目录自动生成，用于存放下载记录及导入日志等文件。')
            if not os.path.exists(download_path):
                os.makedirs(download_path)
                write_txt(download_path + "/README.txt", '本目录自动生成，用于存放从仓库下载和处理过的头像。')
            if not os.path.exists(local_path):
                os.makedirs(local_path)
                write_txt(local_path + "/README.txt",
                          '本目录自动生成，您可以存放自己收集的头像，这些头像将被优先导入服务器。\n\n请自行备份您收集头像的副本，根据个人配置不同，该目录文件可能会被程序修改。\n\n仅支持JPG格式，且请勿再创建子目录。\n\n如果您收集的头像位于子目录，可通过 Move To Here.bat（Only for Windows） 工具将其全部提取到根目录。')
                write_txt(local_path + "/Move To Here.bat",
                          '@echo off\necho This tool will help you move all files which in the subdirectory to this root directory\npause\nfor /f "delims=" %%a in ("dir /a-d /b /s ") do (\nmove "%%~a" ./ 2>nul\n)\n')
            # 定义百度AI
            if fixsize == '3':
                BD_AI_client = AipBodyAnalysis(BD_App_ID, BD_API_Key, BD_Secret_Key)
            else:
                BD_AI_client = None
            return (
            repository_url, host_url, api_key, overwrite, fixsize, max_retries, Proxy, aifix, debug,
            deleteall, download_path, local_path, max_download_connect, max_upload_connect, BD_AI_client, BD_VIP)
        except:
            print(format_exc())
            print('× 无法读取 config.ini。如果这是旧版本的配置文件，请删除后重试。\n')
            if WINOS: print('按任意键退出程序...'); os.system('pause>nul')
            sys.exit()
    else:
        content = '''### Gfriends Inputer 配置文件 ###

[媒体服务器]
### Emby / Jellyfin 服务器地址 ###
Host_Url = http://localhost:8096/
	
### Emby / Jellyfin API 密钥 ###
Host_API = 

[下载设置]
### 下载文件夹 ###
Download_Path = ./Downloads/

### 下载线程数 ###
# 若网络不稳定、丢包率或延迟较高，可适当减小下载线程数
MAX_DL = 5

### 下载失败重试数 ###
# 若网络不稳定、丢包率或延迟较高，可适当增加失败重试数
MAX_Retry = 3

### 女友头像仓库源 ###
# "默认"使用官方主仓库（已禁止浏览器访问）：https://raw.githubusercontent.com/gfriends/gfriends/master/
# 获取更多官方备用镜像，详见项目首页
Repository_Url = 默认

### AI 优化（仅支持官方仓库）###
# 在不可避免下载低质量头像时，自动挑选经 AI 算法放大优化的副本，质量更高但更占空间
AI_Fix = 是

### 多头像下载方式 ###
# 仓库内可能存储了一位女友的多张头像，遇到这种情况默认选择最优的一张。或者您也可以让程序把对应头像全部下载，并在导入前提醒您手动挑选。
# 0 - 自动优选
# 1 - 手动挑选（当有大量头像需要导入时，谨慎选择）

### HTTP / Socks 局部代理 ###
# 推荐开启全局代理而不是使用此局部代理
# 代理地址，格式如下
# HTTP 代理格式为 http://IP:端口 , 如 http://localhost:7890
# Socks 代理格式为 socks+协议版本://IP:端口 , 如 socks5h://localhost:7890
Proxy = 

[导入设置]
### 本地头像文件夹 ###
# 将第三方头像包或自己收集的头像移动至该目录，可优先于仓库导入服务器。仅支持非子目录下的 jpg 格式。
Local_Path = ./Avatar/

### 头像导入方式（仅支持官方仓库） ###
# 0 - 不覆盖
# 1 - 全部覆盖
# 2 - 增量导入（头像有更新时再覆盖）
OverWrite = 2

### 导入线程数 ###
# 导入至本地或内网服务器时，网络稳定可适当增大导入线程数（推荐：20-100）
# 导入至远程服务器时，可适当减小导入线程数（推荐：5-20）
MAX_UL = 20

### 头像尺寸优化 ###
# 避免媒体服务器拉伸比例不符合 2:3 的头像
# 0 - 不处理直接导入
# 1 - 高斯平滑处理（填充毛玻璃样式）
# 2 - 直接裁剪处理（可能会裁剪到演员面部）
# 3 - 本地 AI 检测并裁剪处理（默认，速度取决于设备性能）
# 4 - 云端 AI 检测并裁剪处理（需配置百度人体定位 AI）
Size_Fix = 3

### 百度人体定位 AI ###
# 具体使用说明请参阅仓库项目 README
# 免费个人用户 QPS=2 处理速度慢。付费个人用户和企业用户请修改 BD_VIP 为您购买的 QPS 额度值，免费个人用户修改后会报错。
BD_VIP = 否
BD_App_ID = 
BD_API_Key = 
BD_Secret_Key = 

[调试功能]
### 删除所有头像 ###
# 删除媒体服务器中所有演员的头像
DEL_ALL = 否

### 输出详尽错误 ###
DeBug = 否

### 配置文件版本 ###
Version = '''
        write_txt("config.ini", content + version)
        print('× 没有找到 config.ini。已为阁下生成，请修改配置后重新运行程序。\n')
        if WINOS: print('按任意键退出程序...');    os.system('pause>nul')
        sys.exit()


def read_persons(host_url, api_key, emby_flag):
    rewriteable_word('>> 连接 Emby / Jellyfin 服务器...')
    if emby_flag:
        host_url_persons = host_url + 'emby/Persons?api_key=' + api_key  # &PersonTypes=Actor
    else:
        host_url_persons = host_url + 'jellyfin/Persons?api_key=' + api_key  # &PersonTypes=Actor
    try:
        rqs_emby = session.get(url=host_url_persons,
                                   headers={"User-Agent": 'Gfriends_Inputer/' + version.replace('v', '')},
                                   proxies=proxies, timeout=5)
    except requests.exceptions.ConnectionError:
        print('× 连接 Emby / Jellyfin 服务器失败，请检查地址是否正确：', host_url, '\n')
        sys.exit()
    except requests.exceptions.RequestException:
        print('× 连接 Emby / Jellyfin 服务器超时，请检查地址是否正确：', host_url, '\n')
        sys.exit()
    except:
        if debug: print(format_exc())
        print('× 连接 Emby / Jellyfin 服务器未知错误：', host_url, '\n')
        sys.exit()
    if rqs_emby.status_code == 401:
        print('× 无权访问 Emby / Jellyfin 服务器，请检查 API 密匙是否正确\n')
        sys.exit()
    if rqs_emby.status_code == 404 and emby_flag:
        rewriteable_word('>> 可能是新版 Jellyfin，尝试重新连接...')
        return read_persons(host_url, api_key, False)
    elif rqs_emby.status_code == 404 and not emby_flag:
        print('× 尝试读取 Emby / Jellyfin 演员列表但是未找到，可能是未适配的版本：', host_url, '\n')
        sys.exit()
    if rqs_emby.status_code != 200:
        print('× 连接 Emby / Jellyfin 服务器成功，但是服务器内部错误：' + str(rqs_emby.status_code))
        sys.exit()
    # if 'json' not in rqs_emby.headers['Content-Type']: # 群辉返回的类型是 text/html？
    # print('× 连接 Emby / Jellyfin 服务器成功，但是服务器的演员列表不能识别：' + rqs_emby.headers['Content-Type'])
    # sys.exit()
    try:
        output = sorted(loads(rqs_emby.text)['Items'], key=lambda x: x['Name'])  # 按姓名排序
        print('√ 连接 Emby / Jellyfin 服务器成功')
        print('   演职人员：' + str(len(output)) + '人\n')
        return output, emby_flag
    except:
        print('× 连接 Emby / Jellyfin 服务器成功，但是服务器的演员列表不能识别：' + rqs_emby.headers['Content-Type'])
        sys.exit()


def write_txt(filename, content):
    txt = open(filename, 'a', encoding="utf-8")
    txt.write(content)
    txt.close()


def rewriteable_word(word):
    for t in ['', word]: sys.stdout.write('\033[K' + t + '\r')


def del_all():
    print('【调试模式】删除所有头像\n')
    (list_persons, emby_flag) = read_persons(host_url, api_key, True)
    rewriteable_word('按任意键开始...')
    os.system('pause>nul') if WINOS else input('Press Enter to start...')
    with alive_bar(len(list_persons), enrich_print=False, dual_line=True) as bar:
        for dic_each_actor in list_persons:
            bar.text('正在删除：'+dic_each_actor['Name'])
            bar()
            if dic_each_actor['ImageTags']:
                if emby_flag:
                    url_post_img = host_url + 'emby/Items/' + dic_each_actor[
                        'Id'] + '/Images/Primary?api_key=' + api_key
                else:
                    url_post_img = host_url + 'jellyfin/Items/' + dic_each_actor[
                        'Id'] + '/Images/Primary?api_key=' + api_key
                del_avatar(url_post_img)
                while True:
                    if not threading.activeCount() > max_upload_connect + 1: break
    rewriteable_word('>> 即将完成')
    for thr_status in threading.enumerate():
        try:
            thr_status.join()
        except RuntimeError:
            continue
    print('√ 删除完成')
    if WINOS: print('按任意键退出程序...'); os.system('pause>nul')
    sys.exit()

@asyncc
def get_ip():
    global public_ip
    try:
        response = session.get('https://api.myip.la/cn?json', proxies=proxies)
        ip_country_code = loads(response.text)['location']['country_code']
        ip_country_name = loads(response.text)['location']['country_name']
        ip_city = loads(response.text)['location']['province']
        if ip_country_name == ip_city:
            public_ip = '[' + ip_country_code + ']' + ip_country_name
        else:
            public_ip = '[' + ip_country_code + ']' + ip_country_name + ip_city
    except:
        pass


def check_update():
    rewriteable_word('>> 检查更新...')
    try:
        get_ip()
        response = session.get('https://api.github.com/repos/gfriends/gfriends-inputer/releases', proxies=proxies,
                                   timeout=3)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            print('× 检查更新失败！返回了一个错误： {}\n'.format(response.status_code))
            rewriteable_word('按任意键跳过...')
            os.system('pause>nul') if WINOS else input('Press Enter to skip...')

        # version process
        # `v2.94` > `2.94`
        # `v3.0.0` > `3.0.0` > `0.0.3` > `00.3` > `3.00`
        local_ver = version.replace('v', '')[::-1].replace('.','',1)[::-1]
        remote_ver = loads(response.text)[0]['tag_name'].replace('v', '')
        if remote_ver.count('.') > 1:
            remote_ver = remote_ver[::-1].replace('.', '', 1)[::-1]

        if float(local_ver) < float(remote_ver):
            print(loads(response.text)[0]['name'] + ' 发布啦！\n')
            print(loads(response.text)[0]['body'])
            print('了解详情：https://git.io/JL0tk')
            print('或通过如下链接下载：')
            for item in loads(response.text)[0]['assets']:
                if sys.platform.startswith('win') and ('windows' in item['browser_download_url'] or 'Windows' in item['browser_download_url']):
                    print(item['browser_download_url'])
                    break
                if sys.platform.startswith('darwin') and ('macos' in item['browser_download_url'] or 'macOS' in item['browser_download_url']):
                    print(item['browser_download_url'])
                    break
                if sys.platform.startswith('linux') and ('ubuntu' in item['browser_download_url'] or 'Linux' in item['browser_download_url']):
                    print(item['browser_download_url'])
                    break
            print('')
            rewriteable_word('按任意键跳过更新...')
            os.system('pause>nul') if WINOS else input('Press Enter to skip...')
            print('即将跳过更新。不推荐跳过更新，如遇问题请及时更新。')
            time.sleep(3)
    except requests.exceptions.ConnectTimeout:
        print('× 检查更新超时，网络连接不稳定！\n')
        print('即将跳过更新。')
        time.sleep(3)
    except:
        if debug: print(format_exc())
        print('× 检查更新失败！\n')
        rewriteable_word('按任意键跳过...')
        os.system('pause>nul') if WINOS else input('Press Enter to skip...')
    if WINOS and not quiet_flag: os.system('cls')


WINOS = True if sys.platform.startswith('win') else False
if WINOS:
    os.system('title Gfriends Inputer ' + version)
else:
    # 类 Unix 系统的默认工作目录不在程序所在文件夹
    config_path = '/'.join((sys.argv[0].replace('\\', '/')).split('/')[:-1])
    work_path = os.getcwd().replace('\\', '/')
    if work_path != config_path:
        os.chdir(config_path)  # 切换工作目录
(config_file, quiet_flag) = argparse_function(version)
if quiet_flag: sys.stdout = open("./Getter/quiet.log", "w", buffering=1)
(repository_url, host_url, api_key, overwrite, fixsize, max_retries, Proxy, aifix, debug, deleteall,
 download_path, local_path, max_download_connect, max_upload_connect, BD_AI_client, BD_VIP) = read_config(
    config_file)

# 持久会话
session = requests.Session()
session.mount('http://', requests.adapters.HTTPAdapter(max_retries=max_retries))
session.mount('https://', requests.adapters.HTTPAdapter(max_retries=max_retries))

# 局部代理
if Proxy:
    proxies = {'http': Proxy, 'https': Proxy}
else:
    proxies = None

# 检查更新
public_ip = None
check_update()
if deleteall: del_all()

# 变量初始化
num_suc = num_fail = num_skip = num_exist = 0
exist_list = []
pic_path_dict = {}
actor_dict = {}
link_dict = {}
proc_flag = False

print('Gfriends Inputer ' + version)
print('https://git.io/gfriends\n')

if not quiet_flag:
    rewriteable_word('按任意键开始...')
    os.system('pause>nul') if WINOS else input('Press Enter to start...')

# 代理配置提示
if not proxies:
    if public_ip and 'CN' in public_ip:
        print(public_ip, '推荐开启全局代理\n')
    elif public_ip and 'CN' not in public_ip:
        print(public_ip, '正通过全局代理访问\n')
    else:
        print('推荐开启全局代理\n')
else:
    if public_ip and 'CN' in public_ip:
        print(public_ip, '已连通局部代理，但这个代理似乎不具有科学加速的功效\n')
    elif public_ip and 'CN' not in public_ip:
        print(public_ip, '已连通局部代理\n')
    else:
        print('已配置局部代理 ' + Proxy + '，但似乎无法连通，请检查其格式和可用性\n')

try:
    (list_persons, emby_flag) = read_persons(host_url, api_key, True)
    gfriends_map = get_gfriends_map(repository_url)
    actor_log = open('./Getter/演员清单.txt', 'w', encoding="UTF-8", buffering=1)
    actor_log.write('【演员清单】\n该清单仅供参考，下面可能还有导演、编剧、赞助商等其他人的名字，但是女友头像仓库只会收录日本女友。\n而已匹配到的头像则会根据个人配置，下载导入或会跳过\n\n')

    rewriteable_word('>> 引擎初始化...')
    md5_persons = md5(str(list_persons).encode('UTF-8')).hexdigest()[14:-14]
    md5_config = md5(open('config.ini', 'rb').read()).hexdigest()[14:-14]  # md5计算只支持字节流
    if os.path.exists('./Getter/proc.tmp'):  # 有中断记录，则逐行读取记录
        with open('./Getter/proc.tmp', 'r', encoding='UTF-8') as file:
            proc_list = file.read().split('\n')
        if md5_persons in proc_list and md5_config in proc_list:  # 上次中断后，演员列表和配置文件没有变化才尝试续传
            proc_flag = True
    proc_log = open('./Getter/proc.tmp', 'w', encoding="UTF-8", buffering=1)
    proc_log.write('## Gfriends Inputer 断点记录 ##\n' + md5_persons + '\n' + md5_config + '\n')

    for dic_each_actor in list_persons:
        actor_name = dic_each_actor['Name']
        actor_id = dic_each_actor['Id']
        if dic_each_actor['ImageTags']:
            num_exist += 1
            exist_list.append(actor_name)
            if overwrite == '0':
                actor_log.write('跳过：' + actor_name + '\n')
                num_skip += 1
                continue
        if not os.path.exists(local_path + actor_name + ".jpg"):
            pic_link = get_gfriends_link(actor_name)
            if not pic_link:
                old_actor_name = actor_name
                actor_name = re.sub(r'（.*）', '', actor_name)
                actor_name = re.sub(r'\(.*\)', '', actor_name)
                pic_link = get_gfriends_link(actor_name)
                if not pic_link:
                    actor_log.write('未找到：' + actor_name + '\n')
                    num_fail += 1
                    continue
                if old_actor_name in exist_list:
                    exist_list.remove(old_actor_name)
                    exist_list.append(actor_name)
            actor_log.write('下载：' + actor_name + '\n')
            link_dict[actor_name] = pic_link
        actor_dict[actor_name] = actor_id
        inputed_dict = {}
    actor_log.close()

    if overwrite == '2':
        md5_host_url = md5(host_url.encode('UTF-8')).hexdigest()[14:-14]
        if os.path.exists('./Getter/down' + md5_host_url + '.log'):  # 有下载记录，则逐行读取记录
            with open('./Getter/down' + md5_host_url + '.log', 'r', encoding='UTF-8') as file:
                downlog_list = file.read().split('\n')
            down_log = open('./Getter/down' + md5_host_url + '.log', 'w', encoding="UTF-8")
            if md5_config in downlog_list:
                for item in downlog_list:
                    if '|' in item:
                        inputed_dict[item.split('|')[0]] = item.split('|')[1]
                    elif item == '':
                        pass
                    down_log.write(item + '\n')
            else:
                down_log.write(
                    '## Gfriends Inputer 导入记录 ##\n## 请注意：删除本文件会导致服务器 ' + host_url + ' 的增量更新功能重置\n' + md5_config + '\n')
            down_log.close()

        for index, actor_name in enumerate(list(link_dict)):  # 有删除字典的操作，不能直接遍历字典
            try:
                if WINOS and not quiet_flag and index % 5 == 0:
                    rewriteable_word('>> 引擎初始化... ' + str(index) + '/' + str(len(list(link_dict))))
                proc_md5 = md5((actor_name + '+0').encode('UTF-8')).hexdigest()[13:-13]
                if not proc_flag or (proc_flag and not proc_md5 in proc_list):
                    check_avatar(link_dict[actor_name], actor_name, proc_md5)  # 记录检查完成的操作放到子线程中，以防没下完中断的断点没记录到
                else:
                    proc_log.write(proc_md5 + '\n')
                while True:
                    if threading.activeCount() > 10 * max_download_connect + 1:
                        time.sleep(0.01)
                    else:
                        break
            except KeyboardInterrupt:
                sys.exit()
            except:
                if debug: print(format_exc())
                print('× 网络连接异常，跳过检查：' + str(actor_name) + '\n')
                continue
        for thr_status in threading.enumerate():  # 等待子线程运行结束
            try:
                thr_status.join()
            except RuntimeError:
                continue
    print('√ 引擎初始化成功，尝试从上次中断位置继续') if proc_flag else print('√ 引擎初始化成功                      ')

    if not link_dict:
        print('\n√ 没有需要下载的头像')
    else:
        print('\n>> 下载头像...')
        with alive_bar(len(link_dict), enrich_print=False, dual_line=True) as bar:
            for actor_name, link in link_dict.items():
                try:
                    bar.text('正在下载：'+re.sub(r'（.*）', '', actor_name)) if '（' in actor_name else bar.text('正在下载：'+actor_name)
                    bar()
                    proc_md5 = md5((actor_name + '+1').encode('UTF-8')).hexdigest()[13:-13]
                    if not proc_flag or (proc_flag and not proc_md5 in proc_list):
                        download_avatar(link, actor_name, proc_md5)  # 记录下载完成的操作放到子线程中，以防没下完中断的断点没记录到
                    else:
                        proc_log.write(proc_md5 + '\n')
                    while True:
                        if threading.activeCount() > max_download_connect + 1:
                            time.sleep(0.01)
                        else:
                            break
                except KeyboardInterrupt:
                    sys.exit()
                except:
                    with bar.pause():
                        if debug: print(format_exc())
                        print('× 网络连接异常且重试 ' + str(max_retries) + ' 次失败')
                        print('× 请尝试开启全局代理或配置 HTTP 局部代理；若已开启代理，请检查其可用性')
                        print('× 按任意键继续运行则跳过下载这些头像：' + str(actor_name) + '\n')
                        os.system('pause>nul') if WINOS else input()
                    continue
        rewriteable_word('>> 即将完成')
        for thr_status in threading.enumerate():  # 等待子线程运行结束
            try:
                thr_status.join()
            except RuntimeError:
                continue
        print('√ 下载完成')

    # 构建路径映射
    for filename in os.listdir(download_path):
        if '.jpg' in filename and filename.replace('.jpg', '') in actor_dict:
            if overwrite == '2':
                if filename.replace('.jpg', '') in link_dict:  # link_dict 已经初始化筛选，key 为需要导入的演员名
                    pic_path_dict[filename] = download_path + filename
            else:
                pic_path_dict[filename] = download_path + filename
    for filename in os.listdir(local_path):
        if '.jpg' in filename and filename.replace('.jpg', '') in actor_dict:
            if overwrite == '2' and filename.replace('.jpg', '') in exist_list:  # 覆盖导入且现在头像不存在
                actor_md5 = md5(filename.replace('.jpg', '').encode('UTF-8')).hexdigest()[12:-12]
                if actor_md5 not in inputed_dict or inputed_dict[actor_md5] != str(
                        os.path.getsize(local_path + filename)):
                    pic_path_dict[filename] = local_path + filename
                inputed_dict[actor_md5] = str(os.path.getsize(local_path + filename))
            else:
                pic_path_dict[filename] = local_path + filename

    if not pic_path_dict:
        proc_log.close()
        os.remove('./Getter/proc.tmp')
        if overwrite == '2':
            down_log = open('./Getter/down' + md5_host_url + '.log', 'w', encoding="UTF-8")
            down_log.write(
                '## Gfriends Inputer 导入记录 ##\n## 请注意：删除本文件会导致服务器 ' + host_url + ' 的增量更新功能重置\n' + md5_config + '\n')
            for key, value in inputed_dict.items():
                down_log.write(key + '|' + value + '\n')
            down_log.close()
        print('\n√ 没有需要导入的头像')
        if WINOS and not quiet_flag: print('\n按任意键退出程序...'); os.system('pause>nul')
        os._exit(1)

    if fixsize != '0':
        print('\n>> 尺寸优化...')
        with alive_bar(len(pic_path_dict), enrich_print=False, dual_line=True) as bar:
            for filename, pic_path in pic_path_dict.items():
                bar.text('正在优化：'+re.sub(r'（.*）', '', filename).replace('.jpg', '')) if '（' in filename else bar.text('正在优化：'+
                    filename.replace('.jpg', ''))
                bar()
                proc_md5 = md5((filename + '+2').encode('UTF-8')).hexdigest()[13:-13]
                if not proc_flag or (proc_flag and not proc_md5 in proc_list):
                    result = fix_size(fixsize, pic_path)
                    if not result: pic_path_dict.pop(filename)
                proc_log.write(proc_md5 + '\n')
        print('√ 优化完成')

    print('\n>> 导入头像...')
    with alive_bar(len(pic_path_dict), enrich_print=False, dual_line=True) as bar:
        for filename, pic_path in pic_path_dict.items():
            bar.text('正在导入：'+re.sub(r'（.*）', '', filename).replace('.jpg', '')) if '（' in filename else bar.text('正在导入：'+
                filename.replace('.jpg', ''))
            bar()
            proc_md5 = md5((filename + '+3').encode('UTF-8')).hexdigest()[13:-13]
            if not proc_flag or (proc_flag and not proc_md5 in proc_list):
                with open(pic_path, 'rb') as pic_bit:
                    b6_pic = b64encode(pic_bit.read())
                if emby_flag:
                    url_post_img = host_url + 'emby/Items/' + actor_dict[
                        filename.replace('.jpg', '')] + '/Images/Primary?api_key=' + api_key
                else:
                    url_post_img = host_url + 'jellyfin/Items/' + actor_dict[
                        filename.replace('.jpg', '')] + '/Images/Primary?api_key=' + api_key
                input_avatar(url_post_img, b6_pic)
            proc_log.write(proc_md5 + '\n')
            while True:
                if threading.activeCount() > max_upload_connect + 1:
                    time.sleep(0.01)
                else:
                    break
            num_suc += 1
    rewriteable_word('>> 即将完成')
    for thr_status in threading.enumerate():  # 等待子线程运行结束
        try:
            thr_status.join()
        except RuntimeError:
            continue
    proc_log.close()
    os.remove('./Getter/proc.tmp')
    if overwrite == '2':
        down_log = open('./Getter/down' + md5_host_url + '.log', 'w', encoding="UTF-8")
        down_log.write(
            '## Gfriends Inputer 导入记录 ##\n## 请注意：删除本文件会导致服务器 ' + host_url + ' 的增量更新功能重置\n' + md5_config + '\n')
        for key, value in inputed_dict.items():
            down_log.write(key + '|' + value + '\n')
        down_log.close()
    print('√ 导入完成')
    print('\nEmby / Jellyfin 演职人员共 ' + str(len(list_persons)) + ' 人，其中 ' + str(num_exist) + ' 人之前已有头像')
    print('本次导入 ' + str(num_suc) + ' 人，还有 ' + str(num_fail) + ' 人没有头像\n')
    if overwrite == '0': print('-- 未开启覆盖已有头像，所以跳过了一些演员，详见 Getter 目录下的记录清单')
except (KeyboardInterrupt, SystemExit):
    print('× 用户强制停止或已知错误。')
except:
    if debug: print(format_exc())
    print('× 未知错误，在配置文件中开启 Debug 可获得错误详情。')
if WINOS and not quiet_flag: print('按任意键退出程序...'); os.system('pause>nul')
