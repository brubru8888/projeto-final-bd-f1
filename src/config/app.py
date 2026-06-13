import os
from flask import Flask
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

aplicacao = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'src/app/views/templates'),
    static_folder=os.path.join(BASE_DIR, 'src/app/views'),
    static_url_path='/estatico'
)

CORS(aplicacao)

aplicacao.config['SECRET_KEY'] = 'sua-chave-secreta-aqui'

from src.app.rotas import rotas
rotas(aplicacao)

