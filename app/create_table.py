from app.db.base_class import Base
from app.db.session import engine

# IMPORTAR TODOS OS MODELOS para que o SQLAlchemy registre no metadata
from app.api.models.user import User
from app.api.models.google_token import GoogleToken
from app.api.models.disponibilidade import ProfissionalDisponibilidade
# Se futuramente tiver mais modelos, importe aqui

def create_all():
    print("📦 Criando tabelas no banco...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas com sucesso!")

if __name__ == "__main__":
    create_all()
