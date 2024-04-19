import pytest
from inf349 import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_produits(client):
    response = client.get('/')

    assert response.status_code == 200
    assert response.json is not None

def test_new_commande(client):
    
    response = client.post('/order', json={'product': {'id': 1, 'quantity': 5}})
    assert response.status_code == 302 
    
    response1 = client.post('/order', json={'product': {'id': 1, 'quantity': 0}})
    assert response1.status_code == 400

    response2 = client.post('/order', json={'product': {'quantity': 0}})
    assert response2.status_code == 422

    response3 = client.post('/order', json={'product': {'id': 4, 'quantity': 5}})
    assert response3.status_code == 422 

    
def test_get_order(client):
    
    order_id = 1  
    response = client.get(f'/order/{order_id}')

    assert response.status_code == 200
    assert response.json is not None

def test_put_order(client):

    order_id = 1  
    response = client.put(f'/order/{order_id}', json={
    "order" : {
        "email" : "valromeas43@orange.fr",
        "shipping_information" : {
            "country" : "Canada",
            "adress" : "300 rue Newton",
            "postal_code" : "G7H0S5",
            "city" : "Chicoutimi",
            "province" : "Québec"
        }
    }})

    assert response.status_code == 302

    response2 = client.put(f'/order/{order_id}', json={
    "order" : {
        "email" : "valromeas43@orange.fr",
        "shipping_information" : {
            "country" : "Canada",
            
            "postal_code" : "G7H0S5",
            "city" : "Chicoutimi",
            "province" : "Québec"
        }
    }})

    assert response2.status_code == 422

    response2 = client.put(f'/order/{order_id}', json={
    "order" : {
        "email" : "valromeas43@orange.fr",
        "shipping_information" : {
            "country" : "Canada",
            "adress" : "300 rue Newton",
            "postal_code" : "G7H0S5",
            "city" : "Chicoutimi",
            "province" : "Québec"
        },
        "credit_card" : {}
    }})

    assert response2.status_code == 422

    response3 = client.put(f'/order/{order_id}', json={
    "credit_card" : {
        "name" : "Val",
        "number" : "4242 4242 4242 4242",
        "expiration_year" : 2024,
        "cvv" : "35p",
        "expiration_month" : 6
    }
    })

    assert response3.status_code == 422

    response4 = client.put(f'/order/{order_id}', json={
    "credit_card" : {
        "name" : "Val",
        "number" : "4242 4242 4242 4242",
        "expiration_year" : 2023,
        "cvv" : "354",
        "expiration_month" : 6
    }
    })

    assert response4.status_code == 422

    response5 = client.put(f'/order/{order_id}', json={
    "credit_card" : {
        "name" : "Val",
        "number" : "4242 4242 4242 4242",
        "expiration_year" : 2024,
        "cvv" : "35",
        "expiration_month" : 6
    }
    })

    assert response5.status_code == 422

    response6 = client.put(f'/order/{order_id}', json={
    "credit_card" : {
        "name" : "Val",
        "number" : "4242 4242 4242 4242",
        "expiration_year" : 2024,
        "cvv" : "355",
        "expiration_month" : 2
    }
    })

    assert response6.status_code == 422


