import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth

cred = credentials.Certificate("serviceAccountKey.json")


#cred_dict = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
#cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)
db = firestore.client()
