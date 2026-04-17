import numpy as np
import pandas as pd
import yfinance as yf
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

# LINEの設定（自分のものに書き換えてください）
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('819afe02261cce3b569dd0d9e849701c')

def predict_stock_full_stable(ticker):
    try:
        # 過去60日分のデータを取得
        data = yf.download(ticker, period='60d', interval='1d')
        if data.empty: return "銘柄が見つかりません"
        
        # 終値のリストを取得
        prices = data['Close'].values.flatten()
        current_price = prices[-1]
        
        # トレンド（勢い）を計算（直近5日平均と20日平均の差から算出）
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        trend = (ma5 - ma20) / 15
        
        # 1日から30日後までの毎日の価格を計算
        daily_predictions = []
        for day in range(1, 31):
            pred_price = current_price + (trend * day)
            daily_predictions.append(pred_price)
        
        # メッセージ作成
        diff = daily_predictions[29] - current_price
        res = f"【{ticker} 予測推移】\n"
        
        # 5日おきに表示（全部出すと長すぎるので調整。1,5,10,15,20,25,30日後）
        show_days = [1, 5, 10, 15, 20, 25, 30]
        for d in show_days:
            res += f"{d}日後: {daily_predictions[d-1]:.1f}円\n"
        
        res += f"\n30日間の予測推移: {'+' if diff > 0 else ''}{diff:.1f}円\n"
        res += "※直近のトレンドから算出した安定予測です。"
        
        return res
    except Exception as e:
        return f"予測エラーが発生しました。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    ticker = event.message.text.upper()
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"「{ticker}」を解析中..."))
    
    result_text = predict_stock_full_stable(ticker)
    line_bot_api.push_message(event.source.user_id, TextSendMessage(text=result_text))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)