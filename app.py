from flask import Flask, Response, request
import requests
import json
import pandas as pd
import torch
from chronos import BaseChronosPipeline
import traceback
import logging

app = Flask(__name__)

# Configurar el registro (logging)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
app.logger.setLevel(logging.DEBUG)

model_name = "amazon/chronos-bolt-base"

try:
    app.logger.info("Cargando el modelo Chronos-Bolt...")
    pipeline = BaseChronosPipeline.from_pretrained(
        model_name,
        device_map="auto",
        torch_dtype=torch.float32
    )
    app.logger.info("Modelo cargado exitosamente.")
except Exception as e:
    app.logger.error(f"Error al cargar el modelo: {e}")
    pipeline = None

@app.route("/inference/value/<string:token>/<int:prediction_length>", methods=['GET'])
def get_value_inference(token, prediction_length):
    if pipeline is None:
        app.logger.error("Intento de inferencia sin modelo cargado.")
        return Response("El modelo no está cargado", status=500, mimetype='text/plain')
    try:
        app.logger.debug(f"Recibiendo solicitud de inferencia para token: {token} con prediction_length: {prediction_length}")
        df = get_binance_data(token)
        app.logger.debug(f"Datos obtenidos: {df.head()}")

        # Preparar el contexto
        context = torch.tensor(df['close'].values, dtype=torch.float32).unsqueeze(0)
        app.logger.debug(f"Contexto preparado con shape: {context.shape}")

        # Validar prediction_length
        if prediction_length <= 0:
            app.logger.error("prediction_length debe ser un entero positivo.")
            return Response("prediction_length debe ser un entero positivo.", status=400, mimetype='text/plain')

        forecast = pipeline.predict(context, prediction_length)
        app.logger.debug(f"Forecast generado: {forecast}")

        # Verificar la forma de la predicción
        if forecast.ndim != 3:
            app.logger.error(f"Forecast tiene una forma inesperada: {forecast.shape}")
            return Response("La predicción generada tiene una forma inesperada.", status=500, mimetype='text/plain')

        # Calcular la media de las cuantiles para cada paso de predicción
        forecast_mean = forecast.mean(dim=1).squeeze().tolist()
        app.logger.debug(f"Forecast mean calculado: {forecast_mean}")

        # Retornar la lista de valores decimales como JSON
        return Response(json.dumps({"cast": forecast_mean}), status=200, mimetype='application/json')
    except Exception as e:
        traceback_str = traceback.format_exc()
        app.logger.error(f"Error durante la inferencia: {traceback_str}")
        return Response(str(e), status=500, mimetype='text/plain')

@app.route("/inference/value/<string:token>", methods=['GET'])
def get_value_inference_default(token):
    default_prediction_length = 1  # Valor predeterminado para prediction_length
    if pipeline is None:
        app.logger.error("Intento de inferencia sin modelo cargado.")
        return Response("El modelo no está cargado", status=500, mimetype='text/plain')
    try:
        app.logger.debug(f"Recibiendo solicitud de inferencia para token: {token} con prediction_length: {default_prediction_length}")
        df = get_binance_data(token)
        app.logger.debug(f"Datos obtenidos: {df.head()}")

        # Preparar el contexto
        context = torch.tensor(df['close'].values, dtype=torch.float32).unsqueeze(0)
        app.logger.debug(f"Contexto preparado con shape: {context.shape}")

        # Validar prediction_length
        if default_prediction_length <= 0:
            app.logger.error("prediction_length debe ser un entero positivo.")
            return Response("prediction_length debe ser un entero positivo.", status=400, mimetype='text/plain')

        forecast = pipeline.predict(context, default_prediction_length)
        app.logger.debug(f"Forecast generado: {forecast}")

        # Verificar la forma de la predicción
        if forecast.ndim != 3:
            app.logger.error(f"Forecast tiene una forma inesperada: {forecast.shape}")
            return Response("La predicción generada tiene una forma inesperada.", status=500, mimetype='text/plain')

        # Calcular la media de las cuantiles para cada paso de predicción
        forecast_mean = forecast.mean(dim=1).squeeze().item()
        app.logger.debug(f"Forecast mean calculado: {forecast_mean}")

        # Retornar el valor decimal directamente como texto plano
        return Response(str(forecast_mean), status=200, mimetype='text/plain')
    except Exception as e:
        traceback_str = traceback.format_exc()
        app.logger.error(f"Error durante la inferencia: {traceback_str}")
        return Response(str(e), status=500, mimetype='text/plain')

@app.route("/inference/volatility/<string:token>", methods=['GET'])
def get_volatility_inference(token):
    try:
        app.logger.debug(f"Recibiendo solicitud de volatilidad para token: {token}")
        df = get_binance_data(token)
        app.logger.debug(f"Datos obtenidos para volatilidad: {df.head()}")

        current_price = df["price"].iloc[-1]
        old_price = df["price"].iloc[0]
        price_change = (current_price - old_price) / old_price
        volatility_percentage = abs(price_change) * 100
        app.logger.debug(f"Volatilidad calculada: {volatility_percentage}%")

        return Response(str(volatility_percentage), status=200, mimetype='text/plain')
    except Exception as e:
        traceback_str = traceback.format_exc()
        app.logger.error(f"Error durante el cálculo de volatilidad: {traceback_str}")
        return Response(str(e), status=500, mimetype='text/plain')

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
        'interval': '5m',
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
        df["close"] = df["close"].astype(float)
        df["price"] = df["close"]
        df = df[["date", "close", "price"]]
        df = df[:-1]
        if df.empty:
            raise Exception("El dataframe de precios está vacío")
        return df
    else:
        raise Exception(f"Fallo al recuperar datos de la API de Binance: {response.text}")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
