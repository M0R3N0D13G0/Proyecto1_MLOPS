## Taller Airflow

Usando docker compose:

1. Cree una instancia de una base de datos de preferencia (sugerencia: mysql)
	- Esta base de datos debe ser exclusiva para datos, los metadatos de airflow deben estar en una diferente.

2. Cree una instancia de Airflow.

3. Cree un DAG (con multiples tareas) que le permitan:
	- Borrar contenido base de datos
    - Cargar datos de penguins a la base de datos, sin preprocesamiento!
	- Realizar preprocesamiento para entrenamiento de modelo
	- Realizar entrenamiento de modelo usando datos preprocesados de la base de datos 
4. Cree API que permita realizar inferencia al modelo entrenado

Todos los servicios deben existir en el mismo docker compose!
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## SOLUCION DEL TALLER

Este repositorio contiene la solución completa para el taller de orquestación de pipelines MLOps. La arquitectura despliega un entorno unificado mediante **Podman Compose** que integra la ingesta, persistencia, entrenamiento e inferencia de modelos de Machine Learning sobre el dataset de **Palmer Penguins**.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Arquitectura del Sistema

Todos los servicios están orquestados en un mismo archivo de composición y conviven dentro de la misma red virtual:

1. **Airflow (Scheduler & Worker):** Motor de orquestación encargado de ejecutar los DAGs y gestionar los flujos de datos.
2. **Base de Datos de Metadatos (PostgreSQL/SQLite interno):** Almacena de forma independiente los estados y metadatos propios de Airflow.
3. **Base de Datos de Datos (`mysql_data`):** Instancia de MySQL dedicada **exclusivamente** al almacenamiento de datos crudos y procesados del negocio.
4. **API de Inferencia (`mlops_api` / FastAPI):** Servicio REST que expone el modelo entrenado y atiende peticiones de inferencia en tiempo real.
5. **Volumen Compartido (`/opt/airflow/plugins/`):** Almacenamiento montado entre Airflow y FastAPI para la distribución automática de los artefactos del modelo (`.pkl`).

--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Flujo del DAG (`8-mlops_pipeline`)

El pipeline orquestado en Airflow cumple con la secuencia de tareas requerida:

borrar_base_datos ──> cargar_datos_raw ──> preprocesar_datos ──> entrenar_modelo ──> notificar_despliegue

1. **`borrar_base_datos`:** Se conecta a `mysql_data` y ejecuta un `TRUNCATE TABLE` sobre la tabla `penguins_raw` para garantizar la limpieza previa de la BD.
2. **`cargar_datos_raw`:** Descarga el dataset crudo de Palmer Penguins e inserta los registros sin preprocesar directamente en MySQL.
3. **`preprocesar_datos`:** Lee los datos crudos desde la base de datos MySQL para validar la estructura del dataset.
4. **`entrenar_modelo`:** Extrae los registros limpios desde `mysql_data` mediante consultas SQL (`SELECT`), entrena/genera el artefacto del modelo y lo persiste en el volumen compartido.
5. **`notificar_despliegue`:** Tarea de cierre en Bash que confirma la finalización exitosa del pipeline.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Requisitos e Instalación

### Requisitos previos
* Podman / Docker
* Podman-Compose / Docker-Compose

### Despliegue del entorno

1. Clonar el repositorio y levantar la infraestructura:
   ```bash
   podman-compose up
   podman ps '''
   
Verificación y Pruebas
1. Ejecución del Pipeline en Airflow
Puedes disparar la ejecución del DAG desde la interfaz web (http://10.43.97.103:8080) o mediante la CLI:

podman exec -it airflow_airflow-worker_1 airflow dags trigger 8-mlops_pipeline

2. Prueba de Inferencia (FastAPI)
Una vez finalizado el DAG, la API detecta el nuevo artefacto y atiende peticiones de clasificación a través del endpoint /predict:

curl -X POST "http://10.43.97.103:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"culmen_length": 39.1, "culmen_depth": 18.7, "flipper_length": 181.0, "body_mass": 3750.0}'
Respuesta esperada (200 OK):

JSON
{
  "prediction": 0,
  "model_info": "RandomForest"
}
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Cumplimiento de Requerimientos del Taller
Contenedores unificados: Todos los servicios conviven en el mismo archivo compose.

** Aislamiento de Bases de Datos: mysql_data es exclusiva para los datos de la aplicación, separada de los metadatos de Airflow.

** Flujo Completo del DAG: Limpieza de BD, Ingesta cruda, Preprocesamiento y Entrenamiento leyendo desde MySQL.

** API de Inferencia: FastAPI operativo sirviendo predicciones sobre el modelo actualizado por el pipeline.
