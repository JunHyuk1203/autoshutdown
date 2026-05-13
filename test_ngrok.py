import sys
from pyngrok import ngrok, conf

def test_ngrok():
    try:
        print("Starting ngrok test...")
        token = "3DZmg3sqJ6RKsm06VYzURXc3TVG_3PRerzUhuj9BiVuEohBit"
        domain = "crudely-feast-colt.ngrok-free.dev"
        print(f"Token: {token}")
        print(f"Domain: {domain}")
        
        conf.get_default().auth_token = token
        
        print("Connecting to ngrok...")
        url = ngrok.connect(5000, domain=domain).public_url
        print(f"Success! URL: {url}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ngrok()
