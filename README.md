Redis comme système de cache distribué : applications, comparaison avec les bases relationnelles, et implémentation
Dans quels types de projets Redis est utile ?
Redis est particulièrement utile dans plusieurs types de projets :

Applications nécessitant des performances élevées :

Sites web à fort trafic
Applications temps réel (chat, streaming)
Jeux en ligne avec scores en temps réel
API à haute disponibilité


Cas d'usage spécifiques :

Mise en cache de données (comme notre projet)
Gestion de sessions utilisateurs
Files d'attente de messages
Limite de taux d'appels API (rate limiting)
Analyse de données en temps réel
Compteurs et statistiques en direct
Classements et leaderboards


Architecture microservices : Comme couche de communication entre services ou pour stocker des données partagées
Systèmes distribués : En raison de sa capacité à fonctionner en mode cluster ou réplication
a
Redis vs Bases de données relationnelles : Pourquoi clé-valeur ?
Redis est une base de données de type clé-valeur et non relationnelle pour plusieurs raisons :

Performance :

Redis stocke tout en mémoire (RAM), permettant des temps de réponse en microsecondes
Les bases relationnelles utilisent principalement le disque, qui est beaucoup plus lent


Simplicité et accès direct :

Redis accède aux données directement par leur clé (O(1) - complexité constante)
Les bases relationnelles nécessitent souvent des jointures et des recherches complexes


Flexibilité des données :

Redis ne force pas de schéma rigide (pas de tables avec colonnes définies)
Les valeurs dans Redis peuvent être des structures variées (chaînes, listes, ensembles, hashes)


Cas d'usage différents :

Redis se spécialise dans l'accès rapide à des données connues par leur identifiant
Les bases relationnelles excellent pour les requêtes complexes et les relations entre entités


Complémentarité plutôt qu'opposition :

Dans beaucoup d'architectures, Redis complète une base relationnelle (stockant temporairement les données fréquemment accédées)
Notre projet est un excellent exemple : les données "permanentes" pourraient être dans une base relationnelle, et Redis sert de cache rapide



Atelier Redis adapté - Système de Cache avec Réplication Master/Slave
Table des matières

Introduction
Prérequis
Partie 1 - Installation et configuration de Redis
Partie 2 - Architecture distribuée avec réplication Master/Slave
Partie 3 - Interface utilisateur moderne pour le monitoring Redis
Partie 4 - Redis comme base de données persistante
Ressources utiles
Dépannage

Introduction
Dans cet atelier, nous avons utilisé Redis pour créer un système de cache distribué avec une interface utilisateur moderne. Nous avons aussi exploré l'utilisation de Redis comme base de données en plus de son rôle de cache, démontrant sa flexibilité.
Prérequis

Environnement macOS, Linux ou Windows avec WSL
Python 3.x et Flask
Redis Server
Navigateur web moderne pour l'interface glassmorphism

Partie 1 - Installation et configuration de Redis
Installation (macOS)
bashbrew install redis
Vérification de l'installation
bash# Démarrer le serveur Redis
redis-server

# Vérifier que Redis fonctionne
redis-cli ping  # Doit renvoyer "PONG"
Partie 2 - Architecture distribuée avec réplication Master/Slave
Configuration du Master
bash# Configurer le serveur master sur le port par défaut (6379)
redis-server
Configuration du Slave
bash# Configurer le serveur slave sur un port différent (6380)
# avec réplication depuis le master
redis-server --port 6380 --replicaof 127.0.0.1 6379
Vérification de la réplication
bash# Sur le master
redis-cli -p 6379
> SET test "Hello Redis"
> INFO replication

# Sur un slave
redis-cli -p 6380
> GET test                # Affiche "Hello Redis"
> INFO replication        # Confirme le statut replica
Partie 3 - Interface utilisateur moderne pour le monitoring Redis
Nous avons créé une interface utilisateur moderne avec design glassmorphism pour visualiser et interagir avec Redis :
Installation de l'application
bash# Installation des dépendances
pip install flask redis

# Cloner le dépôt (ou créer les fichiers manuellement)
git clone https://github.com/votre-nom/redis-monitor.git
cd redis-monitor

# Démarrer l'application
python main.py
Fonctionnalités de l'interface

Recherche d'éléments dans le cache Redis
Visualisation du temps de réponse (cache vs. base de données)
Affichage du TTL (time-to-live) restant pour les entrées en cache
Statistiques de performance (Cache Hit Ratio)
Historique des recherches récentes

Partie 4 - Redis comme base de données persistante
Nous avons étendu l'utilisation de Redis au-delà du cache pour stocker des données permanentes :
Structure des données

Produits stockés sous forme de chaînes JSON (db:product:<id>)
Index des produits sous forme d'ensembles (db:products)
Index par catégorie (db:category:<category>)
Produits triés par prix (db:products:by_price)

API d'accès aux données
python# Exemple d'accès à un produit
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
Exemple de données produits
python# Initialisation de la base de données produits
def initialize_product_database():
    products = [
        {
            "id": "prod1",
            "name": "Smartphone Premium",
            "price": 899.99,
            "category": "electronics",
            "in_stock": True,
            "features": ["5G", "HDR Display", "Water Resistant"]
        },
        # Autres produits...
    ]
    
    # Ajouter chaque produit à Redis (sans TTL = persistant)
    for product in products:
        redis_client.set(f"db:product:{product['id']}", json.dumps(product))
        # Indexation par différents critères...
Ressources utiles

Documentation officielle Redis
Guide de réplication Redis
Patterns Redis pour le caching
Interface Flask-Redis

Dépannage
Problèmes courants

Erreur de connexion à Redis

Vérifiez que Redis est en cours d'exécution : ps aux | grep redis
Assurez-vous que l'adresse et le port sont corrects dans votre code
Pour se connecter localement, utilisez localhost ou 127.0.0.1


L'interface ne s'affiche pas correctement

Vérifiez que le serveur Flask est en cours d'exécution : python main.py
Assurez-vous d'accéder à la bonne URL : http://localhost:8090
Vérifiez les logs de Flask pour les erreurs potentielles


Les données ne s'affichent pas dans l'interface

Utilisez redis-cli pour vérifier que les données existent bien dans Redis
Vérifiez les clés : KEYS * (cache) ou KEYS db:* (base de données)
Examinez une clé spécifique : GET db:product:prod1