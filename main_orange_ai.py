# import serial
# import pandas as pd
# import joblib
# import time
# import warnings
# import numpy as np
# from sklearn.ensemble import IsolationForest
# from influxdb_client import InfluxDBClient, Point
# from influxdb_client.client.write_api import SYNCHRONOUS
#
# warnings.filterwarnings("ignore")
#
# # --- CONFIGURARE GENERALA
# TIMP_INVATARE = 30
# BUFFER_SIZE = 20
# SENSIBILITATE_PRAG = 1.8
#
# # --- CONFIGURARE CONEXIUNI
# PORT_SERIAL = 'COM7'
# BAUD_RATE = 115200
# TOKEN = "7R3LUSXdR0N7s1Ellb_gxhE7OwR-k18DhCk5dhRWX8X_ekTtjevNbKgnJvBpwjZcDd5lcJ0kVpfJ9YRfLytiLQ=="
# ORG = "orange-iot"
# BUCKET = "sensor_bucket"
#
# # --- INITIALIZARE INFLUXDB
# try:
#     client = InfluxDBClient(url="http://localhost:8086", token=TOKEN, org=ORG)
#     write_api = client.write_api(write_options=SYNCHRONOUS)
#     print("CONEXIUNE InfluxDB PREGATITA.")
# except Exception as e:
#     print(f"EROARE InfluxDB: {e}")
#
# def open_serial():
#     try:
#         return serial.Serial(PORT_SERIAL, BAUD_RATE, timeout=2)
#     except Exception as e:
#         print(f"EROARE SERIALA: {e}. Verificati daca Arduino IDE este inchis.")
#         exit()
#
# # --- ETAPA 1: INVATARE
# ser = open_serial()
# date_antrenare = []
# print(f"\n--- ETAPA 1: AI INVATA MEDIUL ({TIMP_INVATARE}s) ---")
# print("Nu atingeti senzorul in aceasta faza...")
#
# start_time = time.time()
# while time.time() - start_time < TIMP_INVATARE:
#     if ser.in_waiting > 0:
#         line = ser.readline().decode('utf-8', errors='ignore').strip()
#         try:
#             temp = float(line)
#             date_antrenare.append([temp, 45.0, 80.0, temp, 0.0, 0])
#             print(f"Learning: {temp} C... {int(TIMP_INVATARE - (time.time() - start_time))}s ramase")
#             write_api.write(bucket=BUCKET, record=Point("iot").field("temp", temp).field("mode", 0))
#         except:
#             continue
#
# # --- ETAPA 2: ANTRENARE SI SALVARE MODEL
# print("\n--- ETAPA 2: GENEREZ SI SALVEZ MODELUL AI ---")
# df_train = pd.DataFrame(date_antrenare,
#                         columns=['Temperature', 'Humidity', 'Battery_Level', 'Temp_Rolling_Mean', 'Temp_Rolling_Std', 'Device_ID_Encoded'])
#
# model_live = IsolationForest(contamination=0.05, random_state=42)
# model_live.fit(df_train)
# joblib.dump(model_live, 'anomaly_model.pkl')
# print("Model 'anomaly_model.pkl' creat si salvat.")
#
# # --- ETAPA 3: MONITORIZARE ACTIVA
# print("\n--- ETAPA 3: MONITORIZARE ACTIVA ---")
# time.sleep(1)
# ser.reset_input_buffer()
#
# history = []
#
# try:
#     while True:
#         if ser.in_waiting > 0:
#             line = ser.readline().decode('utf-8', errors='ignore').strip()
#             if not line: continue
#
#             try:
#                 temp_acum = float(line)
#
#                 # Calcul context temporal bazat pe datele din istoric
#                 if len(history) > 2:
#                     rolling_mean = sum(history) / len(history)
#                     rolling_std = np.std(history)
#                 else:
#                     rolling_mean = temp_acum
#                     rolling_std = 0.0
#
#                 # Predictie AI
#                 input_live = pd.DataFrame([[
#                     temp_acum, 45.0, 80.0, rolling_mean, rolling_std, 0
#                 ]], columns=df_train.columns)
#
#                 pred = model_live.predict(input_live)[0]
#
#                 # Logica de alertare
#                 if pred == -1 and (temp_acum > rolling_mean + SENSIBILITATE_PRAG):
#                     status = "ANOMALIE"
#                     is_anomaly = 1
#                     # NU adaugam in history daca este anomalie pentru a pastra pragul fix
#                 else:
#                     status = "NORMAL"
#                     is_anomaly = 0
#                     # Adaugam in history DOAR daca totul este normal
#                     history.append(temp_acum)
#                     if len(history) > BUFFER_SIZE:
#                         history.pop(0)
#
#                 print(f"[{status}] Temp: {temp_acum} C | Prag Detectie: >{rolling_mean + SENSIBILITATE_PRAG:.2f} C")
#
#                 write_api.write(bucket=BUCKET, record=Point("iot")
#                                 .field("temp", temp_acum)
#                                 .field("anomaly", is_anomaly)
#                                 .field("mode", 1))
#
#             except Exception:
#                 continue
#         else:
#             time.sleep(0.1)
# except KeyboardInterrupt:
#     print("\nSistem oprit.")
# finally:
#     ser.close()
#     client.close()


