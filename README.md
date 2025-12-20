# Hopeir

## Create virtual environment

```
python3 -m venv venv
```

## Activate the environment

```
source ./venv/bin/activate
```

## Install packages via requirements.txt

```
pip install -r requirements.txt
```

## Start the server

```
cd Hopeir
uvicorn Hopeir.asgi:application --reload
```
