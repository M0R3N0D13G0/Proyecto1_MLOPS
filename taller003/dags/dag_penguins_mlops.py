from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
from sqlalchemy import create_engine
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import os

# Cadena de conexión hacia el servicio mysql_data
DB_URI = "mysql+pymysql://airflow_user:airflow_password@mysql_data:3306/penguins_db"

def borrar_contenido_bd():
    engine = create_engine(DB_URI)
    with engine.connect() as conn:
        conn.execute("DROP TABLE IF EXISTS raw_penguins;")
        conn.execute("DROP TABLE IF EXISTS clean_penguins;")
    print("Tablas anteriores borradas exitosamente de MySQL.")

def cargar_datos_penguins():
    url = "https://raw.githubusercontent.com/mcnamara-sk/penguins-dataset/master/penguins_raw.csv"
    df = pd.read_csv(url)
    engine = create_engine(DB_URI)
    df.to_sql('raw_penguins', con=engine, if_exists='replace', index=False)
    print(f"Cargados {len(df)} registros crudos a la base de datos.")

def preprocesar_datos():
    engine = create_engine(DB_URI)
    df = pd.read_sql("SELECT * FROM raw_penguins", con=engine)
    
    cols = ['Species', 'Culmen Length (mm)', 'Culmen Depth (mm)', 'Flipper Length (mm)', 'Body Mass (g)']
    df_clean = df[cols].dropna()
    df_clean.columns = ['species', 'culmen_length', 'culmen_depth', 'flipper_length', 'body_mass']
    
    le = LabelEncoder()
    df_clean['species'] = le.fit_transform(df_clean['species'])
    
    df_clean.to_sql('clean_penguins', con=engine, if_exists='replace', index=False)
    print("Preprocesamiento finalizado y almacenado en MySQL.")

def entrenar_modelo():
    engine = create_engine(DB_URI)
    df = pd.read_sql("SELECT * FROM clean_penguins", con=engine)
    
    X = df.drop(columns=['species'])
    y = df['species']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X_train, y_train)
    
    os.makedirs('/opt/airflow/plugins', exist_ok=True)
    model_path = '/opt/airflow/plugins/modelo_penguins.pkl'
    joblib.dump(clf, model_path)
    print(f"Modelo guardado en {model_path}.")

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=1)
}

with DAG(
    dag_id="dag_penguins_mlops",
    default_args=default_args,
    description="Pipeline Penguins MLOps con MySQL",
    schedule_interval="@once",
    catchup=False
) as dag:

    t1 = PythonOperator(task_id="1_borrar_bd", python_callable=borrar_contenido_bd)
    t2 = PythonOperator(task_id="2_cargar_datos_crudos", python_callable=cargar_datos_penguins)
    t3 = PythonOperator(task_id="3_preprocesar_datos", python_callable=preprocesar_datos)
    t4 = PythonOperator(task_id="4_entrenar_modelo", python_callable=entrenar_modelo)

    t1 >> t2 >> t3 >> t4
