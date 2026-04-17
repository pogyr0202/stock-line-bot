import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

# LINEの設定（自分のものに書き換え）
line_bot_api = LineBotApi('gCpKFk6xSV/6ngm6UYCopsSOaKV5NrOdE3bs5IJQLI2CL1nK1eJaQzEGw4+rbK/B2eX2GkyVfh3roE2AE66ShFdgstCvmDAfanmfyLgMVesG2DCdugf7501YjEG3y+pouCZMcXYfHNrMDJCARl/gtwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('819afe02261cce3b569dd0d9e849701c')

def predict_stock(ticker):
    try:
        data = yf.download(ticker, period='300d', interval='1d')
        if data.empty: return "銘柄が見つかりません"
        df = data[['Close']].dropna().values
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(df)
        train_data = scaled_data[-100:]
        x_train, y_train = [], []
        for i in range(30, len(train_data)):
            x_train.append(train_data[i-30:i, 0])
            y_train.append(train_data[i, 0])
        x_train = np.array(x_train).reshape(-1, 30, 1)
        y_train = np.array(y_train)
        model = Sequential([LSTM(20, input_shape=(30, 1)), Dense(1)])
        model.compile(optimizer='adam', loss='mse')
        model.fit(x_train, y_train, epochs=3, batch_size=16, verbose=0)
        current_batch = scaled_data[-30:].reshape(1, 30, 1)
        preds = []
        for _ in range(30):
            p = model.predict(current_batch, verbose=0)[0]
            preds.append(p)
            current_batch = np.append(current_batch[:, 1:, :], [[p]], axis=1)
                # 予測結果の計算
        actual_preds = scaler.inverse_transform(preds)
        diff = actual_preds[29][0] - actual_preds[0][0] # 30日後と1日後の差
        
        res = f"【{ticker} 予測結果】\n"
        res += f"30日間の予測推移: {'+' if diff > 0 else ''}{diff:.1f}円\n"
        res += f"（1日後: {actual_preds[0][0]:.1f}円 → 30日後: {actual_preds[29][0]:.1f}円）"
        return res

    except:
        return "予測エラー。銘柄を確認してください。"

@app.route("/callback", methods=['POST'])
def callback():
    handler.handle(request.get_data(as_text=True), request.headers.get('x-line-signature', ''))
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    ticker = event.message.text.upper()
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"「{ticker}」を解析中..."))
    result_text = predict_stock(ticker)
    line_bot_api.push_message(event.source.user_id, TextSendMessage(text=result_text))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
