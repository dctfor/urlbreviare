import logging
import os
import uuid
from io import BytesIO
from urllib.parse import urlparse

import qrcode
import requests
from firebase_admin import credentials, firestore, initialize_app
from flask import Flask, abort, jsonify, redirect, render_template, request, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_talisman import Talisman
from flask_wtf import CSRFProtect
from flask_wtf.csrf import ValidationError
from marshmallow import Schema, fields
from werkzeug.security import check_password_hash, generate_password_hash

from config import DevelopmentConfig, ProductionConfig
from error_handlers import page_not_found, server_error
from utils import generar_id_con_hash_validado

MAX_URL_LENGTH = int(os.getenv("MAX_URL_LENGTH", 2048))
PORT = int(os.getenv("PORT", 8080))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

env = os.getenv("FLASK_ENV", "development")

if env == "production":
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Enable CORS
# TODO: Improve security by specifying the allowed origins;
#       CORS(app, resources={r"/add": {"origins": "https://tudominio.com"}})
CORS(app, resources={r"*": {"origins": "*"}})

# Initialize Firebase
firebase_cred = os.getenv("firebase") or "key.json"
cred = credentials.Certificate(firebase_cred)
default_app = initialize_app(cred)
db = firestore.client()
store_db = db.collection("store")

# Define the FQDN or FULL URL
local_fqdn = os.getenv("fqdn") or f"http://127.0.0.1:{PORT}/"


# Configuración de Flask-Limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["100 per day", "100 per hour"],  # Ajusta según tus necesidades
)

# Inicializar CSRFProtect
csrf = CSRFProtect(app)

# Configurar Talisman para agregar cabeceras de seguridad
csp = {
    "default-src": [
        "'self'",
    ],
    "script-src": [
        "'self'",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
    ],
    "style-src": [
        "'self'",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
        "'unsafe-inline'",  # Necessary if you include inline styles or styles from JS libraries
    ],
    "font-src": [
        "'self'",
        "https://cdn.jsdelivr.net",
    ],
    "img-src": [
        "'self'",
        "data:",
    ],
}


# Inicializar Flask-Talisman con la configuración CSP y habilitar nonces para scripts
talisman = Talisman(
    app,
    content_security_policy=csp,
    content_security_policy_nonce_in=["script-src"],
)


class URLSchema(Schema):
    url = fields.Url(
        required=True,
        error_messages={
            "required": "La URL es obligatoria",
            "invalid": "La URL proporcionada no es válida",
        },
    )


url_schema = URLSchema()


# Inicializar LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Ruta a la que se redirige para iniciar sesión
login_manager.login_message_category = "debug"


# Modelo de Usuario (ejemplo básico)
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id  # ID único (puede ser UUID)
        self.username = username
        self.password_hash = password_hash

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


# Cargar usuarios (ejemplo simple)
@login_manager.user_loader
def load_user(user_id):
    """
    Carga el usuario desde Firestore usando el ID.
    """
    user_doc = db.collection("users").document(user_id).get()
    if user_doc.exists:
        data = user_doc.to_dict()
        return User(id=user_id, username=data["username"], password_hash=data["password_hash"])
    return None


def crear_usuario(username, password):
    """
    Crea un nuevo usuario con un nombre de usuario y contraseña.
    """
    # Verificar si el usuario ya existe
    users_ref = db.collection("users")
    query = users_ref.where("username", "==", username).get()
    if query:
        return False, "El nombre de usuario ya existe."

    # Generar un ID único
    user_id = str(uuid.uuid4())

    # Hashear la contraseña
    password_hash = generate_password_hash(password)

    # Crear el documento de usuario
    users_ref.document(user_id).set({"username": username, "password_hash": password_hash})

    return True, user_id


def obtener_usuario_por_username(username):
    """
    Obtiene un usuario desde Firestore por nombre de usuario.
    """
    users_ref = db.collection("users")
    query = users_ref.where("username", "==", username).get()
    if query:
        doc = query[0]
        data = doc.to_dict()
        return User(id=doc.id, username=data["username"], password_hash=data["password_hash"])
    return None


def obtener_usuario_por_id(user_id):
    """
    Obtiene un usuario desde Firestore por ID.
    """
    user_doc = db.collection("users").document(user_id).get()
    if user_doc.exists:
        data = user_doc.to_dict()
        return User(id=user_id, username=data["username"], password_hash=data["password_hash"])
    return None


def actualizar_usuario(user_id, username=None, password=None):
    """
    Actualiza el nombre de usuario y/o contraseña de un usuario existente.
    """
    user_ref = db.collection("users").document(user_id)
    if not user_ref.get().exists:
        return False, "Usuario no encontrado."

    update_data = {}
    if username:
        # Verificar si el nuevo nombre de usuario ya existe
        query = db.collection("users").where("username", "==", username).get()
        if query:
            return False, "El nombre de usuario ya existe."
        update_data["username"] = username
    if password:
        update_data["password_hash"] = generate_password_hash(password)

    user_ref.update(update_data)
    return True, "Usuario actualizado exitosamente."


