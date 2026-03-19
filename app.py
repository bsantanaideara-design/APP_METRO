from flask import Flask, render_template, request, session, redirect, url_for, abort
import sqlite3
import bcrypt
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cambia-esta-clave-en-produccion')

DB = 'users.db'

# ── Configuración de informes (los reportId nunca llegan al navegador) ──
REPORTS = {
    'CE':  {
        'label':    'CE – Cliente Externo',
        'reportId': '745f3223-0df8-4943-a0bd-0b61d43c1916',
        'groupId':  '83b96d00-0bbf-44ba-8c8a-0931bd9993d0',
        'table':    'LE_CE_Datos',
        'field':    'TITULO',
    },
    'CT':  {
        'label':    'CT – Coches de Tren',
        'reportId': '63c4d082-a5ce-4db2-8576-afd7af0968a3',
        'groupId':  '83b96d00-0bbf-44ba-8c8a-0931bd9993d0',
        'table':    'CT',
        'field':    'TITULO',
    },
    'LT':  {
        'label':    'LT – Línea de Tren',
        'reportId': '40919cd6-ac26-4077-828f-d2dc850bc8c5',
        'groupId':  '83b96d00-0bbf-44ba-8c8a-0931bd9993d0',
        'table':    'LT',
        'field':    'Título',
    },
    'VIG': {
        'label':    'VIG – Vigilancia',
        'reportId': '2ff905d4-9850-41f1-bb3b-ae98b5eedd73',
        'groupId':  '83b96d00-0bbf-44ba-8c8a-0931bd9993d0',
        'table':    'VIG_SinAgrupar',
        'field':    'TITULO',
    },
    'CAC': {
        'label':    'CAC – Cliente Misterioso',
        'reportId': '8262b3c7-8ea0-481c-9796-9e33fa019b30',
        'groupId':  '83b96d00-0bbf-44ba-8c8a-0931bd9993d0',
        'table':    'CAC',
        'field':    'CLAVEID',
    },
}


# ── Base de datos ──
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea la tabla de usuarios si no existe y añade un admin por defecto."""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario    TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                informes   TEXT NOT NULL,
                activo     INTEGER DEFAULT 1
            )
        ''')
        # Crear admin por defecto si no existe
        existing = conn.execute("SELECT id FROM users WHERE usuario='admin'").fetchone()
        if not existing:
            pwd_hash = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (usuario, password, informes) VALUES (?, ?, ?)",
                ('admin', pwd_hash, 'CE,CT,LT,VIG,CAC')
            )
        conn.commit()


# ── Rutas ──
@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('visor'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        try:
            usuario = request.form.get('usuario', '').strip()
            password = request.form.get('password', '').encode()

            with get_db() as conn:
                row = conn.execute(
                    "SELECT password, informes, activo FROM users WHERE usuario=?",
                    (usuario,)
                ).fetchone()

            if row and row['activo'] and bcrypt.checkpw(password, row['password'].encode()):
                session['usuario'] = usuario
                session['informes'] = row['informes'].split(',')
                next_url = request.args.get('next')
                return redirect(next_url or url_for('visor'))
            else:
                error = 'Usuario o contraseña incorrectos.'
        except Exception as e:
            app.logger.error(f'Error en login: {e}', exc_info=True)
            error = f'Error interno: {str(e)}'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/visor')
def visor():
    if 'usuario' not in session:
        return redirect(url_for('login', next=request.url))

    tipo = request.args.get('tipo', '').upper()
    id_  = request.args.get('id', '').strip()

    if not tipo or not id_:
        return render_template('visor.html',
                               usuario=session['usuario'],
                               informes_permitidos=session['informes'],
                               error='Faltan parámetros tipo e id en la URL.')

    if tipo not in REPORTS:
        abort(404)

    if tipo not in session['informes']:
        abort(403)

    cfg = REPORTS[tipo]
    filter_str = cfg['table'] + '/' + cfg['field'] + " eq '" + id_ + "'"
    encoded_filter = filter_str.replace(' ', '%20').replace('/', '%2F').replace("'", '%27')
    embed_url = (
        "https://app.powerbi.com/reportEmbed"
        "?filter=" + encoded_filter +
        "&reportId=" + cfg['reportId'] +
        "&groupId=" + cfg['groupId'] +
        "&autoAuth=true"
        "&filterPaneEnabled=false"
        "&navContentPaneEnabled=false"
    )

    return render_template('visor.html',
                           usuario=session['usuario'],
                           informes_permitidos=session['informes'],
                           tipo=tipo,
                           id_=id_,
                           label=cfg['label'],
                           embed_url=embed_url)


# ── Panel de administración ──
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        with get_db() as conn:
            row = conn.execute(
                "SELECT informes FROM users WHERE usuario=?",
                (session['usuario'],)
            ).fetchone()
        # Solo admin tiene acceso a todos los informes
        if not row or 'CE,CT,LT,VIG,CAC' not in row['informes']:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@app.route('/admin')
@admin_required
def admin():
    with get_db() as conn:
        users = conn.execute("SELECT id, usuario, informes, activo FROM users").fetchall()
    return render_template('admin.html',
                           users=users,
                           todos_informes=list(REPORTS.keys()),
                           usuario=session['usuario'])


@app.route('/admin/nuevo', methods=['POST'])
@admin_required
def admin_nuevo():
    usuario  = request.form.get('usuario', '').strip()
    password = request.form.get('password', '').encode()
    informes = ','.join(request.form.getlist('informes'))

    if not usuario or not password or not informes:
        return redirect(url_for('admin'))

    pwd_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode()
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (usuario, password, informes) VALUES (?, ?, ?)",
                (usuario, pwd_hash, informes)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        pass  # Usuario ya existe

    return redirect(url_for('admin'))


@app.route('/admin/editar/<int:user_id>', methods=['POST'])
@admin_required
def admin_editar(user_id):
    informes = ','.join(request.form.getlist('informes'))
    activo   = 1 if request.form.get('activo') else 0
    password = request.form.get('password', '').encode()

    with get_db() as conn:
        if password:
            pwd_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode()
            conn.execute(
                "UPDATE users SET informes=?, activo=?, password=? WHERE id=?",
                (informes, activo, pwd_hash, user_id)
            )
        else:
            conn.execute(
                "UPDATE users SET informes=?, activo=? WHERE id=?",
                (informes, activo, user_id)
            )
        conn.commit()

    return redirect(url_for('admin'))


@app.route('/admin/eliminar/<int:user_id>', methods=['POST'])
@admin_required
def admin_eliminar(user_id):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
    return redirect(url_for('admin'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
