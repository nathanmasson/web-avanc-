from flask import Flask, jsonify, request, abort, redirect, url_for
import peewee as p

import json
import datetime
import urllib.request
from urllib.parse import urlencode
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
    total_price = p.FloatField(null=True)
    id_produit = p.IntegerField()
    quantity = p.IntegerField(default=0, null=False, constraints=[p.Check('quantity > 1')])
    email = p.CharField(null=True)
    credit_card = p.TextField(null=True)
    paid = p.BooleanField(default=False)
    shipping_price = p.FloatField(null=True)

class Shipping(BaseModel):
    id = p.AutoField(primary_key=True)
    country = p.CharField(null=True)
    adress = p.CharField(null=True)
    postal_code = p.CharField(null=True)
    city = p.CharField(null=True)
    province = p.CharField(null=True)
    commande = p.ForeignKeyField(Commande, backref='shipping', null=True)

class Card(BaseModel):
    id = p.AutoField()
    name = p.CharField()
    first_digits = p.CharField()
    last_digits = p.CharField()
    expiration_year = p.IntegerField()
    expiration_month = p.IntegerField()
    commande = p.ForeignKeyField(Commande, backref='card', null=True)
    

class Transactions(BaseModel):
    id = p.CharField()
    success = p.BooleanField()
    amount_charged = p.FloatField()
    commande = p.ForeignKeyField(Commande, backref='transactions', null=True)


with app.app_context():
    db.connect()
    db.create_tables([Commande, Produits, Shipping, Card, Transactions])

# URL du service de produits
url_produits = 'http://dimprojetu.uqac.ca/%7Ejgnault/shops/products/'

# Fonction pour récupérer les produits et les enregistrer localement
def fetch_and_save_products():
    global products
    try:
        # Envoie de la requête pour récupérer les produits
        with urllib.request.urlopen(url_produits) as response:
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
    
    product = Produits.get_or_none(Produits.id == product_id)
    if not product or not product.stock:
        return jsonify({
            'errors': {
                'product': {
                    'code': 'out-of-inventory',
                    'name': "Le produit demandé n'est pas en stock"
                }
            }
        }), 422
    
    total_price = quantity * product.price

    total_poids = quantity * product.weight

    if total_poids <= 500:
        frais_expedition = 5
    elif 500 < total_poids <= 2000:
        frais_expedition = 10
    else:
        frais_expedition = 25

    shipping_price = total_price + frais_expedition


    # Créer une nouvelle commande
    order = Commande.create(id_produit=product_id, quantity=quantity, total_price=total_price, shipping_price = shipping_price)



    try:
        order.save()
    except p.IntegrityError:
        return jsonify({
        "error": "Un compte avec le même propriétaire existe déjà"
    }), 422
    

    # Rediriger vers l'URL de la nouvelle commande avec le code 302
    return redirect(url_for("get_order", order_id=order.id, _method='GET'))
    

@app.route('/order/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = Commande.get_or_none(order_id)
    if order is None:
        return abort(404)
    
    order_data = model_to_dict(order)
    order_data['shipping_information'] = [model_to_dict(shipping) for shipping in order.shipping]
    order_data['credit_card'] = [model_to_dict(card) for card in order.card]
    order_data['transactions'] = [model_to_dict(transaction) for transaction in order.transactions]

    return jsonify(order_data)
    

@app.route('/order/<int:order_id>', methods=['PUT'])
def ajout_infos(order_id):
    data = request.json
    #Vérifier si les champs nécessaires sont présents

 # Récupérer la commande de la base de données par son identifiant
    order = Commande.get_or_none(Commande.id == order_id)
    if order is None:
        return abort(404)

    if 'order' in data:

        adress = data['order']['shipping_information']

        if 'email' not in data['order'] or 'country' not in adress or 'adress' not in adress or 'postal_code' not in adress or 'city' not in adress or 'province' not in adress:
            return jsonify({'errors': {
                'order': {
                   'code': 'out-of-inventory',
                   'name': "Il manque un ou plusieur champs obligatoires"
               }
            }}), 422
        
        if order:
          # Mise à jour des informations sur le client si elles sont fournies
          if 'email' in data['order']:
              order.email = data['order']['email']
          if 'shipping_information' in data['order']:
            #   new_adress = dict_to_model(Shipping, data['order']['shipping_information'])
            #   new_adress.save()
             # Shipping.update(shipping_information = order_id).where(order.id == order_id).execute()
            Shipping.create(
                country=adress["country"],
                adress=adress["adress"],
                postal_code=adress["postal_code"],
                city=adress["city"],
                province=adress["province"],
                commande=order
            )

        # Sauvegarder les modifications dans la base de données
          order.save()

        return redirect(url_for("get_order", order_id=order.id, _method='GET'))
        
    
    if 'credit_card' in data: 


        montant_total = order.shipping_price
        
        # Ajouter le montant total dans les informations envoyées à l'API de paiement
        data['amount_charged'] = montant_total

        carte = json.dumps(data)
        post_carte = carte.encode("UTF-8")

        url_paiment = "http://dimprojetu.uqac.ca/~jgnault/shops/pay/"


        # Créer une requête POST avec les données JSON
        req = urllib.request.Request(url_paiment, post_carte, headers={'Content-Type': 'application/json'})

        # Envoyer la requête
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            response_data = json.loads(response_data)

        transaction_data = response_data.get('transaction')
        if transaction_data:
            new_transaction = Transactions.create(
                id=transaction_data['id'],
                success=transaction_data['success'],
                amount_charged=transaction_data['amount_charged']
            )

                    
        new_card = dict_to_model(Card, response_data['credit_card'])
        new_card.save()


        return jsonify(response_data)
