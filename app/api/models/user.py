from sqlalchemy import Column, Integer, String, Boolean
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Identidade do médico
    nome = Column(String, nullable=False)
    inbox_id = Column(Integer, unique=True, nullable=True)
    
    # Número do WhatsApp conectado ao Chatwoot
    phone_channel = Column(String, unique=True, index=True, nullable=False)

    # Dados de agenda
    calendar_id = Column(String, nullable=False)
    timezone = Column(String, default="America/Sao_Paulo")

    duracao_consulta = Column(Integer, nullable=False)  # minutos
    valor_consulta = Column(Integer, nullable=True)     # centavos

    ativo = Column(Boolean, default=True)

    # Auth (opcional manter)
    email = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=True)

    # bio_profissional = Column(String, nullable=True)
    # especialidade = Column(String, nullable=True)