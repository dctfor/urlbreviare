import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    FQDN = os.getenv('FQDN', 'http://127.0.0.1/')
    FIREBASE_CRED = os.getenv("FIREBASE_CRED", 'key.json')

class ProductionConfig(Config):
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True