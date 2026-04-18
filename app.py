import numpy as np
import yfinance as yf
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

# LINE設定（ご自身のものに！）
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('819afe02261cce3b569dd0d9e849701c')

def predict_stock_final_v2(user_input):
    try:
        # 1. 銘柄コードの特定
        ticker = user_input.upper()
        # もし数字4桁だけなら「.T」を自動で付ける
        if len(ticker) == 4 and ticker.isdigit():
            ticker += ".T"
        
        # 2. データの取得
        stock = yf.Ticker(ticker)
        data = stock.history(period='60d')
        
        # もしデータが空なら、企業名での検索を試みる
        if data.empty:
            search = yf.Search(user_input, max_results=1)
            if search.quotes:
                ticker = search.quotes[0]['symbol']
                stock = yf.Ticker(ticker)
                data = stock.history(period='60d')
        
        if data.empty:
            return "銘柄が見つかりませんでした。「トヨタ」や「7203」のように入力してください。"

        # 3. 計算処理
        prices = data['Close'].values
        current_price = prices[-1]
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        trend = (ma5 - ma20) / 15
        
        # 4. メッセージ構築
        company_name = stock.info.get('shortName', ticker)
        res = f"【{company_name}】\n"
        res += f"現在値: {current_price:.1f}円\n\n"
        
        target_days = [1, 5, 10, 15, 20, 25, 30]
        for d in target_days:
            p = current_price + (trend * d)
            res += f"{d}日後: {p:.1f}円\n"
        
        diff = (current_price + (trend * 30)) - current_price
        pct = (diff / current_price) * 100
        
        res += f"\n30日間の推移: {'+' if diff > 0 else ''}{diff:.1f}円\n"
        res += f"騰落率予測: {'+' if pct > 0 else ''}{pct:.1f}%"
        return res
    except Exception as e:
        return f"エラー: 銘柄コード（例: 7203）を試してください。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 返信
    result = predict_stock_final_v2(event.message.text)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

if __name__ == "__main__":
    # Renderのポートに確実に合わせる設定
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
