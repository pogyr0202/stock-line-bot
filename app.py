import yfinance as yf
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import pandas as pd
from prophet import Prophet
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# トークン設定
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('819afe02261cce3b569dd0d9e849701c')

def get_japanese_name(ticker):
    code = ticker.split('.')[0]
    url = f"https://finance.yahoo.co.jp/quote/{code}.T"
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.find('title').get_text()
        return title.split('【')[0] if '【' in title else ticker
    except:
        return ticker

def judge_signal(rsi, last_price, pred_30d):
    diff_pct = (pred_30d - last_price) / last_price * 100
    if rsi < 35 and diff_pct > 0: return "🔥【絶好の買い場かも】"
    if rsi < 45 and diff_pct > 2: return "✨【買い検討】"
    if rsi > 70 or diff_pct < -5: return "💀【売り・警戒】"
    return "😑【様子見・レンジ】"

def predict_with_prophet(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period='2y')
        if df.empty: return None
        df_prophet = df.reset_index()[['Date', 'Close']]
        df_prophet['Date'] = df_prophet['Date'].dt.tz_localize(None)
        df_prophet.columns = ['ds', 'y']
        model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
        model.fit(df_prophet)
        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)
        return forecast[['ds', 'yhat']].tail(31)
    except:
        return None

def main_logic(user_input):
    try:
        ticker = user_input.upper()
        if "." not in ticker and 4 <= len(ticker) <= 5:
            if any(c.isdigit() for c in ticker): ticker += ".T"
        
        name = get_japanese_name(ticker) if ticker.endswith(".T") else ticker
        forecast = predict_with_prophet(ticker)
        if forecast is None: return "解析に失敗しました。正しい銘柄コードを入力してください。"
        
        stock = yf.Ticker(ticker)
        recent = stock.history(period='60d')
        delta = recent['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        
        cur_price = float(recent['Close'].iloc[-1])
        pred_30d = float(forecast['yhat'].iloc[-1])
        pct = (pred_30d - cur_price) / cur_price * 100
        
        # メッセージ組み立て（不要な説明文を削除）
        res = f"【{name}】\n"
        res += f"現在値: {cur_price:.1f}円 (RSI:{rsi:.1f}%)\n\n"
        res += f"📢 AI判定：{judge_signal(rsi, cur_price, pred_30d)}\n"
        res += "------------------\n"
        res += "🤖 AIによる30日後予測\n"
        res += f" 7日後: {float(forecast['yhat'].iloc[7]):.1f}円\n"
        res += f"30日後: {pred_30d:.1f}円\n"
        res += f"予測騰落率: {'+' if pct > 0 else ''}{pct:.1f}%"
        
        return res
    except Exception:
        return "解析エラーが発生しました。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    result = main_logic(event.message.text)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))