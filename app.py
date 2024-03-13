from flask import Flask, jsonify, request, abort, redirect, url_for
import peewee as p

import json
import datetime
import urllib.request
from playhouse.shortcuts import model_to_dict, dict_to_model

db = p.SqliteDatabase('commandes.db')
app = Flask("shopping")

class BaseModel(p.Model):
    class Meta:
        database = db

class Produits(BaseModel):
    id = p.IntegerField()
    description = p.TextField()
    height = p.IntegerField()
    image = p.CharField()
    stock = p.BooleanField()
    name = p.CharField()
    price = p.FloatField()
    type = p.CharField()
    weight = p.IntegerField()

class Commande(BaseModel):
    id = p.AutoField(primary_key=True)
    quantity = p.IntegerField(default=0, null=False, constraints=[p.Check('quantity > 1')])

with app.app_context():
    db.connect()
    db.create_tables([Commande, Produits])

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
            # Supprimer les anciens produits de la base de données
            Produits.delete().execute()
            # Enregistrer les nouveaux produits dans la base de données
            for product in products["products"]:
                Produits.create(
                    id=product['id'],
                    description=product['description'],
                    height=product['height'],
                    image=product['image'],
                    stock=product['in_stock'],
                    name=product['name'],
                    price=product['price'],
                    type=product['type'],
                    weight=product['weight']
                )
            print("Les produits ont été récupérés et enregistrés localement avec succès.")
    except urllib.error.URLError as e:
        print("Une erreur s'est produite lors de la récupération des produits:", e)

# Exécuter la fonction pour récupérer et enregistrer les produits localement
fetch_and_save_products()

@app.route("/")
def produits():
    produits = []
    for produit in Produits.select():
        produits.append(model_to_dict(produit))

    return jsonify(produits)

@app.route("/order", methods=['POST'])
def new_commande():
    if not request.is_json:
        return abort(400)
    
    # Récupérer les données JSON de la requête
    data = request.json

    # Vérifier si les champs nécessaires sont présents
    if 'product' not in data or 'id' not in data['product'] or 'quantity' not in data['product']:
        return jsonify({'errors': {'product':{'code' : 'missing-fields', 'name' : 'La création d\'une commande nécessite un produit'}}}), 422

    # Récupérer l'identifiant du produit et la quantité
    product_id = data['product']['id']
    quantity = data['product']['quantity']

    # Vérifier si la quantité est valide
    if quantity < 1:
        return jsonify({'error': 'invalid-quantity'}), 400

    # Créer une nouvelle commande
    order = Commande.create(id=product_id, quantity=quantity)

    try:
        order.save()
    except p.IntegrityError:
        return jsonify({
        "error": "Un compte avec le même propriétaire existe déjà"
    }), 422

    product = Produits.get_or_none(Produits.id == product_id)
    if not product or not product.stock:
        return jsonify({
            'errors': {
                'product': {
                    'code': 'out-of-inventory',
                    'name': "Le produit demandé n'est pas en inventaire"
                }
            }
        }), 422
    
    # Rediriger vers l'URL de la nouvelle commande avec le code 302
    return redirect(url_for("get_order", order_id=order.id, _method='GET'))
    

@app.route('/order/<int:order_id>', methods=['GET'])
def get_order(order_id):
    # Récupérer la commande de la base de données par son identifiant
    order = Commande.get_or_none(Commande.id == order_id)
    if order:
        # Retourner les détails de la commande au format JSON
        return jsonify({'id': order.id, 'quantity': order.quantity})
    else:
        # Retourner une erreur si la commande n'est pas trouvée
        return jsonify({'error': 'order-not-found'}), 404