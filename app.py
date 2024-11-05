from flask import Flask, Response
import requests
import json
import pandas as pd
import torch
from chronos import ChronosPipeline

app = Flask(__name__)

model_name = "amazon/chronos-t5-small"

@app.route("/inference/<string:token>")
def get_inference(token):
    try:
        pipeline = ChronosPipeline.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.bfloat16,
        )
    except Exception as e:
        return Response(json.dumps({"error de pipeline": str(e)}), status=500, mimetype='application/json')

    try:
        df = get_binance_data(token)
    except ValueError as e:
        return Response(json.dumps({"error": str(e)}), status=400, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"Fallo al recuperar datos de la API": str(e)}),
                        status=500,
                        mimetype='application/json')

    context = torch.tensor(df["price"].values)
    prediction_length = 1

    try:
        forecast = pipeline.predict(context, prediction_length)
        print(forecast[0].mean().item())
        return Response(str(forecast[0].mean().item()), status=200)
    except Exception as e:
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
        print(df.tail(5))
        return df
    else:
        raise Exception(f"Fallo al recuperar datos de la API de Binance: {response.text}")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
