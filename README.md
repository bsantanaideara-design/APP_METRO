# Metro de Madrid · Visor de Cuestionarios

Aplicación Flask con login de usuarios y control de acceso a informes Power BI.

---

## Instalación local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Copiar el logo al directorio static
#    (copia logo-vector-metro-madrid.webp como static/logo.webp)

# 3. Arrancar
python app.py
```

Abre http://localhost:5000

**Usuario por defecto:** `admin` / `admin123`  
*(¡Cámbialo desde el panel de administración!)*

---

## Despliegue en Render (gratis)

1. Sube este proyecto a un repositorio GitHub
2. Ve a https://render.com → New Web Service
3. Conecta tu repositorio
4. Configura:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
5. En **Environment Variables** añade:
   - `SECRET_KEY` → una cadena aleatoria larga (ej: `openssl rand -hex 32`)
6. Deploy

La URL quedará: `https://tu-app.onrender.com`

---

## URLs de acceso

```
# Visor con informe directo
https://tu-app.onrender.com/visor?tipo=CE&id=10334
https://tu-app.onrender.com/visor?tipo=CT&id=10052
https://tu-app.onrender.com/visor?tipo=LT&id=113
https://tu-app.onrender.com/visor?tipo=VIG&id=10334
https://tu-app.onrender.com/visor?tipo=CAC&id=10334

# Panel de administración (solo admin)
https://tu-app.onrender.com/admin
```

---

## Estructura del proyecto

```
metro_app/
├── app.py                  ← Servidor Flask
├── requirements.txt        ← Dependencias
├── Procfile                ← Para Render/Heroku
├── users.db                ← Base de datos (se crea sola)
├── static/
│   └── logo.webp           ← Logo Metro de Madrid
└── templates/
    ├── login.html          ← Pantalla de acceso
    ├── visor.html          ← Visor de informes
    └── admin.html          ← Panel de gestión de usuarios
```

---

## Seguridad

- Las contraseñas se guardan con **bcrypt** (hash seguro)
- Los `reportId` de Power BI **nunca salen al navegador**
- El servidor verifica permisos antes de generar la URL embed
- Sesiones con clave secreta configurable
