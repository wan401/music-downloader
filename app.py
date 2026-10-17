# -*- coding: utf-8 -*-
"""音乐下载工具 安卓版 - Flask后端"""
import os
import re
import json
import threading
import time

from flask import Flask, render_template, jsonify, request

VERSION = "v1.1-android"

app = Flask(__name__)

# 全局状态（单用户本地服务，简单够用）
state = {
    'progress': 0,
    'status': '就绪',
    'log': [],
    'done': None,  # True/False/None
    'downloading': False,
}

def get_save_dir():
    """获取安卓默认保存目录"""
    # 安卓公共音乐目录
    for p in [
        '/storage/emulated/0/Music/Downloaded',
        '/sdcard/Music/Downloaded',
        os.path.expanduser('~/Music/Downloaded'),
        os.path.expanduser('~/Download/Music'),
    ]:
        try:
            os.makedirs(p, exist_ok=True)
            # 测试可写
            test_file = os.path.join(p, '.write_test')
            with open(test_file, 'w') as f:
                f.write('ok')
            os.remove(test_file)
            return p
        except:
            continue
    # 兜底
    d = os.path.expanduser('~')
    os.makedirs(d, exist_ok=True)
    return d

def find_ffmpeg():
    """查找ffmpeg路径"""
    import shutil
    # 环境变量
    exe = shutil.which('ffmpeg')
    if exe:
        return os.path.dirname(exe)
    # 常见路径
    for p in ['/usr/bin', '/usr/local/bin', '/data/data/com.termux/files/usr/bin']:
        if os.path.exists(os.path.join(p, 'ffmpeg')):
            return p
    return None

def log(msg):
    state['log'].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    if len(state['log']) > 100:
        state['log'] = state['log'][-100:]

def get_session():
    import requests
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    })
    try:
        s.get('https://www.bilibili.com/', timeout=10)
    except:
        pass
    return s

@app.route('/')
def index():
    return render_template('index.html', version=VERSION)

@app.route('/api/default_dir')
def api_default_dir():
    return jsonify({'dir': get_save_dir()})

@app.route('/api/search')
def api_search():
    kw = request.args.get('kw', '').strip()
    if not kw:
        return jsonify({'ok': False, 'error': '请输入关键词'})

    try:
        s = get_session()
        r = s.get(
            'https://api.bilibili.com/x/web-interface/search/type',
            params={'search_type': 'video', 'keyword': kw, 'page': 1, 'page_size': 20, 'order': 'totalrank'},
            headers={'Referer': 'https://search.bilibili.com/'},
            timeout=15
        )
        data = r.json()
        if data.get('code') != 0:
            return jsonify({'ok': False, 'error': data.get('message', '搜索失败')})

        items = []
        for v in ((data.get('data') or {}).get('result') or []):
            bvid = v.get('bvid')
            if not bvid:
                continue
            title = re.sub(r'<[^>]+>', '', v.get('title', ''))
            ds = v.get('duration', '')
            dur = 0
            if ds and ':' in ds:
                p = ds.split(':')
                try:
                    dur = int(p[0]) * 60 + int(p[1])
                except:
                    pass
            items.append({
                'title': title,
                'url': f'https://www.bilibili.com/video/{bvid}',
                'uploader': v.get('author', ''),
                'duration': dur
            })
        return jsonify({'ok': True, 'items': items})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/api/download', methods=['POST'])
def api_download():
    if state['downloading']:
        return jsonify({'ok': False, 'error': '正在下载中，请稍候'})

    url = request.json.get('url', '').strip()
    save_dir = request.json.get('save_dir', '').strip() or get_save_dir()

    if not url:
        return jsonify({'ok': False, 'error': '请提供视频链接'})

    threading.Thread(target=do_download, args=(url, save_dir), daemon=True).start()
    return jsonify({'ok': True})

def do_download(url, save_dir):
    state['downloading'] = True
    state['progress'] = 0
    state['status'] = '排队中...'
    state['done'] = None
    state['log'] = []
    log(f"开始下载: {url}")

    try:
        import yt_dlp
    except ImportError:
        log("[错误] 未安装 yt-dlp，请先运行 pip install yt-dlp")
        state['status'] = '失败：缺少 yt-dlp'
        state['done'] = False
        state['downloading'] = False
        return

    ff = find_ffmpeg()
    if ff:
        log(f"ffmpeg 路径: {ff}（将转MP3）")
    else:
        log("未找到 ffmpeg，将直接保存为 m4a 格式（手机可直接播放）")

    if not os.path.isdir(save_dir):
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception as e:
            log(f"[错误] 无法创建保存目录: {e}")
            state['status'] = f'失败：{e}'
            state['done'] = False
            state['downloading'] = False
            return

    outtmpl = os.path.join(save_dir, "%(title)s.%(ext)s")

    def hook(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            got = d.get('downloaded_bytes') or 0
            sp = d.get('speed') or 0
            if total:
                pct = got * 100 / total
                state['progress'] = pct
                state['status'] = f"下载中 {pct:.1f}%  {sp/1024/1024:.1f} MB/s"
        elif d.get('status') == 'finished':
            state['progress'] = 99
            state['status'] = '下载完成，正在处理...'

    # 基础选项：直接下载最佳音频（m4a）
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl,
        'progress_hooks': [hook],
        'quiet': True,
        'no_warnings': True
    }

    # 如果有ffmpeg，就转成MP3
    if ff:
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320'
        }]
        opts['ffmpeg_location'] = ff

    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=True)
            title = info.get('title', '')
            log(f"[完成] 《{title}》")
            log(f"保存位置: {save_dir}")
            state['progress'] = 100
            state['status'] = f'完成！已保存到 {save_dir}'
            state['done'] = True
    except Exception as e:
        log(f"[失败] {e}")
        state['status'] = f'失败：{e}'
        state['done'] = False

    state['downloading'] = False

@app.route('/api/status')
def api_status():
    return jsonify({
        'progress': state['progress'],
        'status': state['status'],
        'log': state['log'][-20:],  # 最近20条
        'done': state['done'],
        'downloading': state['downloading']
    })

if __name__ == '__main__':
    port = 5000
    print(f"音乐下载工具 {VERSION}")
    print(f"访问 http://127.0.0.1:{port}")
    print(f"保存目录: {get_save_dir()}")
    app.run(host='127.0.0.1', port=port, debug=False)
