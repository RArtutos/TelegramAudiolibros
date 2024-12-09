import os
import json
import random
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import MessageTooLongError
from telethon.tl.types import InputFile
from config import Config
from audiobook_handler import AudiobookHandler
from message_formatter import MessageFormatter
from file_splitter import FileSplitter
from utils.admin_check import admin_only

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudiobookBot:
    def __init__(self):
        self.config = Config()
        self.client = TelegramClient('bot_session', 
                                   self.config.API_ID, 
                                   self.config.API_HASH)
        self.handler = AudiobookHandler()
        self.formatter = MessageFormatter()
        self.splitter = FileSplitter()
        logger.info("Bot inicializado correctamente")
        
    async def start(self):
        await self.client.start(bot_token=self.config.BOT_TOKEN)
        logger.info("Bot conectado a Telegram")
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            logger.info(f"Comando /start recibido de {event.sender_id}")
            is_admin = event.sender_id == self.config.ADMIN_ID
            message = ('¡Bienvenido al Bot de Audiolibros! 📚\n'
                      'Los audiolibros se suben automáticamente cada hora al canal.')
            
            if is_admin:
                message += '\nComo administrador, puedes usar /search para buscar audiolibros'
                
            await event.respond(message)

        @self.client.on(events.NewMessage(pattern='/search'))
        @admin_only()
        async def search_handler(event):
            logger.info(f"Búsqueda iniciada por admin {event.sender_id}")
            await event.respond('Por favor, escribe el título del audiolibro que deseas buscar:')
            try:
                response = await self.client.wait_event(
                    events.NewMessage(from_users=event.sender_id),
                    timeout=30
                )
                query = response.message.text
                logger.info(f"Búsqueda: {query}")
                
                results = self.handler.search_audiobooks(query)
                if not results:
                    await event.respond('No se encontraron resultados.')
                    return

                buttons = []
                for i, book in enumerate(results[:10]):
                    buttons.append([Button.inline(book['title'][:100], data=f'book_{i}')])
                
                await event.respond('Resultados encontrados:', buttons=buttons)
            except asyncio.TimeoutError:
                await event.respond('Tiempo de espera agotado. Por favor, intenta de nuevo.')
            except Exception as e:
                logger.error(f"Error en búsqueda: {e}")
                await event.respond('Ocurrió un error durante la búsqueda.')

        @self.client.on(events.CallbackQuery())
        async def callback_handler(event):
            if event.sender_id != self.config.ADMIN_ID:
                await event.answer("❌ Solo el administrador puede seleccionar audiolibros.", alert=True)
                return
                
            data = event.data.decode()
            if data.startswith('book_'):
                index = int(data.split('_')[1])
                logger.info(f"Audiolibro seleccionado: índice {index}")
                await self.upload_audiobook(index)

    async def upload_random_audiobook(self):
        try:
            logger.info("Iniciando subida de audiolibro aleatorio")
            audiobook = self.handler.get_random_audiobook()
            await self.upload_audiobook(audiobook)
        except Exception as e:
            logger.error(f"Error al subir audiolibro aleatorio: {e}")

    async def upload_audiobook(self, audiobook):
        try:
            logger.info(f"Subiendo audiolibro: {audiobook['title']}")
            
            # Preparar mensaje con información del audiolibro
            caption = self.formatter.format_audiobook_info(audiobook)
            
            # Subir imagen de portada como foto
            try:
                async with self.client.action(self.config.CHANNEL_ID, 'photo'):
                    logger.info("Descargando portada...")
                    # Descargar la imagen temporalmente
                    cover_path = await self.handler.download_cover(audiobook['cover']['url'])
                    
                    logger.info("Enviando portada como foto...")
                    await self.client.send_file(
                        self.config.CHANNEL_ID,
                        cover_path,
                        caption=caption,
                        parse_mode='markdown',
                        force_document=False,  # Asegura que se envíe como foto
                        attributes=[]  # Sin atributos especiales
                    )
                    
                    # Limpiar archivo temporal de la portada
                    if os.path.exists(cover_path):
                        os.remove(cover_path)
                        
                logger.info("Portada subida exitosamente")
            except MessageTooLongError:
                logger.warning("Caption demasiado largo, enviando en mensajes separados")
                async with self.client.action(self.config.CHANNEL_ID, 'photo'):
                    cover_path = await self.handler.download_cover(audiobook['cover']['url'])
                    await self.client.send_file(
                        self.config.CHANNEL_ID,
                        cover_path,
                        force_document=False,
                        attributes=[]
                    )
                    if os.path.exists(cover_path):
                        os.remove(cover_path)
                        
                await self.client.send_message(
                    self.config.CHANNEL_ID,
                    caption,
                    parse_mode='markdown'
                )

            # Descargar y procesar archivo de audio
            logger.info("Descargando archivo de audio")
            audio_path = await self.handler.download_audiobook(audiobook)
            
            if os.path.getsize(audio_path) > 1.92 * 1024 * 1024 * 1024:  # 1.92GB
                logger.info("Archivo mayor a 1.92GB, dividiendo en partes")
                parts = self.splitter.split_file(audio_path)
                for i, part in enumerate(parts, 1):
                    logger.info(f"Subiendo parte {i}/{len(parts)}")
                    await self.client.send_file(
                        self.config.CHANNEL_ID,
                        part,
                        caption=f"Parte {i}/{len(parts)}"
                    )
                    os.remove(part)  # Limpiar parte después de subir
            else:
                logger.info("Subiendo archivo de audio completo")
                await self.client.send_file(
                    self.config.CHANNEL_ID,
                    audio_path
                )
            
            # Limpiar archivos temporales
            os.remove(audio_path)
            logger.info("Audiolibro subido exitosamente")
            
        except Exception as e:
            logger.error(f"Error al subir audiolibro: {e}", exc_info=True)

    async def schedule_uploads(self):
        while True:
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"Iniciando subida programada: {current_time}")
                await self.upload_random_audiobook()
            except Exception as e:
                logger.error(f"Error en subida programada: {e}")
            finally:
                await asyncio.sleep(3600)  # Esperar 1 hora

    def run(self):
        logger.info("Iniciando bot...")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        loop.create_task(self.schedule_uploads())
        logger.info("Bot ejecutándose...")
        loop.run_forever()

if __name__ == '__main__':
    bot = AudiobookBot()
    bot.run()