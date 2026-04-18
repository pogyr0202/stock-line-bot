import yfinance as yf
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import numpy as np
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# 設定済みトークン
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('819afe02261cce3b569dd0d9e849701c')

def get_japanese_name(ticker_input):
    """日本のYahoo!ファイナンスから日本語名をスクレイピングする"""
    # 285A.T -> 285A に変換
    code = ticker_input.split('.')[0]
    url = f"https://finance.yahoo.co.jp/quote/{code}.T"
    
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        # ページのタイトルから企業名を取得（例：トヨタ自動車(株)【7203】）
        title = soup.find('title').get_text()
        if '【' in title:
            name = title.split('【')[0]
            # 「(株)」などを残したい場合はこのまま、消したい場合は replace してください
            return name
        return ticker_input
    except:
        return ticker_input

def predict_stock_final(user_input):
    try:
        ticker = user_input.upper()
        # 日本株の判定（4-5文字で数字を含む場合）
        if "." not in ticker and 4 <= len(ticker) <= 5:
            if any(char.isdigit() for char in ticker):
                ticker += ".T"
        
        # 会社名の取得（日本語版を優先）
        if ticker.endswith(".T"):
            company_name = get_japanese_name(ticker)
        else:
            # 米国株などは従来通り yfinance で取得
            stock_info = yf.Ticker(ticker)
            company_name = stock_info.info.get('shortName') or ticker
        
        stock = yf.Ticker(ticker)
        data = stock.history(period='60d')
        
        if data.empty:
            return f"銘柄 {ticker} のデータが見つかりませんでした。"

        prices = data['Close'].values
        current_price = float(prices[-1])
        
        # トレンド計算
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        trend = (ma5 - ma20) / 15
        
        res = f"【{company_name}】\n"
        res += f"現在値: {current_price:.1f}円\n\n"
        
        for d in [1, 5, 10, 15, 20, 25, 30]:
            p = current_price + (trend * d)
            res += f"{d}日後: {p:.1f}円\n"
        
        pred_30d = current_price + (trend * 30)
        diff = pred_30d - current_price
        pct = (diff / current_price) * 100
        
        res += f"\n30日間の推移: {'+' if diff > 0 else ''}{diff:.1f}円\n"
        res += f"騰落率予測: {'+' if pct > 0 else ''}{pct:.1f}%"
        
        return res
    except Exception:
        return "解析エラーが発生しました。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    result = predict_stock_final(event.message.text)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
