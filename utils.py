import base64
import hashlib
import os
import random
import string


def generar_id_unico(longitud=8):
    """
    Genera un ID único de una longitud especificada.

    Args:
        longitud (int): La longitud del ID único a generar. Por defecto es 6.

    Returns:
        str: Un ID único compuesto de letras y dígitos.
    """
    caracteres = string.ascii_letters + string.digits
    return "".join(random.choices(caracteres, k=longitud))


def generar_id_unico_validado(longitud=8, store_db=None):
    """
    Genera un ID único y validado de una longitud especificada.

    Este método genera un ID aleatorio compuesto por letras y dígitos.
    Luego, verifica si el ID generado ya existe en la base de datos proporcionada.
    Si el ID no existe, lo retorna como resultado.

    Args:
        longitud (int): La longitud del ID a generar. Por defecto es 6.
        store_db: La base de datos donde se verificará la existencia del ID.
                  Debe ser un objeto que tenga un método `document(id).get().exists`.

    Returns:
        str: Un ID único que no existe en la base de datos proporcionada.
    """
    caracteres = string.ascii_letters + string.digits
    while True:
        id = "".join(random.choices(caracteres, k=longitud))
        if not store_db.document(id).get().exists:
            return id


def generar_id_con_hash_validado(url, longitud=8, store_db=None):
    """
    Genera un ID único basado en un hash de la URL.
    """
    salt = os.urandom(16)  # Genera un salt aleatorio
    hash_obj = hashlib.sha256(salt + url.encode())
    hash_digest = hash_obj.digest()
    # Codificar en base62 o base64 y truncar
    id = base64.urlsafe_b64encode(hash_digest).decode("utf-8").rstrip("=")[:longitud]
    if not store_db.document(id).get().exists:
        return id
    else:
        return generar_id_unico(longitud)  # Fallback a generación aleatoria
