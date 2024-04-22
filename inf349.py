import html
import os
from flask import Flask, jsonify, request, abort, redirect, url_for
import peewee as p
from rq import Queue, Worker

import json
import datetime
import urllib.request
from urllib.parse import urlencode
from playhouse.shortcuts import model_to_dict, dict_to_model
from redis import Redis

redis = Redis.from_url("redis://localhost")
rq = Queue(connection=redis)

db = p.PostgresqlDatabase(
    os.environ.get('DB_NAME', 'inf349'),
    user=os.environ.get('DB_USER', 'user'),
    password=os.environ.get('DB_PASSWORD', 'pass'),
    host=os.environ.get('DB_HOST', 'localhost'),
    port=os.environ.get('DB_PORT', 5432)
)

# db = p.SqliteDatabase("commandes.db")

app = Flask("shopping")

class BaseModel(p.Model):
    class Meta:
        database = db

class Produits(BaseModel):
    id = p.IntegerField()
    description = p.TextField(null=True)
    height = p.IntegerField(null=True)
    image = p.CharField(null=True)
    stock = p.BooleanField(null=True)
    name = p.CharField(null=True)
    price = p.FloatField(null=True)
    type = p.CharField(null=True)
    weight = p.IntegerField(null=True)

class Shipping(BaseModel):
    id = p.AutoField(primary_key=True)
    country = p.CharField(null=True)
    adress = p.CharField(null=True)
    postal_code = p.CharField(null=True)
    city = p.CharField(null=True)
    province = p.CharField(null=True)

class Card(BaseModel):
    id = p.AutoField(null=True)
    name = p.CharField(null=True)
    first_digits = p.CharField(null=True)
    last_digits = p.CharField(null=True)
    expiration_year = p.IntegerField(null=True)
    expiration_month = p.IntegerField(null=True)
    

class Transactions(BaseModel):
    id = p.AutoField(null=True)
    id_transaction = p.CharField(null=True)
    success = p.BooleanField(null=True)
    amount_charged = p.FloatField(null=True)

class Commande(BaseModel):
    id = p.AutoField(primary_key=True)
    total_price = p.FloatField(null=True)
    id_produit = p.IntegerField(null=True)
    quantity = p.IntegerField(default=0, null=True, constraints=[p.Check('quantity > 1')])
    email = p.CharField(null=True)
    credit_card = p.TextField(null=True)
    paid = p.BooleanField(default=False, null=True)
    shipping_price = p.FloatField(null=True)
    shipping_information = p.ForeignKeyField(Shipping, backref="shipping_information", null=True)
    credit_card = p.ForeignKeyField(Card, backref="credit_card", null=True)
    transaction = p.ForeignKeyField(Transactions, backref="transactions", null=True)


with app.app_context():
    db.connect()
    db.create_tables([Commande, Produits, Shipping, Card, Transactions])


def clean_description(description):
    # Supprimer les caractères nuls de la description
    return description.replace('\x00', '')

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
                    description=clean_description(product['description']),
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

    cache_key = "commande-{0}".format(order_id)

    if redis.exists(cache_key):
        return json.loads(redis.get(cache_key))
    
    else:
        order = Commande.get_or_none(order_id)
        if order is None:
            return abort(404)
    
        order_data = model_to_dict(order)
        return jsonify(order_data)
    

@app.route('/order/<int:order_id>', methods=['PUT'])
def ajout_infos(order_id):
    data = request.json

    # Récupérer la commande de la base de données par son identifiant
    order = Commande.get_or_none(Commande.id == order_id)
    if order is None:
        return abort(404)

    if order.paid:
        return jsonify({'error': 'La commande a déjà été payée'}), 422

    if 'order' in data:
        adress = data['order']['shipping_information']

        # Vérifier si les champs nécessaires sont présents
        if 'email' not in data['order']:
            return jsonify({'errors': {'email': 'L\'adresse e-mail est requise'}}), 422

        if 'shipping_information' not in data['order']:
            return jsonify({'errors': {'shipping_information': 'Les informations d\'expédition sont requises'}}), 422

        if 'country' not in adress or 'adress' not in adress or 'postal_code' not in adress or 'city' not in adress or 'province' not in adress:
            return jsonify({'errors': {
                'shipping_information': 'Il manque un ou plusieurs champs obligatoires'
            }}), 422
        
        if 'credit_card' in data['order'] and 'shipping_information' in data['order']:
            return jsonify({'errors': {
                'shipping_information': 'Impossible d\'envoyer les information de livraison et de paiement en même temps'
            }}), 422


        # Mise à jour des informations sur le client si elles sont fournies
        order.email = data['order']['email']
        new_shipping = Shipping.create(
            country=adress["country"],
            adress=adress["adress"],
            postal_code=adress["postal_code"],
            city=adress["city"],
            province=adress["province"]
        )

        order.shipping_information = new_shipping.id

        # Sauvegarder les modifications dans la base de données
        order.save()

        return redirect(url_for("get_order", order_id=order.id, _method='GET'))

    if 'credit_card' in data:
        # Vérifier si les informations d'expédition sont présentes
        if not order.shipping_information:
            return jsonify({'errors': {'shipping_information': 'Les informations d\'expédition sont requises'}}), 422
        
        expiration_year = data['credit_card']['expiration_year']
        expiration_month = data['credit_card']['expiration_month']
        
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month

        if not isinstance(expiration_year, int) or not isinstance(expiration_month, int):
            return jsonify({'error': 'expiration_year et expiration_month doivent être des entiers'}), 422

        if expiration_year < current_year or (expiration_year == current_year and expiration_month < current_month):
            return jsonify({'error': 'La carte est expirée'}), 422

        cvv = data['credit_card']['cvv']
        if not isinstance(cvv, str) or not cvv.isdigit() or len(cvv) != 3:
            return jsonify({'error': 'cvv doit être une chaîne de 3 chiffres'}), 422

        work = rq.enqueue(paiement, order, data)

        return redirect(url_for("check_work", work_id=work.id, _method='GET'))

def paiement(order, data):
            # Ajouter le montant total dans les informations envoyées à l'API de paiement
        montant_total = order.shipping_price
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
                id_transaction=transaction_data['id'],
                success=transaction_data['success'],
                amount_charged=transaction_data['amount_charged']
            )
            order.transaction = new_transaction.id


        new_card = dict_to_model(Card, response_data['credit_card'])
        new_card.save()

        order.credit_card = new_card.id

        # Marquer la commande comme payée
        order.paid = True
        order.save()

        # si la commande est payée, on l'ajout dans le base de données redis
        if order.paid == True:
            order_data = model_to_dict(order)
            cache_key = "commande-{0}".format(order.id)
            redis.set(cache_key, json.dumps(order_data))
            print(redis.get(cache_key))

        return "Patate"
        
    
@app.route('/work/<string:work_id>', methods=['GET'])
def check_work(work_id):
    job = rq.fetch_job(work_id)
    if not job.is_finished:
        return jsonify(), 202

    return job.result


@app.cli.command("init-db")
def init_db():
    db.create_tables([Commande, Produits, Shipping, Card, Transactions])

@app.cli.command("worker")
def rq_worker():
    worker = Worker([rq], connection=redis)
    worker.work()