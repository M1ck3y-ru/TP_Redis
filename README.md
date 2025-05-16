# Atelier Redis - Système de Cache Distribué

## Table des matières
- [Introduction](#introduction)
- [Prérequis](#prérequis)
- [Partie 1 - Installation de Redis](#partie-1---installation-de-redis)
- [Partie 2 - Architecture distribuée](#partie-2---architecture-distribuée)
  - [Option 1 : Réplication Master/Slave](#option-1--réplication-masterslave)
  - [Option 2 : Cluster Redis](#option-2--cluster-redis)
- [Partie 3 - Intégration dans une application web](#partie-3---intégration-dans-une-application-web)
- [Partie 4 - Vérification et démonstration](#partie-4---vérification-et-démonstration)
- [Ressources utiles](#ressources-utiles)
- [Dépannage](#dépannage)

## Introduction

Cet atelier vous permettra de découvrir Redis, un système de stockage de données en mémoire performant et polyvalent. Vous apprendrez à l'installer, le configurer en mode distribué (réplication ou clustering), puis à l'intégrer dans une application web en tant que cache selon le modèle cache-aside.

## Prérequis

- Environnement Linux, macOS ou Windows (WSL recommandé pour Windows)
- Droits d'administrateur sur votre machine
- Connaissances de base en ligne de commande
- Connaissances dans au moins un langage de programmation web (Python, Node.js, PHP, etc.)

## Partie 1 - Installation de Redis

### Installation

#### Sur Ubuntu/Debian
```bash
sudo apt update
sudo apt install redis-server
```

#### Sur macOS
```bash
brew install redis
```

#### Sur CentOS/RHEL
```bash
sudo yum install redis
```

### Vérification de l'installation
```bash
# Démarrer le serveur Redis
sudo systemctl start redis-server   # Sur Linux avec systemd
redis-server                        # Démarrage manuel

# Vérifier que Redis fonctionne
redis-cli ping                      # Doit renvoyer "PONG"
```

### Configuration de base
Modifiez le fichier de configuration Redis (généralement `/opt/hombrew/etc/redis.conf`) :

```bash
# Autoriser les connexions externes (pour la réplication ou le clustering)
bind 0.0.0.0

# Définir un mot de passe (recommandé)
requirepass VotreMotDePasseComplexe

# Pour la réplication ou le clustering
protected-mode no
```

N'oubliez pas de redémarrer Redis après modification :
```bash
sudo systemctl restart redis-server
```

## Partie 2 - Architecture distribuée

Choisissez l'une des deux options suivantes :

### Option 1 : Réplication Master/Slave

#### Configuration du Master
Le serveur est déjà configuré par défaut comme un master. Assurez-vous simplement que :
```bash
# Dans redis.conf du master
bind 0.0.0.0
requirepass VotreMotDePasseMaster
masterauth VotreMotDePasseMaster  # Pour permettre la réplication sécurisée
```

#### Configuration des Slaves
Sur chaque serveur slave, modifiez `redis.conf` :
```bash
# Dans redis.conf du slave
replicaof <IP_DU_MASTER> 6379
masterauth VotreMotDePasseMaster
requirepass VotreMotDePasseSlave
```

#### Vérification de la réplication
```bash
# Sur le master
redis-cli -a VotreMotDePasseMaster
> SET test "Hello Redis"
> INFO replication

# Sur un slave
redis-cli -a VotreMotDePasseSlave
> GET test                # Devrait afficher "Hello Redis"
> INFO replication
```

### Option 2 : Cluster Redis

#### Configuration des nœuds
Créez au moins 3 instances Redis (idéalement 6 pour avoir une réplication) :

```bash
# Créez les répertoires pour chaque nœud
mkdir -p /path/to/cluster/{7000,7001,7002,7003,7004,7005}
```

Pour chaque nœud, créez un fichier de configuration (ex: `redis-7000.conf`) :
```bash
port 7000
cluster-enabled yes
cluster-config-file nodes-7000.conf
cluster-node-timeout 5000
appendonly yes
dir /path/to/cluster/7000
bind 0.0.0.0
requirepass VotreMotDePasse
masterauth VotreMotDePasse
```

Répétez pour chaque port (7001, 7002, etc.) en changeant les valeurs appropriées.

#### Démarrer les nœuds
```bash
redis-server /path/to/cluster/7000/redis-7000.conf &
redis-server /path/to/cluster/7001/redis-7001.conf &
# ... et ainsi de suite pour chaque nœud
```

#### Création du cluster
```bash
redis-cli --cluster create 127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 -a VotreMotDePasse --cluster-replicas 1
```

#### Test du cluster
```bash
redis-cli -c -p 7000 -a VotreMotDePasse
> SET key1 "value1"
> SET key2 "value2"
> CLUSTER KEYSLOT key1       # Voir sur quel nœud cette clé est stockée
> CLUSTER NODES              # Voir tous les nœuds et leur état
```

## Partie 3 - Intégration dans une application web

Voici un exemple simple en Python avec Flask :

```python
from flask import Flask, jsonify
import redis
import time
import json

app = Flask(__name__)

# Configuration Redis
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    password='VotreMotDePasse',
    decode_responses=True
)

# Durée de vie du cache en secondes
CACHE_TTL = 60

@app.route('/data/<item_id>')
def get_data(item_id):
    # Étape 1: Vérifier si la donnée est en cache
    cache_key = f"data:{item_id}"
    cached_data = redis_client.get(cache_key)
    
    # Source de la réponse (cache ou base de données)
    source = "cache"
    
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
    
    # Ajout de la source et du TTL restant à la réponse
    response = {
        "data": data,
        "source": source
    }
    
    if source == "cache":
        response["ttl"] = redis_client.ttl(cache_key)
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### Instructions d'exécution
```bash
# Installation des dépendances
pip install flask redis

# Démarrer l'application
python app.py
```

## Partie 4 - Vérification et démonstration

### Test de performance
Utilisez curl ou un navigateur pour faire plusieurs requêtes successives :

```bash
# Première requête (lente, depuis la "base de données")
time curl http://localhost:5000/data/123

# Deuxième requête (rapide, depuis le cache)
time curl http://localhost:5000/data/123

# Attendre l'expiration du cache (> 60 secondes)
sleep 61

# Requête après expiration (lente à nouveau)
time curl http://localhost:5000/data/123
```

### Test de la distribution

#### Pour la réplication
1. Modifiez une donnée sur le master
2. Vérifiez qu'elle est disponible sur les slaves

#### Pour le clustering
1. Utilisez `CLUSTER KEYSLOT` pour voir où les clés sont stockées
2. Arrêtez un nœud primaire et vérifiez que son replica prend le relais
3. Vérifiez que les données sont toujours accessibles

## Ressources utiles

- [Documentation officielle Redis](https://redis.io/documentation)
- [Guide de réplication Redis](https://redis.io/topics/replication)
- [Guide du clustering Redis](https://redis.io/topics/cluster-tutorial)
- [Patterns de mise en cache](https://redis.io/docs/manual/patterns/distributed-locks/)

## Dépannage

### Problèmes courants

1. **Impossible de se connecter à Redis**
   - Vérifiez que Redis est en cours d'exécution : `ps aux | grep redis`
   - Vérifiez la configuration de liaison : `grep bind /etc/redis/redis.conf`
   - Vérifiez les pare-feu : `sudo ufw status` ou `sudo firewall-cmd --list-all`

2. **La réplication ne fonctionne pas**
   - Vérifiez les journaux : `journalctl -u redis-server`
   - Vérifiez la connexion réseau entre les serveurs : `ping <IP_DU_MASTER>`
   - Vérifiez le statut de la réplication : `redis-cli INFO replication`

3. **Problèmes de cluster**
   - Assurez-vous que tous les nœuds peuvent communiquer entre eux
   - Vérifiez l'état du cluster : `redis-cli -c -p 7000 CLUSTER INFO`
   - Réinitialisez un nœud si nécessaire : `redis-cli -c -p 7000 CLUSTER RESET`
