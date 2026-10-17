# -*- coding: utf-8 -*-
"""安卓启动入口：后台Flask + 前台WebView"""
import threading
import time
import os
import sys

# 确保能导入app模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def start_flask():
    from app import app
    # 安卓上绑定所有接口，方便WebView访问
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def is_android():
    return 'ANDROID_ARGUMENT' in os.environ

def main():
    # 启动Flask后台线程
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()

    # 等Flask启动
    time.sleep(2)

    if is_android():
        # 安卓上：用WebView打开
        from kivy.app import App
        from kivy.uix.widget import Widget
        from kivy.clock import Clock
        import android
        from android.runnable import run_on_ui_thread
        from jnius import autoclass, cast

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        WebView = autoclass('android.webkit.WebView')
        WebViewClient = autoclass('android.webkit.WebViewClient')
        Intent = autoclass('android.content.Intent')

        class WebViewApp(App):
            def build(self):
                # 用Android原生WebView
                self.activity = PythonActivity.mActivity
                self.load_webview()
                return Widget()

            @run_on_ui_thread
            def load_webview(self):
                wv = WebView(self.activity)
                wv.getSettings().setJavaScriptEnabled(True)
                wv.getSettings().setDomStorageEnabled(True)
                wv.setWebViewClient(WebViewClient())
                wv.loadUrl('http://127.0.0.1:5000')
                self.activity.setContentView(wv)

        WebViewApp().run()
    else:
        # 桌面测试：直接开浏览器
        import webbrowser
        webbrowser.open('http://127.0.0.1:5000')
        print("Flask已启动: http://127.0.0.1:5000")
        print("按 Ctrl+C 退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    main()
