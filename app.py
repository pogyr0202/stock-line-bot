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

def get_ticker_from_name(name):
    """企業名からティッカーシンボルを探す関数"""
    try:
        # yfinanceの検索機能を使用
        search = yf.Search(name, max_results=1)
        if search.quotes:
            # 検索結果の1番目のシンボル（コード）を返す
            return search.quotes[0]['symbol']
    except:
        pass
    return None

def predict_stock_v4(user_input):
    try:
        # 1. まず入力された言葉で検索してコードを取得
        # （数字だけの場合はそのまま、文字の場合は検索）
        ticker = user_input
        if not user_input.replace('.', '').isdigit():
            found_ticker = get_ticker_from_name(user_input)
            if found_ticker:
                ticker = found_ticker
            else:
                return "その企業名では銘柄が見つかりませんでした。"

        # 2. データの取得
        stock = yf.Ticker(ticker)
        data = stock.history(period='60d')
        if data.empty: return f"銘柄コード {ticker} のデータが見つかりません"
        
        # 企業名などの情報
        info = stock.info
        company_name = info.get('longName', ticker)
        prices = data['Close'].values
        current_price = prices[-1]
        
        # トレンド計算
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        trend = (ma5 - ma20) / 15
        
        # 予測メッセージ作成
        res = f"【{company_name}】\n"
        res += f"（検索結果: {ticker}）\n"
        res += f"現在値: {current_price:.1f}円\n\n"
        
        daily_predictions = []
        show_days = [1, 5, 10, 15, 20, 25, 30]
        for day in range(1, 31):
            pred_price = current_price + (trend * day)
            daily_predictions.append(pred_price)
            if day in show_days:
                res += f"{day}日後: {pred_price:.1f}円\n"
        
        pred_30d = daily_predictions[29]
        diff = pred_30d - current_price
        pct = (diff / current_price) * 100
        
        res += f"\n30日間の予測推移: {'+' if diff > 0 else ''}{diff:.1f}円\n"
        res += f"騰落率予測: {'+' if pct > 0 else ''}{pct:.1f}%\n"
        return res
    except Exception as e:
        return f"解析エラーが発生しました。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"「{user_text}」を検索して解析中..."))
    
    result_text = predict_stock_v4(user_text)
    line_bot_api.push_message(event.source.user_id, TextSendMessage(text=result_text))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
