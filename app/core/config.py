## config do ambiente (variaveis de ambiente)from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Definimos as configurações base da aplicação
class Settings(BaseSettings):
    # Configuração Pydantic Settings
    # O model_config especifica onde Pydantic deve buscar as variáveis (do .env)
    model_config = SettingsConfigDict(
        env_file='.env', 
        case_sensitive=True, # Garante que as chaves sejam lidas exatamente como estão no .env
        extra='ignore' # Ignora chaves que existam no ambiente, mas não na classe
    )

    # ----------------------------------------------------
    # 1. CONFIGURAÇÕES GERAIS DO PROJETO E DO SERVIDOR
    # ----------------------------------------------------
    ENV: str
    SECRET_KEY: str
    BASE_URL: str
    N8N_API_KEY: str
    # ----------------------------------------------------
    # 2. CONFIGURAÇÕES DO BANCO DE DADOS
    # ----------------------------------------------------
    # A URL completa é a forma preferida para conexão
    DATABASE_URL: str
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    # Detalhes opcionais, caso precise montar a URL em outro lugar
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_NAME: str

    # ----------------------------------------------------
    # 3. INTEGRAÇÃO WHATSAPP (UAZAPI / Z-API)
    # ----------------------------------------------------
    WHATSAPP_API_BASE_URL: str
    WHATSAPP_PARTNER_TOKEN: str
    WHATSAPP_WEBHOOK_URL: str
    # O webhook secret pode ser opcional, dependendo da API
    WHATSAPP_WEBHOOK_SECRET: Optional[str] = None # 'Optional' e '= None' tornam a variável opcional

    # ----------------------------------------------------
    # 4. INTEGRAÇÃO GOOGLE OAUTH2
    # ----------------------------------------------------
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    GOOGLE_SCOPES: str
    
# Cria uma instância única da classe Settings para ser importada em toda a aplicação
settings = Settings()

N8N_WEBHOOK_URL: str

FRONTEND_BASE_URL: str = "http://localhost:5173"


# Exemplo de uso:
# print(settings.BASE_URL)
# print(settings.WHATSAPP_PARTNER_TOKEN)


    
