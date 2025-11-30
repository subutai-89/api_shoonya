import yaml
from NorenRestApiPy import NorenApi
from pyotp import TOTP
import base64
import threading


def load_credentials():
    with open('config/credentials.yml', 'r') as file:
        return yaml.safe_load(file)


def generate_totp(base32_secret):
    return TOTP(base32_secret).now()


def login_shoonya():
    credentials = load_credentials()
    
    # Convert secret to Base32 if needed
    secret = credentials['totp_secret']
    base32_secret = base64.b32encode(secret.encode()).decode() if not secret.isupper() else secret
    
    factor2 = generate_totp(base32_secret)
    
    # Initialize API with WebSocket URL
    api = NorenApi.NorenApi(host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSWeb/')
    ret = api.login(
        userid=credentials['user'],
        password=credentials['pwd'],
        twoFA=factor2,
        vendor_code=credentials['vc'],
        api_secret=credentials['apikey'],
        imei=credentials['imei']
    )
    return api, ret


def start_websocket(api):
    """
    Start WebSocket connection for real-time data.
    """
    def on_message(ws, message):
        print("WebSocket Message:", message)
        # Handle incoming message here

    # Initialize WebSocket
    ws = api.start_websocket()
    ws.on_message = on_message
    # Run WebSocket in a separate thread to avoid blocking
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.start()
    return ws_thread


def get_token(api, exchange, tradingsymbol):
    """
    Fetch token for a given exchange and tradingsymbol.
    """
    ret = api.searchscrip(exchange=exchange, searchtext=tradingsymbol)
    if ret and 'values' in ret:
        for item in ret['values']:
            if item['tsym'] == tradingsymbol:
                return item['token']
    return None


def logout_shoonya(api):
    ret = api.logout()
    return ret
