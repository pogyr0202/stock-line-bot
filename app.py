import numpy as np
import pandas as pd
import yfinance as yf
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

# LINEの設定（ご自身のものに書き換えてください）
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('819afe02261cce3b569dd0d9e849701c')

def get_ticker(text):
    """企業名からコードを検索する（精度向上版）"""
    # 既に入力自体がコードっぽい場合はそのまま返す
    if text.replace('.', '').isdigit() or ('.' in text and text.split('.')[0].isdigit()):
        return text.upper()
    
    try:
        # 日本語での検索
        search = yf.Search(text, max_results=3)
        if search.quotes:
            # 日本株(.T)を優先的に探す
            for q in search.quotes:
                symbol = q['symbol']
                if symbol.endswith('.T'):
                    return symbol
            # なければ1番目を返す
            return search.quotes[0]['symbol']
    except:
        pass
    return None

def predict_stock_final(user_input):
    try:
        ticker = get_ticker(user_input)
        if not ticker:
            return f"「{user_input}」に該当する銘柄が見つかりませんでした。"

        stock = yf.Ticker(ticker)
        # 余裕を持って少し多めにデータを取る
        data = stock.history(period='100d')
        if data.empty: return f"銘柄 {ticker} のデータが取得できませんでした。"
        
        # 企業名と現在値
        info = stock.info
        company_name = info.get('longName', ticker)
        current_price = data['Close'].values[-1]
        
        # トレンド計算（20日平均を使用）
        prices = data['Close'].values
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        trend = (ma5 - ma20) / 15
        
        # メッセージ構築
        res = f"【{company_name}】\n"
        res += f"（コード: {ticker}）\n"
        res += f"現在値: {current_price:.1f}円\n\n"
        
        daily_preds = []
        target_days = [1, 5, 10, 15, 20, 25, 30]
        for d in range(1, 31):
            p = current_price + (trend * d)
            daily_preds.append(p)
            if d in target_days:
                res += f"{d}日後: {p:.1f}円\n"
        
        # 騰落率の計算
        diff = daily_preds[29] - current_price
        pct = (diff / current_price) * 100
        
        res += f"\n30日間の予測推移: {'+' if diff > 0 else ''}{diff:.1f}円\n"
        res += f"騰落率予測: {'+' if pct > 0 else ''}{pct:.1f}%\n"
        res += "※直近20日間のトレンドに基づく予測"
        return res
    except:
        return "解析中にエラーが発生しました。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"「{user_text}」を検索して解析中..."))
    result = predict_stock_final(user_text)
    line_bot_api.push_message(event.source.user_id, TextSendMessage(text=result))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
