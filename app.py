import numpy as np
import yfinance as yf
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

# LINE設定（必ず自分のものに書き換えてください！）
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('819afe02261cce3b569dd0d9e849701c')

def get_stock_data(user_input):
    # 数字4桁なら末尾に .T をつける
    ticker = user_input.upper()
    if len(ticker) == 4 and ticker.isdigit():
        ticker += ".T"
    
    # データの取得
    stock = yf.Ticker(ticker)
    data = stock.history(period='60d')
    
    # 日本語検索（データが空の場合のみ実行）
    if data.empty:
        search = yf.Search(user_input, max_results=1)
        if search.quotes:
            ticker = search.quotes[0]['symbol']
            stock = yf.Ticker(ticker)
            data = stock.history(period='60d')
            
    return ticker, stock, data

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    try:
        ticker, stock, data = get_stock_data(user_text)
        if data.empty:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"銘柄「{user_text}」が見つかりませんでした。"))
            return

        # 計算処理
        prices = data['Close'].values
        current_price = float(prices[-1])
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        trend = (ma5 - ma20) / 15
        
        # 30日予測
        pred_30d = current_price + (trend * 30)
        diff = pred_30d - current_price
        pct = (diff / current_price) * 100
        
        # メッセージ作成
        res = f"【{ticker} 予測】\n"
        res += f"現在値: {current_price:.1f}円\n\n"
        
        for d in [1, 5, 10, 15, 20, 25, 30]:
            p = current_price + (trend * d)
            res += f"{d}日後: {p:.1f}円\n"
        
        res += f"\n30日間の推移: {'+' if diff > 0 else ''}{diff:.1f}円\n"
        res += f"騰落率予測: {'+' if pct > 0 else ''}{pct:.1f}%"
        
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))
        
    except Exception:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="エラーが発生しました。銘柄名かコードを試してください。"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
