import yfinance as yf
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import numpy as np

app = Flask(__name__)

# LINE設定（ご自身のものに書き換えてください）
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('Ue58a36b4aa45b1eeb12408f2e368df0a')

def predict_stock_simple(ticker_input):
    try:
        # 数字4桁なら .T を補完
        ticker = ticker_input.upper()
        if len(ticker) == 4 and ticker.isdigit():
            ticker += ".T"
        
        # データ取得（過去60日分）
        stock = yf.Ticker(ticker)
        data = stock.history(period='60d')
        
        if data.empty:
            return f"銘柄コード「{ticker}」が見つかりませんでした。正しいコードを入力してください。"

        # 企業名の取得
        # infoがエラーになることがあるため、historyのメタデータからも試行
        company_name = stock.info.get('shortName') or stock.info.get('longName') or ticker
        
        # 終値データ
        prices = data['Close'].values
        current_price = float(prices[-1])
        
        # トレンド計算（直近5日と20日の比較）
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        trend = (ma5 - ma20) / 15
        
        # メッセージ作成
        res = f"【{company_name}】\n"
        res += f"現在値: {current_price:.1f}円\n\n"
        
        # 予測リスト（1, 5, 10, 15, 20, 25, 30日後）
        for d in [1, 5, 10, 15, 20, 25, 30]:
            p = current_price + (trend * d)
            res += f"{d}日後: {p:.1f}円\n"
        
        # 推移と％
        pred_30d = current_price + (trend * 30)
        diff = pred_30d - current_price
        pct = (diff / current_price) * 100
        
        res += f"\n30日間の推移: {'+' if diff > 0 else ''}{diff:.1f}円\n"
        res += f"騰落率予測: {'+' if pct > 0 else ''}{pct:.1f}%"
        
        return res
    except Exception as e:
        return "データの取得中にエラーが発生しました。時間を置いて試してください。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    result = predict_stock_simple(event.message.text)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

