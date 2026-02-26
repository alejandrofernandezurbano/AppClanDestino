import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore, auth

'''
cred_json = base64.b64decode(
    os.environ["FIREBASE_KEY_BASE64"]
).decode("utf-8")

cred_dict = json.loads(cred_json)

cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
'''
base64_key = os.environ.get("FIREBASE_KEY_BASE64")

if not base64_key:
    raise ValueError("No FIREBASE_KEY_BASE64 environment variable set")

decoded_key = base64.b64decode(base64_key)
cred_dict = json.loads(decoded_key)

cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

db = firestore.client()
'''cred = credentials.Certificate("serviceAccountKey.json")


#cred_dict = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
#cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)
db = firestore.client()'''