def eliminar_usuario(user_id):
    """
    Elimina un usuario de Firestore por ID.
    """
    user_ref = db.collection("users").document(user_id)
    if not user_ref.get().exists:
        return False, "Usuario no encontrado."

    user_ref.delete()
    return True, "Usuario eliminado exitosamente."


# @app.before_request
# def csrf_protect():
#     print(request.method)
#     print(request.headers)
#     print(request.get_json())
#     if request.method == "POST":
#         csrf_token = request.headers.get('X-CSRFToken') or request.get_json().get('X-CSRFToken')
#         if not csrf_token:
#             abort(400, description='El token CSRF está ausente.')
#         try:
#             validate_csrf(csrf_token)
#         except ValidationError:
#             abort(400, description='Token CSRF inválido.')


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Ruta para iniciar sesión.
    """
    print(f"login - {request.method}")
    if request.method == "POST":
        # data = request.get_json()
        username = request.form.get("username") or request.get_json().get("username")
        password = request.form.get("password") or request.get_json().get("password")
        print(f"username: {username}, password: {password}")
        if not username or not password:
            return (
                jsonify({"message": "Nombre de usuario y contraseña son requeridos."}),
                400,
            )

        user = obtener_usuario_por_username(username)
        print(user.verify_password(password))
        if user and user.verify_password(password):
            login_user(user)
            print("render index - redirecting")
            return jsonify({"message": "Login exitoso"}), 200
        else:
            return (
                jsonify({"message": "Nombre de usuario o contraseña incorrectos."}),
                401,
            )
    print("render login ... ?")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """
    Ruta para cerrar sesión.
    """
    logout_user()
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    """
    Ruta para registrar un nuevo usuario.
    """
    if request.method == "POST":
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify({"message": "Nombre de usuario y contraseña son requeridos."}),
                400,
            )

        success, result = crear_usuario(username, password)
        if success:
            return jsonify({"message": "Usuario registrado exitosamente."}), 201
        else:
            return jsonify({"message": result}), 400

    return render_template("register.html")


@app.route("/admin/users", methods=["GET"])
@login_required
def listar_usuarios():
    """
    Lista todos los usuarios. Solo accesible para usuarios autenticados.
    """
    users_ref = db.collection("users").get()
    usuarios = []
    for user_doc in users_ref:
        data = user_doc.to_dict()
        usuarios.append({"id": user_doc.id, "username": data["username"]})
    return jsonify({"users": usuarios}), 200


@app.route("/admin/users/<user_id>", methods=["GET"])
@login_required
def obtener_usuario(user_id):
    """
    Obtiene los detalles de un usuario específico.
    """
    user = obtener_usuario_por_id(user_id)
    if user:
        return jsonify({"id": user.id, "username": user.username}), 200
    else:
        return jsonify({"message": "Usuario no encontrado."}), 404


@app.route("/admin/users", methods=["POST"])
@login_required
def crear_usuario_admin():
    """
    Crea un nuevo usuario. Solo accesible para usuarios autenticados.
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return (
            jsonify({"message": "Nombre de usuario y contraseña son requeridos."}),
            400,
        )

    success, result = crear_usuario(username, password)
    if success:
        return (
            jsonify({"message": "Usuario creado exitosamente.", "user_id": result}),
            201,
        )
    else:
        return jsonify({"message": result}), 400


