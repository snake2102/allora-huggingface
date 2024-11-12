from flask import Flask, Response
import requests
import json
import pandas as pd
import torch
from chronos import ChronosPipeline
import traceback

app = Flask(__name__)

model_name = "amazon/chronos-t5-small"

try:
    pipeline = ChronosPipeline.from_pretrained(
        model_name,
        device_map="auto",
        torch_dtype=torch.float32,
    )
except Exception as e:
    print(f"Error al cargar el modelo: {e}")
    pipeline = None

@app.route("/inference/value/<string:token>")
def get_value_inference(token):
    if pipeline is None:
        return Response(json.dumps({"error": "El modelo no está cargado"}), status=500, mimetype='application/json')
    try:
        df = get_binance_data(token)
        context = torch.tensor(df["price"].values)
        prediction_length = 1
        forecast = pipeline.predict(context, prediction_length)
        forecast_value = forecast[0].mean().item()
        response_data = {
            "forecast": forecast_value
        }
        return Response(json.dumps(response_data), status=200, mimetype='application/json')
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')

@app.route("/inference/volatility/<string:token>")
def get_volatility_inference(token):
    try:
        df = get_binance_data(token)
        current_price = df["price"].iloc[-1]
        old_price = df["price"].iloc[0]
        price_change = (current_price - old_price) / old_price
        volatility_percentage = abs(price_change) * 100
        response_data = {
            "volatility_percentage": volatility_percentage
        }
        return Response(json.dumps(response_data), status=200, mimetype='application/json')
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')

def get_binance_data(token):
    base_url = "https://api.binance.com/api/v3/klines"
    token_map = {
        'ETH': 'ETHUSDT',
        'SOL': 'SOLUSDT',
        'BTC': 'BTCUSDT',
        'BNB': 'BNBUSDT',
        'ARB': 'ARBUSDT'
    }
    token = token.upper()
    if token in token_map:
        symbol = token_map[token]
    else:
        raise ValueError("Token no soportado")
    params = {
        'symbol': symbol,
        'interval': '1m',
        'limit': 1000
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if not data:
            raise Exception("Datos vacíos recibidos de la API de Binance")
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume",
            "ignore"
        ])
        df["date"] = pd.to_datetime(df["close_time"], unit='ms')
        df["price"] = df["close"].astype(float)
        df = df[["date", "price"]]
        df = df[:-1]
        if df.empty:
            raise Exception("El dataframe de precios está vacío")
        return df
    else:
        raise Exception(f"Fallo al recuperar datos de la API de Binance: {response.text}")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
