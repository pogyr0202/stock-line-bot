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

def get_company_name_v3(ticker_input):
    """アルファベット混じりのコードでも執念深く名前を探す"""
    clean_ticker = ticker_input.split('.')[0]
    try:
        # まずは検索機能で名前を探す
        search = yf.Search(clean_ticker, max_results=2)
        if search.quotes:
            for quote in search.quotes:
                if quote.get('symbol').startswith(clean_ticker):
                    name = quote.get('longname') or quote.get('shortname')
                    if name: return name
    except:
        pass
    
    try:
        # 検索で見つからなければ直接情報を取る
        stock = yf.Ticker(ticker_input)
        return stock.info.get('shortName') or stock.info.get('longName') or ticker_input
    except:
        return ticker_input

def predict_stock_final(user_input):
    try:
        ticker = user_input.upper()
        # 【ここを修正】
        # 4〜5文字で、数字が1つでも含まれていて、ドットがない場合は日本株(.T)にする
        if "." not in ticker and 4 <= len(ticker) <= 5:
            if any(char.isdigit() for char in ticker):
                ticker += ".T"
        
        company_name = get_company_name_v3(ticker)
        stock = yf.Ticker(ticker)
        data = stock.history(period='60d')
        
        if data.empty:
            return f"銘柄 {ticker} のデータが見つかりませんでした。"

        prices = data['Close'].values
        current_price = float(prices[-1])
        
        # トレンド計算（簡易版）
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
        return "解析エラーが発生しました。コードを再確認してください。"

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