@app.route("/admin/users/<user_id>", methods=["PUT"])
@login_required
def actualizar_usuario_admin(user_id):
    """
    Actualiza un usuario existente. Solo accesible para usuarios autenticados.
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    success, result = actualizar_usuario(user_id, username=username, password=password)
    if success:
        return jsonify({"message": result}), 200
    else:
        return jsonify({"message": result}), 400


@app.route("/admin/users/<user_id>", methods=["DELETE"])
@login_required
def eliminar_usuario_admin(user_id):
    """
    Elimina un usuario existente. Solo accesible para usuarios autenticados.
    """
    success, result = eliminar_usuario(user_id)
    if success:
        return jsonify({"message": result}), 200
    else:
        return jsonify({"message": result}), 400


@app.route("/<uuid>", methods=["GET"])
def find(uuid=None):
    """
    Retrieve a document from the database using a UUID and redirect to the stored URL.

    Args:
        uuid (str): The UUID of the document to retrieve.

    Returns:
        Response: A redirect response to the URL stored in the document if found.
        If the document is not found, a 404 error is raised with a description.

    Raises:
        404: If the document with the given UUID is not found in the database.
    """
    todo = store_db.document(uuid).get().to_dict()
    if todo:
        return redirect(f"{todo['url']}")
    else:
        abort(404, description="La URL no es válida")


@app.route("/add", methods=["POST"])
@login_required
@limiter.limit("100 per day")  # Limita a 10 solicitudes por día
def add():
    """
    Handles the addition of a new URL.

    Endpoint: /add
    Method: POST

    Request JSON Parameters:
    - url (str): The URL to be shortened.

    Response:
    - 200 OK: Returns the shortened URL.
    - 400 Bad Request: If the provided URL is not valid.

    The function performs the following steps:
    1. Retrieves the 'url' from the request JSON.
    2. Validates the URL using the `_validar_url` function.
    3. If valid, ensures the URL starts with 'https://' using the `_agregar_https` function.
    4. Generates a unique 4-character ID.
    5. Adds the ID to the request JSON.
    6. Stores the request JSON in the database with the generated ID.
    7. Returns the shortened URL.

    If the URL is not valid, it aborts the request with a 400 status code and an appropriate error message.
    """
    try:
        data = request.get_json()
        validated_data = url_schema.load(data)
        url = validated_data["url"]
        _validar_url(url)  # Esta función ahora lanza una excepción si la URL es inválida
        # url = _agregar_https(url) # No es necesario agregar 'https://' a la URL
        unique_id = generar_id_con_hash_validado(url, store_db=store_db)
        data["id"] = unique_id
        store_db.document(unique_id).set(data)
        shortened_url = f"{local_fqdn}{unique_id}"
        qr_url = f"{local_fqdn}qr/{unique_id}"  # URL para acceder al código QR

        return jsonify({"shortened_url": shortened_url, "qr_url": qr_url}), 200
    except ValidationError as ve:
        return jsonify({"message": ve.messages}), 400
    except Exception as e:
        logging.error(f"Error en /add: {e}")
        abort(500, description="Error interno del servidor")


@app.route("/")
def index():
    if request.method == "POST":
        print("POST")
    return render_template("index.html", nonce=os.urandom(16).hex())


def _validar_url(url):
    """
    Validate if the given URL has a scheme, a network location, and other common URL components.

    Args:
        url (str): The URL to validate.

    Returns:
        bool: True if the URL passes all validations, False otherwise.
    """
    if not url:
        abort(400, description="La URL está vacía")

    if len(url) > MAX_URL_LENGTH:
        abort(
            400,
            description=f"La URL excede la longitud máxima permitida de {MAX_URL_LENGTH} caracteres",
        )

    parsed_url = urlparse(url)

    if not (parsed_url.scheme and parsed_url.netloc):
        abort(
            400,
            description="La URL debe contener un esquema (http o https) y un dominio válido",
        )

    if parsed_url.scheme not in ["http", "https"]:
        abort(400, description="La URL debe usar los esquemas HTTP o HTTPS")

    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        if response.status_code >= 400:
            abort(400, description="La URL no es accesible o retorna un error")
        return True
    except requests.RequestException:
        abort(400, description="La URL no es válida o no se puede acceder a ella")


def _agregar_https(url):
    """
    Adds 'https://' to the beginning of a URL if it does not already start with 'http://' or 'https://'.

    Args:
        url (str): The URL to be checked and potentially modified.

    Returns:
        str: The modified URL with 'https://' added if necessary.
    """
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def generar_qr(url, size=512):
    """
    Genera un código QR en formato WebP para la URL proporcionada.

    Args:
        url (str): La URL para la cual se generará el código QR.
        size (int, optional): Tamaño de la imagen en píxeles. Por defecto es 512.

    Returns:
        BytesIO: Objeto en memoria que contiene la imagen WebP.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size, size))

    img_io = BytesIO()
    img.save(img_io, "WEBP", quality=100)
    img_io.seek(0)
    return img_io


@app.route("/qr/<uuid>", methods=["GET"])
def obtener_qr(uuid):
    """
    Genera y devuelve un código QR en formato WebP para la URL acortada correspondiente al UUID proporcionado.

    Args:
        uuid (str): El identificador único de la URL acortada.

    Returns:
        Response: Imagen del código QR en formato WebP.
    """
    try:
        # Recuperar el documento desde Firestore
        todo = store_db.document(uuid).get().to_dict()
        if not todo or "url" not in todo:
            abort(404, description="La URL no es válida")

        # Construir la URL acortada
        shortened_url = f"{local_fqdn}{uuid}"

        # Generar el código QR
        qr_image = generar_qr(shortened_url)

        return send_file(
            qr_image,
            mimetype="image/webp",
            as_attachment=False,
            download_name=f"{uuid}.webp",
        )
    except Exception as e:
        logging.error(f"Error en /qr/<uuid>: {e}")
        abort(500, description="Error interno del servidor")


if __name__ == "__main__":
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, server_error)
    app.run(threaded=True, host="0.0.0.0", port=PORT)
