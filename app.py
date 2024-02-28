from flask import Flask, jsonify, request, abort, redirect, url_for
import peewee as p

import json
import datetime

db = p.SqliteDatabase('products.db')
app = Flask("shopping")

@app.route("/")
def coucou():
    return 'coucou'