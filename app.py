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

def predict_stock_stable(ticker):
    try:
        # 過去60日分のデータを取得
        data = yf.download(ticker, period='60d', interval='1d')
        if data.empty: return "銘柄が見つかりません"
        
        # 終値のリストを取得
        prices = data['Close'].values.flatten()
        current_price = prices[-1]
        
        # 直近5日間の移動平均と、20日間の移動平均からトレンド（勢い）を計算
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        
        # 1日あたりの平均変化率を簡易的に算出
        trend = (ma5 - ma20) / 15
        
        # 30日後の予測
        prediction_30d = current_price + (trend * 30)
        diff = prediction_30d - current_price
        
        res = f"【{ticker} 安定予測】\n"
        res += f"現在値: {current_price:.1f}円\n"
        res += f"30日間の予測推移: {'+' if diff > 0 else ''}{diff:.1f}円\n"
        res += f"（30日後の予想: {prediction_30d:.1f}円）\n\n"
        res += "※直近20日間のトレンドから算出しています。"
        return res
    except Exception as e:
        return f"予測エラー: 形式を確認してください。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    ticker = event.message.text.upper()
    # ユーザーへ「解析中」を送る
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"「{ticker}」を安定モデルで解析中..."))
    
    # 予測結果を計算してプッシュメッセージで送る
    result_text = predict_stock_stable(ticker)
    line_bot_api.push_message(event.source.user_id, TextSendMessage(text=result_text))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)