import serial
import pandas as pd
import joblib
import time
import warnings
import numpy as np
from sklearn.ensemble import IsolationForest
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

warnings.filterwarnings("ignore")

# --- CONFIGURARE GENERALA
TIMP_INVATARE = 30
BUFFER_SIZE = 15         # Buffer mai mic pentru reactie mai rapida
SENSIBILITATE_PRAG = 1.5 # Prag de 1.5 grade (echilibru bun intre fals-pozitiv si detectie)

# --- CONFIGURARE CONEXIUNI
PORT_SERIAL = 'COM7'
BAUD_RATE = 115200
TOKEN = "7R3LUSXdR0N7s1Ellb_gxhE7OwR-k18DhCk5dhRWX8X_ekTtjevNbKgnJvBpwjZcDd5lcJ0kVpfJ9YRfLytiLQ=="
ORG = "orange-iot"
BUCKET = "sensor_bucket"

# --- INITIALIZARE INFLUXDB
try:
    client = InfluxDBClient(url="http://localhost:8086", token=TOKEN, org=ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    print("CONEXIUNE InfluxDB OK.")
except Exception as e:
    print(f"EROARE InfluxDB: {e}")

def open_serial():
    try:
        return serial.Serial(PORT_SERIAL, BAUD_RATE, timeout=2)
    except Exception as e:
        print(f"EROARE SERIALA: {e}. Inchideti Arduino IDE.")
        exit()

# --- ETAPA 1: INVATARE
ser = open_serial()
date_antrenare = []
print(f"\n--- ETAPA 1: CALIBRARE ({TIMP_INVATARE}s) ---")
print("Senzorul trebuie sa stea liber pe masa...")

start_time = time.time()
while time.time() - start_time < TIMP_INVATARE:
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        try:
            temp = float(line)
            date_antrenare.append([temp, 45.0, 80.0, temp, 0.0, 0])
            print(f"Calibrare: {temp} C | {int(TIMP_INVATARE - (time.time() - start_time))}s")
            write_api.write(bucket=BUCKET, record=Point("iot").field("temp", temp).field("mode", 0))
        except:
            continue

# --- ETAPA 2: ANTRENARE SI SALVARE
print("\n--- ETAPA 2: GENERARE MODEL AI ---")
df_train = pd.DataFrame(date_antrenare,
                        columns=['Temperature', 'Humidity', 'Battery_Level', 'Temp_Rolling_Mean', 'Temp_Rolling_Std', 'Device_ID_Encoded'])

# Am crescut contamination la 0.1 pentru a fi mai sensibil la deviatii
model_live = IsolationForest(contamination=0.1, random_state=42)
model_live.fit(df_train)
joblib.dump(model_live, 'anomaly_model.pkl')
print("Model anomaly_model.pkl salvat.")

# --- ETAPA 3: MONITORIZARE ACTIVA
print("\n--- ETAPA 3: MONITORIZARE ACTIVA (PROTECT MODE) ---")
time.sleep(1)
ser.reset_input_buffer()

history = []
# Initializam media cu ultima valoare din antrenare pentru a nu pleca de la 0
rolling_mean = sum([d[0] for d in date_antrenare]) / len(date_antrenare)

try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line: continue

            try:
                temp_acum = float(line)

                # Calculam media DOAR daca avem date in istoric, altfel ramane cea veche
                if len(history) > 0:
                    current_avg = sum(history) / len(history)
                else:
                    current_avg = rolling_mean

                # Predictie AI
                input_live = pd.DataFrame([[
                    temp_acum, 45.0, 80.0, current_avg, 0.1, 0
                ]], columns=df_train.columns)

                pred_ai = model_live.predict(input_live)[0]

                # LOGICA DE FIER:
                # Daca AI zice -1 SAU temperatura sare cu 1.5 grade peste media "curata"
                if (pred_ai == -1) or (temp_acum > current_avg + SENSIBILITATE_PRAG):
                    status = "ANOMALIE"
                    is_anomaly = 1
                    # NU adaugam in history. Blocam media la valoarea normala anterioara.
                else:
                    status = "NORMAL"
                    is_anomaly = 0
                    # Adaugam in history doar valorile bune
                    history.append(temp_acum)
                    if len(history) > BUFFER_SIZE:
                        history.pop(0)
                    rolling_mean = sum(history) / len(history)

                print(f"[{status}] Temp: {temp_acum} C | Prag: >{current_avg + SENSIBILITATE_PRAG:.2f} C")

                write_api.write(bucket=BUCKET, record=Point("iot")
                                .field("temp", temp_acum)
                                .field("anomaly", is_anomaly)
                                .field("mode", 1))

            except Exception:
                continue
        else:
            time.sleep(0.1)
except KeyboardInterrupt:
    print("\nOprit.")
finally:
    ser.close()
    client.close()