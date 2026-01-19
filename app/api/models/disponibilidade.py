from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.base_class import Base
from sqlalchemy.types import SmallInteger, Time, Boolean
from datetime import datetime

class ProfissionalDisponibilidade(Base):
    __tablename__ = "profissional_disponibilidade"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    dia_semana = Column(SmallInteger)
    hora_inicio = Column(Time)
    hora_fim = Column(Time)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
