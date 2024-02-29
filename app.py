from flask import Flask, jsonify, request, abort, redirect, url_for
import peewee as p

import json
import datetime
import requests

db = p.SqliteDatabase('products.db')
app = Flask("shopping")

# Fonction pour récupérer et stocker les données des produits
def fetch_and_store_products_data():
    global products_data
    # Effectuer une requête pour récupérer la liste complète des produits
    response = requests.get('http://dimprojetu.uqac.ca/%7Ejgnault/shops/products/')
    if response.status_code == 200:
        products_data = response.json()
        # Vous pouvez ensuite persister les données localement, par exemple dans un fichier JSON
        with open('products.json', 'w') as f:
            json.dump(products_data, f)
    else:
        # Gérer les erreurs de récupération des données des produits
        print("Erreur lors de la récupération des données des produits:", response.status_code)

# Liste pour stocker les informations des produits
products_data = None

# Récupérer et stocker les données des produits au démarrage de l'application
fetch_and_store_products_data()

@app.route("/")
def coucou():
    return products_data