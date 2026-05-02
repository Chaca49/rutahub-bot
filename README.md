# RutaHub Bot 🚛

Bot de WhatsApp para conectar transportistas con cargas disponibles.

## Stack
- **FastAPI** — servidor web / webhook
- **Twilio** — WhatsApp API
- **PostgreSQL** — base de datos
- **Railway / Render** — hosting

---

## Setup local

### 1. Clonar e instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus credenciales de Twilio y PostgreSQL
```

### 3. Crear tablas en la base de datos
```bash
python scripts/create_tables.py
```

### 4. Cargar datos de prueba (opcional)
```bash
python scripts/seed_data.py
```

### 5. Levantar el servidor
```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Exponer el webhook local (para pruebas con Twilio)
```bash
ngrok http 8000
```
Copiar la URL de ngrok y configurarla en Twilio:
`https://xxxx.ngrok.io/webhook/whatsapp`

---

## Estructura del proyecto
```
rutahub/
├── app/
│   ├── main.py                  # Entry point FastAPI
│   ├── routers/
│   │   └── webhook.py           # Endpoint POST /webhook/whatsapp
│   ├── services/
│   │   ├── bot_service.py       # Máquina de estados del bot
│   │   ├── matching_service.py  # Lógica de matching cargas/viajes
│   │   └── twilio_service.py    # Envío de mensajes proactivos
│   ├── models/
│   │   └── models.py            # Modelos SQLAlchemy (Usuario, Carga, Viaje)
│   └── db/
│       └── database.py          # Conexión y sesión de BD
├── scripts/
│   ├── create_tables.py         # Crear tablas
│   └── seed_data.py             # Datos de prueba
├── requirements.txt
└── .env.example
```

---

## Flujos implementados

| Caso de Uso | Estado | Descripción |
|---|---|---|
| CU-01 | ✅ | Registro del transportista |
| CU-02 | ✅ | Consulta de cargas disponibles |
| CU-03 | ✅ | Publicación de viaje |
| CU-04 | ✅ | Matching automático (base) |
| CU-05 | 🔜 | Publicación de carga (pendiente) |
