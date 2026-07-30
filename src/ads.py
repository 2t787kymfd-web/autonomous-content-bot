"""
ads.py
------
AdSenseのパブリッシャーIDと、<head>に埋め込む広告スクリプトタグを一箇所で管理する。
"""

ADSENSE_CLIENT_ID = "ca-pub-6750806391010121"

ADSENSE_HEAD_SNIPPET = (
    '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
    f'?client={ADSENSE_CLIENT_ID}" crossorigin="anonymous"></script>'
)
