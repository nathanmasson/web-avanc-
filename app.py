from flask import Flask, jsonify, request, abort, redirect, url_for
import peewee as p

import json
import datetime
import urllib.request

db = p.SqliteDatabase('commandes.db')
app = Flask("shopping")

class BaseModel(p.Model):
    class Meta:
        database = db

# URL du service de produits
url = 'http://dimprojetu.uqac.ca/%7Ejgnault/shops/products/'

# Fonction pour récupérer les produits et les enregistrer localement
def fetch_and_save_products():
    global products
    try:
        # Envoie de la requête pour récupérer les produits
        with urllib.request.urlopen(url) as response:
            data = response.read().decode('utf-8')  # Lecture des données de la réponse
            products = json.loads(data)  # Conversion des données JSON en un objet Python
            # Enregistrement des produits localement, par exemple dans un fichier JSON
            with open('products.json', 'w') as f:
                json.dump(products, f)
            print("Les produits ont été récupérés et enregistrés localement avec succès.")
    except urllib.error.URLError as e:
        print("Une erreur s'est produite lors de la récupération des produits:", e)

# Exécuter la fonction pour récupérer et enregistrer les produits localement
fetch_and_save_products()

@app.route("/")
def produits():
    return products

class Commande(BaseModel):
    id = p.AutoField(primary_key=True)
    quantity = p.IntegerField(default=0, null=False, constraints=[p.Check('quantity > 1')])

with app.app_context():
    db.connect()
    db.create_tables([Commande])

@app.route("/order", methods=['POST'])
def new_commande():
# Vérifier si la requête contient le type de contenu JSON
    if request.headers['Content-Type'] == 'application/json':
        # Récupérer les données JSON de la requête
        data = request.json

        # Vérifier si les champs nécessaires sont présents
        if 'product' not in data or 'id' not in data['product'] or 'quantity' not in data['product']:
            return jsonify({'error': 'missing-fields'}), 400

        # Récupérer l'identifiant du produit et la quantité
        product_id = data['product']['id']
        quantity = data['product']['quantity']

        # Vérifier si la quantité est valide
        if quantity < 1:
            return jsonify({'error': 'invalid-quantity'}), 400

        # Créer une nouvelle commande
        order = Commande.create(id=product_id, quantity=quantity)

        # Rediriger vers l'URL de la nouvelle commande avec le code 302
        return jsonify({'ca marche boloss'}), 200
    else:
        # Retourner une erreur si le type de contenu n'est pas pris en charge
        return jsonify({'error': 'unsupported-media-type'}), 415
    