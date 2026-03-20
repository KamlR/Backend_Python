# этот файл можно запускать отдельно через python model.py, если нужно пройти train этап модели.

import os
import pickle
import numpy as np
import mlflow
import mlflow.sklearn

from sklearn.linear_model import LogisticRegression


MODEL_PATH = os.getenv("MODEL_PATH", "model.pkl")
USE_MLFLOW = os.getenv("USE_MLFLOW", "false").lower() == "true"

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "moderation-model")
MLFLOW_MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "moderation-model")
MLFLOW_MODEL_STAGE = os.getenv("MLFLOW_MODEL_STAGE", "local")


def train_model():
    """Обучает простую модель на синтетических данных."""
    np.random.seed(42)

    # Признаки: [is_verified_seller, images_qty, description_length, category]
    X = np.random.rand(1000, 4)

    # Целевая переменная: 1 = нарушение, 0 = нет нарушения
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
    y = y.astype(int)

    model = LogisticRegression()
    model.fit(X, y)
    return model


def save_model(model, path=MODEL_PATH):
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model(path=MODEL_PATH):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def configure_mlflow():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)


def train_and_register_model():
    """
    Обучает модель, логирует ее в MLflow и регистрирует в Model Registry.
    """
    configure_mlflow()

    model = train_model()

    with mlflow.start_run():
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=MLFLOW_MODEL_NAME,
        )

    return model


def load_model_from_mlflow(model_name: str = MLFLOW_MODEL_NAME, stage: str = MLFLOW_MODEL_STAGE):
    """
    Загружает модель из MLflow Model Registry по stage.
    """
    configure_mlflow()
    model_uri = f"models:/{model_name}/{stage}"
    return mlflow.sklearn.load_model(model_uri)


def get_model():
    """
    Единая точка загрузки модели:
    - из MLflow, если USE_MLFLOW=true
    - из локального файла, если USE_MLFLOW=false
    """
    if USE_MLFLOW:
        return load_model_from_mlflow()
    return load_model()


if __name__ == "__main__":
    if USE_MLFLOW:
        print("🚀 Training model and registering in MLflow...")
        train_and_register_model()
        print("✅ Model trained and registered in MLflow")
    else:
        print("🚀 Training model and saving locally...")
        model = train_model()
        save_model(model)
        print(f"✅ Model trained and saved to {MODEL_PATH}")