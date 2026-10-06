# Informe de Despliegue y Solución de API de Clasificación de Pinguinos (MLOps)

**Estudiante:** Luz Andrea Garcia Trujillo /Dierick Salvador Brochero Niebles /Diego Alexander Moreno Quintana 
**Rama de Desarrollo:** `taller001-desarrollo`  
**Repositorio:** `mlops-assignment`

---

## 1. Resumen Ejecutivo
Este informe detalla las correcciones de sintaxis, adecuaciones de esquemas de datos, contenerización y pruebas de inferencia realizadas 
para poner en marcha la API de clasificación de especies de pingüinos con FastAPI y Podman sobre el puerto `8989`.

---

## 2. Problemas Identificados y Soluciones Aplicadas

### A. Corrección de Errores en Código Python y Pydantic
* **Sintaxis y Rutas:** Se corrigieron incoherencias en las rutas de importación de módulos y la lectura de modelos serializados (`.pkl`).

* **Mapeo de Campos (Pydantic):** Se actualizó `modelo_de_datos.py` ajustando la clase `PenguinFeatures` con los nombres de atributos 
originales en inglés (`bill_length_mm`, `flipper_length_mm`, `island_Torgersen`, etc.) solicitados por los modelos de scikit-learn entrenados.

* **Integración con FastAPI:** Se ajustó `respuestas_y_estados.py` para construir un DataFrame directamente desde el objeto Pydantic enviado por el usuario mediante `dict(by_alias=True)`.

### B. Mapeo de Puertos y Contenerización con Podman
* **Aislamiento de Red:** Se configuró el contenedor `penguins_container` para exponer y mapear el puerto de la máquina virtual al puerto interno del servidor Uvicorn:
  ```bash
  podman run -d -p 8989:8989 --name penguins_container penguins-app:v1


## 3. Guía de Ejecución y Pruebas de Inferencia
* **Reconstruir e Iniciar Contenedor**
* ** Sintaxis **
Bash
podman build -t penguins-app:v1 .
podman run -d -p 8989:8989 --name penguins_container penguins-app:v1

* **Verificación de Endpoints**
##3.1 Estado de la API (GET /)

Bash
curl [http://127.0.0.1:8989/](http://127.0.0.1:8989/)
# Respuesta: {"message": "¡Hola, FastAPI está funcionando!"}

##3.2 Predicción por Defecto (POST /predict)

Bash
curl -X POST "[http://127.0.0.1:8989/predict](http://127.0.0.1:8989/predict)" \
     -H "Content-Type: application/json" \
     -d '{
       "Unnamed: 0": 0,
       "bill_length_mm": 39.1,
       "bill_depth_mm": 18.7,
       "flipper_length_mm": 181.0,
       "body_mass_g": 3750,
       "year": 2007,
       "island_Dream": 0,
       "island_Torgersen": 1,
       "sex_male": 1
     }'
# Respuesta: {"selected_model":"Decision Tree (Default)","predicted_species":"Adelie"}

## 3.3 Predicción Dinámica por Modelo - (POST /predict/decision_tree)

Bash
curl -X POST "[http://127.0.0.1:8989/predict/decision_tree](http://127.0.0.1:8989/predict/decision_tree)" \
     -H "Content-Type: application/json" \
     -d '{
       "Unnamed: 0": 0,
       "bill_length_mm": 39.1,
       "bill_depth_mm": 18.7,
       "flipper_length_mm": 181.0,
       "body_mass_g": 3750,
       "year": 2007,
       "island_Dream": 0,
       "island_Torgersen": 1,
       "sex_male": 1
     }'
# Respuesta: {"selected_model":"decision_tree","predicted_species":"Adelie"}

## 3.4 Artefactos Generados y Control de Versiones
Imagen Exportada: La imagen del contenedor fue serializada mediante:

Bash
podman save -o penguins_app_v1.tar localhost/penguins-app:v1
Git Ignore: Se añadió la regla *.tar a .gitignore para evitar superar el límite de tamaño de archivo por commit en GitHub (100 MB).

Control de Versiones:
Todos los cambios del código fuente fueron subidos exclusivamente a la rama independiente taller001-desarrollo.

