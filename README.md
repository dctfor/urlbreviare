# UrlBreviare

This is a simple API CRUD in FLASK + Firebase Demo

## The highlights are:
    - It was a quickly developed project/setup for showing base skills for developing
    - Currently only http errors such as 404 & 500 are handled with custom pages renders for this server
    - This repo used to be connected with a Trigger in Google Cloud Build for automatic deploy after pushing changes and deployed in Google Run
    - Has the simple yet useful added logging configuration ofr showing logs in Google Cloud Run/Log Explorer
    - Google secrets are being used + Env Vars for keeping safe some secrets for connecting with Firebase
    - The interface was intended to be in another project using VUE, but for improving this current project is included
    - The project implements different Flask plugins as Talisman, Login and Limiter
    - The generated short URL comes now with a QR created with pillow

## Pending ideas
    Currently I'm not implementing JWT as currently for being such a small project, this can work using Flask-login + CSRF Tokens
    No need for a more complex implementation for this demo.

### TODOs
    - Add example code for using Sendgrid by Twilio for validating emails validating format and validating 'A' and 'MX' DNS records
    - Add unittesting with pytest into the yaml file
    - Add Telegram realtime notifications
    - Add examples for APIs usage / flask-apispec other than the site-map
    - Add SSO/OAuth capabilities


# Desarrollo

## Configuración del Entorno

1. **Crear y Activar un Entorno Virtual:**
    ```bash
    python -m venv env
    source env/bin/activate  # En Windows: env\Scripts\activate
    ```

    ```bash
    pip install -r requirements.txt
    ```

    ```bash
    pre-commit install
    ```
