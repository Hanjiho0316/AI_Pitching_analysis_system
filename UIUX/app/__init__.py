from flask import Flask

app = Flask(__name__)
app.secret_key = "pitch_types_secret_key"

from app import routes