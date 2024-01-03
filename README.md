# GCP_Flask_Firebase

This is a simple API CRUD in FLASK + Firebase Demo protecting the APIs with JWT

## The highlights are:
    - It was a quickly developed project/setup for showing base skills for developing
    - Currently only http errors such as 404 & 500 are handled with custom pages renders for this server
    - This repo is connected with a Trigger in Google Cloud Build for automatic deploy after pushing changes  and deployed in Google Run
    - Has the simple yet useful added logging configuration ofr showing logs in Google Cloud Run/Log Explorer
    - Google secrets are being used + Env Vars for keeping safe some secrets for connecting with Firebase
    - The interface is in another project using VUE

## Downside
    - Currently this lacks of any proper UI for managing the CRUD for a common final user here, it's mostly likely for a developer with min experience with Restful APIs

### TODO
    - Add example code for using Sendgrid by Twilio for validating emails validating format and validating 'A' and 'MX' DNS records
    - Add unittesting with pytest into the yaml file
    - Add Telegram realtime notifications
    - Add examples for APIs usage / flask-apispec other than the site-map
    - Add SSO/OAuth capabilities [WIP]
    - and other stuff

## Get hired

Last Update 2022 Aug 24