import yfinance as yf
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# トークン設定
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('819afe02261cce3b569dd0d9e849701c')

def get_japanese_name(ticker_input):
    code = ticker_input.split('.')[0]
    url = f"https://finance.yahoo.co.jp/quote/{code}.T"
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('title').get_text()
        return title.split('【')[0] if '【' in title else ticker_input
    except:
        return ticker_input

def calculate_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    # MACD
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def judge_signal(rsi, macd, signal):
    """買い・売りの総合判定"""
    # 買い条件
    buy_score = 0
    if rsi < 35: buy_score += 1 # 売られすぎ
    if macd > signal: buy_score += 1 # 上昇トレンド
    
    # 売り条件
    sell_score = 0
    if rsi > 65: sell_score += 1 # 買われすぎ
    if macd < signal: sell_score += 1 # 下落トレンド

    if buy_score >= 2: return "🔥【強気の買い時】"
    if buy_score == 1: return "✨【買い検討】"
    if sell_score >= 2: return "💀【即売り検討】"
    if sell_score == 1: return "⚠️【売り検討・利益確定】"
    return "😑【様子見・レンジ相場】"

def predict_stock_v3(user_input):
    try:
        ticker = user_input.upper()
        if "." not in ticker and 4 <= len(ticker) <= 5:
            if any(char.isdigit() for char in ticker):
                ticker += ".T"
        
        name = get_japanese_name(ticker) if ticker.endswith(".T") else ticker
        stock = yf.Ticker(ticker)
        data = stock.history(period='100d')
        
        if data.empty: return f"銘柄 {ticker} は見つかりません。"

        data = calculate_indicators(data)
        r, m, s = data['RSI'].iloc[-1], data['MACD'].iloc[-1], data['Signal'].iloc[-1]
        
        prices = data['Close'].values
        cur = float(prices[-1])
        trend = (np.mean(prices[-5:]) - np.mean(prices[-20:])) / 15
        
        # メッセージ組み立て
        res = f"【{name}】\n"
        res += f"現在値: {cur:.1f}円\n"
        res += f"RSI: {r:.1f}%\n\n"
        
        res += f"📢 判定：{judge_signal(r, m, s)}\n"
        res += "------------------\n"
        
        # 30日予測
        res += "📅 未来予測\n"
        p30 = cur + (trend * 30)
        pct = (p30 - cur) / cur * 100
        res += f" 7日後: {cur+(trend*7):.1f}円\n"
        res += f"30日後: {p30:.1f}円\n"
        res += f"予測騰落率: {'+' if pct > 0 else ''}{pct:.1f}%\n"
        
        return res
    except Exception:
        return "エラーが発生しました。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    result = predict_stock_v3(event.message.text)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
