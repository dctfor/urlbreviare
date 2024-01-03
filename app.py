# app.py

# Required imports
from urllib.parse import urlparse
from collections.abc import Mapping
from functools import wraps

from flask import Flask, request, jsonify, render_template, Blueprint, url_for, session, abort, redirect
from flask_jwt import JWT, jwt_required, current_identity
from flask_cors import CORS
from firebase_admin import credentials, firestore, initialize_app

import os, logging, uuid, pathlib, requests, hmac, hashlib
import google.cloud.logging

#init logger
client = None
if os.getenv("firebase"):
    client = google.cloud.logging.Client()
    client.setup_logging()

lg = logging.getLogger(__name__)

#Define the FQDN or FULL URL such as
local_fqdn = os.getenv("fqdn") if os.getenv("fqdn") else "http://127.0.0.1/"

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret'

# Look forward the file in a secret related in Google Run
cred = credentials.Certificate(os.getenv("firebase")) if os.getenv("firebase") else credentials.Certificate('key.json')
default_app = initialize_app(cred)
db = firestore.client()

store_db = db.collection('store') 

def _validar_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def _agregar_https(url):
    if not url.startswith(('http://', 'https://')):
        return f'https://{url}'
    return url



@app.route("/<uuid>", methods=['GET'])
def find(uuid=None):
    todo = store_db.document(uuid).get().to_dict()
    if todo:
        print(todo['url'])
        # return jsonify(todo.to_dict()), 200
        return redirect(f"https://{todo['url']}")
    else:
        print('La URL no es válida')
        abort(404, description='La URL no es válida')


@app.route("/add", methods=['POST'])
def add():
    print(f"> URL : {request.json['url']}")
    if _validar_url(request.json['url']):
        url = _agregar_https(url)
        print(url)
    else:
        print('La URL no es válida')
        abort(400, description='La URL no es válida')
    id = str(uuid.uuid4())[:4]
    request.json['id'] = id
    store_db.document(id).set(request.json) 
    return jsonify(f"{local_fqdn}{id}"), 200

@app.route('/')
def index():
    return render_template('index.html')


#This is the error handling section
def page_not_found(e):
    lg.warn("running page_not_found")
    print("running page_not_found")
    '''
        page_not_found()... not sure why we got a request for a non existing url 
    '''
    return render_template('Error404.html'), 404

def server_error(e):
    lg.error("running server_error")
    print("running server_error")
    '''
        server_error()... ammm Houston, we have a problem here
    '''
    return render_template('Error500.html'), 500



#The magic happens here
port = int(os.environ.get('PORT', 8080))
if __name__ == '__main__':
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, server_error)
    cors = CORS(app, resources={r"*":{"origins":"*"}})
    app.run(threaded=True, host='0.0.0.0', port=port)