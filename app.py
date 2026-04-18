import yfinance as yf
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import numpy as np

app = Flask(__name__)

# 設定済みトークン
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('819afe02261cce3b569dd0d9e849701c')

def get_company_name(ticker):
    """名前を執念深く取得する関数"""
    try:
        stock = yf.Ticker(ticker)
        # 方法1: infoから取得（基本）
        name = stock.info.get('longName') or stock.info.get('shortName')
        if name: return name

        # 方法2: Search機能を使って逆引き（強力）
        search = yf.Search(ticker, max_results=1)
        if search.quotes:
            return search.quotes[0].get('longname') or search.quotes[0].get('shortname')
        
        # 方法3: 履歴データのメタ情報から取得
        name = stock.history_metadata.get('symbol')
        return name if name else ticker
    except:
        return ticker

def predict_stock_final(ticker_input):
    try:
        ticker = ticker_input.upper()
        if len(ticker) == 4 and ticker.isdigit():
            ticker += ".T"
        
        stock = yf.Ticker(ticker)
        data = stock.history(period='60d')
        
        if data.empty:
            return f"銘柄 {ticker} が見つかりませんでした。"

        # 会社名の取得（強化版関数を呼び出し）
        company_name = get_company_name(ticker)

        prices = data['Close'].values
        current_price = float(prices[-1])
        
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

