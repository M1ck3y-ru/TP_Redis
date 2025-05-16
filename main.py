from flask import Flask, jsonify, render_template, request
import redis
import time
import json

app = Flask(__name__)
# Configuration Redis - Connexion au maître pour les opérations d'écriture/lecture
redis_client = redis.Redis(
    host='localhost',  # Adresse locale
    port=6379,         # Port du maître
    decode_responses=True
)

# Facultatif: Configuration d'une deuxième connexion pour les opérations de lecture uniquement
# qui pourrait être dirigée vers le slave pour répartir la charge
redis_read_client = redis.Redis(
    host='localhost',  # Adresse locale
    port=6380,         # Port de l'esclave
    decode_responses=True
)
# Durée de vie du cache en secondes
CACHE_TTL = 60

def initialize_product_database():
    # Produits à ajouter
    products = [
        {
            "id": "prod1",
            "name": "Smartphone Premium",
            "price": 899.99,
            "category": "electronics",
            "in_stock": True,
            "features": ["5G", "HDR Display", "Water Resistant"]
        },
        {
            "id": "prod2",
            "name": "Casque Bluetooth",
            "price": 159.99,
            "category": "accessories",
            "in_stock": True,
            "features": ["Noise Cancelling", "24h Battery"]
        },
        {
            "id": "prod3",
            "name": "SSD 1To",
            "price": 129.99,
            "category": "storage",
            "in_stock": False,
            "features": ["NVMe", "High Speed"]
        }
    ]
    
    # Ajouter chaque produit à Redis comme entrée permanente
    for product in products:
        product_id = product["id"]
        
        # Stocker les détails du produit comme JSON (string)
        redis_client.set(f"db:product:{product_id}", json.dumps(product))
        
        # Ajouter à l'index des produits (set)
        redis_client.sadd("db:products", product_id)
        
        # Ajouter à l'index par catégorie (set)
        redis_client.sadd(f"db:category:{product['category']}", product_id)
        
        # Ajouter au sorted set par prix
        redis_client.zadd("db:products:by_price", {product_id: product['price']})
    
    print(f"Base de données produits initialisée avec {len(products)} produits")

# Route principale pour servir l'interface utilisateur
@app.route('/')
def index():
    return render_template('index.html')

# API route pour obtenir les données au format JSON (CACHE)
@app.route('/api/data/<item_id>')
def get_data(item_id):
    # Étape 1: Vérifier si la donnée est en cache
    cache_key = f"data:{item_id}"
    cached_data = redis_client.get(cache_key)
    
    # Source de la réponse (cache ou base de données)
    source = "cache"
    start_time = time.time()
    
    if cached_data:
        # Étape 2: Donnée trouvée dans le cache
        data = json.loads(cached_data)
    else:
        # Étape 3: Donnée absente du cache
        source = "database"
        
        # Simulation d'une requête lente à la base de données
        time.sleep(2)
        
        # Génération de données simulées
        data = {
            "id": item_id,
            "name": f"Item {item_id}",
            "description": f"Description for item {item_id}",
            "timestamp": time.time()
        }
        
        # Enregistrement dans Redis avec expiration
        redis_client.setex(
            cache_key,
            CACHE_TTL,
            json.dumps(data)
        )
    
    # Calcul du temps de réponse
    response_time = round((time.time() - start_time) * 1000)
    
    # Ajout de la source et du TTL restant à la réponse
    response = {
        "data": data,
        "source": source,
        "response_time": response_time
    }
    
    if source == "cache":
        response["ttl"] = redis_client.ttl(cache_key)
    
    return jsonify(response)

# Route pour obtenir les statistiques de l'API (optionnel)
@app.route('/api/stats')
def get_stats():
    # Ici vous pourriez implémenter des statistiques réelles
    # Pour l'instant, nous retournons des données fictives
    return jsonify({
        "total_requests": 0,
        "cache_hits": 0,
        "average_response_time": 0
    })

# Ajouter des données permanentes à la base de données Redis
@app.route('/api/db/add', methods=['POST'])
def add_db_data():
    # Obtenir les données JSON de la requête
    data = request.get_json()
    
    if not data or 'id' not in data:
        return jsonify({"error": "L'ID est requis"}), 400
    
    # Créer une clé de base de données (remarquez qu'on utilise un préfixe différent)
    db_key = f"db:{data['id']}"
    
    # Ajouter un timestamp si non présent
    if 'timestamp' not in data:
        data['timestamp'] = time.time()
    
    # Enregistrer dans Redis SANS expiration
    redis_client.set(
        db_key,
        json.dumps(data)
    )
    
    return jsonify({
        "message": "Données ajoutées en base de données avec succès",
        "data": data
    })

# Lister toutes les entrées de la base de données
@app.route('/api/db/list')
def list_db_data():
    # Récupérer toutes les clés commençant par "db:"
    keys = redis_client.keys("db:*")
    
    # Convertir les clés en chaînes de caractères
    string_keys = [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
    
    # Extraire les IDs de ces clés
    ids = [key.split(':')[1] for key in string_keys]
    
    return jsonify({
        "count": len(ids),
        "ids": ids
    })

# Récupérer un produit spécifique
@app.route('/api/db/product/<product_id>')
def get_product(product_id):
    product_key = f"db:product:{product_id}"
    product_data = redis_client.get(product_key)
    
    if product_data:
        return jsonify({
            "data": json.loads(product_data),
            "source": "redis_db"
        })
    else:
        return jsonify({"error": "Produit non trouvé"}), 404

# Récupérer les produits par catégorie
@app.route('/api/db/category/<category>')
def get_products_by_category(category):
    category_key = f"db:category:{category}"
    
    # Récupérer les IDs des produits dans cette catégorie
    product_ids = redis_client.smembers(category_key)
    
    if not product_ids:
        return jsonify({"error": "Catégorie non trouvée ou vide"}), 404
    
    # Récupérer les détails de chaque produit
    products = []
    for product_id in product_ids:
        product_data = redis_client.get(f"db:product:{product_id}")
        if product_data:
            products.append(json.loads(product_data))
    
    return jsonify({
        "category": category,
        "count": len(products),
        "products": products
    })

# Récupérer les produits triés par prix
@app.route('/api/db/products/by-price')
def get_products_by_price():
    # Récupérer les IDs des produits triés par prix (du moins cher au plus cher)
    product_ids_with_scores = redis_client.zrange("db:products:by_price", 0, -1, withscores=True)
    
    # Récupérer les détails de chaque produit
    products = []
    for product_id, price in product_ids_with_scores:
        product_data = redis_client.get(f"db:product:{product_id}")
        if product_data:
            products.append(json.loads(product_data))
    
    return jsonify({
        "count": len(products),
        "products": products
    })
    
@app.route('/api/db/product/<product_id>')
def get_db_product(product_id):
    product_key = f"db:product:{product_id}"
    product_data = redis_client.get(product_key)
    
    if product_data:
        return jsonify({
            "data": json.loads(product_data),
            "source": "redis_db"
        })
    else:
        return jsonify({"error": "Produit non trouvé"}), 404

if __name__ == '__main__':
    # Initialiser la base de données de produits
    initialize_product_database()
    # Lancer l'application Flask
    app.run(debug=True, host='192.168.1.17', port=8090)