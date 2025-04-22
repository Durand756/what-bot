# main.py
import os
import inspect
import requests
import random
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration Meta WhatsApp API
META_WHATSAPP_TOKEN = os.environ.get('META_WHATSAPP_TOKEN')
META_WHATSAPP_PHONE_ID = os.environ.get('META_WHATSAPP_PHONE_ID')
META_VERIFY_TOKEN = os.environ.get('META_VERIFY_TOKEN', 'token_secret_unique')
META_API_VERSION = os.environ.get('META_API_VERSION', 'v18.0')

# Vérification des variables d'environnement
if not all([META_WHATSAPP_TOKEN, META_WHATSAPP_PHONE_ID]):
    logger.error("Variables d'environnement Meta WhatsApp manquantes!")

class CommandHandler:
    def __init__(self):
        self.commands = {}
        self.default_response = "Je ne comprends pas cette commande. Envoyez !aide pour voir la liste des commandes disponibles."
        
        # Enregistrement automatique des commandes
        self._register_commands()
    
    def _register_commands(self):
        """Enregistre automatiquement toutes les méthodes commençant par 'cmd_'"""
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith('cmd_'):
                command_name = name[4:]  # Supprimer le préfixe 'cmd_'
                self.register_command(command_name, method)
    
    def register_command(self, command_name, callback):
        """Enregistre une nouvelle commande"""
        self.commands[command_name.lower()] = callback
        logger.info(f"Commande '{command_name}' enregistrée")
        return callback  # Retourne la fonction pour permettre l'utilisation comme décorateur
    
    def process_command(self, message, sender):
        """Traite un message et exécute la commande appropriée"""
        # Si le message commence par '!', c'est une commande
        if message.startswith('!'):
            # Séparer le nom de la commande et les arguments
            parts = message[1:].split(' ', 1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ''
            
            # Exécuter la commande si elle existe
            if command in self.commands:
                logger.info(f"Exécution de la commande '{command}'")
                return self.commands[command](args, sender)
            else:
                return f"Commande inconnue: {command}. Envoyez !aide pour voir les commandes disponibles."
        
        # Si ce n'est pas une commande, traiter comme un message normal
        return self._handle_normal_message(message, sender)
    
    def _handle_normal_message(self, message, sender):
        """Traite les messages qui ne sont pas des commandes"""
        # Par défaut, répondre avec un message d'aide
        return "Bonjour! Je suis un bot WhatsApp. Envoyez !aide pour voir les commandes disponibles."
    
    # Définition des commandes intégrées
    def cmd_aide(self, args, sender):
        """Affiche la liste des commandes disponibles"""
        help_text = "Commandes disponibles:\n"
        for cmd_name, cmd_func in self.commands.items():
            doc = cmd_func.__doc__ or "Pas de description disponible"
            help_text += f"!{cmd_name} - {doc}\n"
        return help_text
    
    def cmd_salut(self, args, sender):
        """Salue l'utilisateur"""
        return f"Bonjour! Comment puis-je vous aider aujourd'hui?"
    
    def cmd_echo(self, args, sender):
        """Répète le message de l'utilisateur"""
        if not args:
            return "Vous n'avez rien dit à répéter!"
        return f"Vous avez dit: {args}"
    
    def cmd_meteo(self, args, sender):
        """Obtient la météo pour une ville (ex: !meteo Paris)"""
        if not args:
            return "Veuillez spécifier une ville. Exemple: !meteo Paris"
        
        city = args.strip()
        api_key = os.environ.get('WEATHER_API_KEY', '')
        
        if not api_key:
            return "Service météo temporairement indisponible."
        
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=fr"
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                temp = data['main']['temp']
                description = data['weather'][0]['description']
                return f"Météo à {city}: {description}, {temp}°C"
            else:
                return f"Impossible de trouver la météo pour {city}."
        except Exception as e:
            return "Erreur lors de la récupération des données météo."
    
    def cmd_citation(self, args, sender):
        """Renvoie une citation inspirante aléatoire"""
        citations = [
            "La vie est ce qui arrive quand on a d'autres projets. - John Lennon",
            "Le succès, c'est d'aller d'échec en échec sans perdre son enthousiasme. - Winston Churchill",
            "La seule façon de faire du bon travail est d'aimer ce que vous faites. - Steve Jobs",
            "La simplicité est la sophistication suprême. - Léonard de Vinci",
            "L'imagination est plus importante que le savoir. - Albert Einstein"
        ]
        return random.choice(citations)
    
    def cmd_heure(self, args, sender):
        """Affiche l'heure et la date actuelles"""
        now = datetime.now()
        return f"Il est actuellement {now.strftime('%H:%M:%S')} le {now.strftime('%d/%m/%Y')}."

# Créer une instance du gestionnaire de commandes
command_handler = CommandHandler()

# Fonction pour ajouter des commandes personnalisées
def add_custom_command(name, description):
    """Décorateur pour ajouter facilement des commandes personnalisées"""
    def decorator(func):
        def wrapper(args, sender):
            return func(args, sender)
        wrapper.__doc__ = description
        return command_handler.register_command(name, wrapper)
    return decorator

# Exemple d'ajout d'une commande personnalisée
@add_custom_command("info", "Affiche des informations sur le bot")
def cmd_info(args, sender):
    return "Bot WhatsApp développé avec l'API Meta WhatsApp Business. Version 1.0.0"

def send_whatsapp_message(phone_number, message):
    """Envoie un message WhatsApp via l'API Meta"""
    url = f"https://graph.facebook.com/{META_API_VERSION}/{META_WHATSAPP_PHONE_ID}/messages"
    
    # Format du numéro de téléphone: doit être au format international sans '+' 
    # Ex: 33612345678 pour un numéro français
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {META_WHATSAPP_TOKEN}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            logger.info(f"Message envoyé à {phone_number}")
            return True
        else:
            logger.error(f"Erreur lors de l'envoi du message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception lors de l'envoi du message: {e}")
        return False

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Endpoint pour la vérification du webhook par Meta"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    logger.info(f"Vérification du webhook - Mode: {mode}, Token: {token}, Challenge: {challenge}")
    
    if mode and token:
        if mode == 'subscribe' and token == META_VERIFY_TOKEN:
            logger.info("Webhook vérifié avec succès")
            return challenge, 200
        else:
            logger.error(f"Échec de vérification. Token reçu: {token}, attendu: {META_VERIFY_TOKEN}")
            return "Verification failed", 403
    return "Hello World", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint pour recevoir les messages WhatsApp via l'API Meta"""
    data = request.json
    logger.info(f"Données reçues sur webhook: {data}")
    
    try:
        if data.get('object'):
            if data.get('entry') and data['entry'][0].get('changes') and data['entry'][0]['changes'][0].get('value') and \
               data['entry'][0]['changes'][0]['value'].get('messages') and data['entry'][0]['changes'][0]['value']['messages'][0]:
                
                message_data = data['entry'][0]['changes'][0]['value']['messages'][0]
                sender_id = message_data['from']
                
                if message_data.get('text') and message_data['text'].get('body'):
                    message_text = message_data['text']['body']
                    
                    logger.info(f"Message reçu de {sender_id}: {message_text}")
                    
                    # Traiter la commande
                    response_text = command_handler.process_command(message_text, sender_id)
                    
                    # Envoyer la réponse
                    send_whatsapp_message(sender_id, response_text)
                
                return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Erreur dans le webhook: {e}")
    
    return jsonify({"status": "received"}), 200

@app.route('/status', methods=['GET'])
def status():
    """Endpoint pour vérifier l'état du service"""
    return jsonify({
        "status": "online",
        "environment": {
            "META_WHATSAPP_PHONE_ID": META_WHATSAPP_PHONE_ID is not None,
            "META_WHATSAPP_TOKEN": META_WHATSAPP_TOKEN is not None,
            "META_VERIFY_TOKEN": META_VERIFY_TOKEN is not None,
        }
    })

@app.route('/', methods=['GET'])
def health_check():
    """Route pour la vérification de santé requise par Render"""
    return "Bot WhatsApp Meta en ligne!"

if __name__ == '__main__':
    # Utilisé pour le développement local
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
