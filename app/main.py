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
from utils.file_naming import get_audiobook_filename
from utils.telegram_utils import send_audio_file
from utils.download_manager import DownloadManager
from utils.stats_manager import StatsManager

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
        self._search_handlers = {}
        self.download_manager = DownloadManager()
        self.stats_manager = StatsManager()
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
                message += '\nComo administrador, puedes usar:\n'
                message += '- /search para buscar audiolibros\n'
                message += '- /status para ver el estado actual\n'
                message += '- /stats para ver estadísticas'
                
            await event.respond(message)

        @self.client.on(events.NewMessage(pattern='/status'))
        @admin_only()
        async def status_handler(event):
            progress = self.download_manager.get_progress()
            current_status = self.stats_manager.get_status()
            
            status_msg = f"📊 Estado actual del bot:\n\n"
            status_msg += f"Estado: {current_status}\n"
            
            if progress["status"] != "idle":
                status_msg += f"\nDescarga actual:\n"
                status_msg += f"Archivo: {progress['current_file']}\n"
                status_msg += f"Progreso: {progress['percentage']:.1f}%\n"
                status_msg += f"Descargado: {progress['progress'] / 1024 / 1024:.1f}MB\n"
                status_msg += f"Total: {progress['total'] / 1024 / 1024:.1f}MB"
            
            await event.respond(status_msg)

        @self.client.on(events.NewMessage(pattern='/stats'))
        @admin_only()
        async def stats_handler(event):
            stats = self.stats_manager.get_stats()
            stats_msg = f"📈 Estadísticas del bot:\n\n"
            stats_msg += f"Total de audiolibros subidos: {stats['total_uploads']}\n"
            stats_msg += f"Audiolibros únicos: {stats['unique_books']}\n"
            stats_msg += f"Tamaño total subido: {stats['total_size_gb']}GB"
            
            await event.respond(stats_msg)

        @self.client.on(events.NewMessage(pattern='/search'))
        @admin_only()
        async def search_handler(event):
            logger.info(f"Búsqueda iniciada por admin {event.sender_id}")
            sent_msg = await event.respond('Por favor, escribe el título del audiolibro que deseas buscar:')
            self._search_handlers[event.sender_id] = True

        @self.client.on(events.NewMessage())
        async def message_handler(event):
            if event.sender_id in self._search_handlers:
                try:
                    query = event.message.text
                    if query.startswith('/'):
                        return
                        
                    logger.info(f"Búsqueda: {query}")
                    del self._search_handlers[event.sender_id]
                    
                    results = self.handler.search_audiobooks(query)
                    if not results:
                        await event.respond('No se encontraron resultados.')
                        return

                    buttons = []
                    for i, book in enumerate(results):
                        buttons.append([Button.inline(book['title'][:100], data=f'book_{i}')])
                    
                    await event.respond('Resultados encontrados:', buttons=buttons)
                except Exception as e:
                    logger.error(f"Error en búsqueda: {e}")
                    await event.respond('Ocurrió un error durante la búsqueda.')
                    if event.sender_id in self._search_handlers:
                        del self._search_handlers[event.sender_id]

        @self.client.on(events.CallbackQuery())
        async def callback_handler(event):
            if event.sender_id != self.config.ADMIN_ID:
                await event.answer("❌ Solo el administrador puede seleccionar audiolibros.", alert=True)
                return
                
            data = event.data.decode()
            if data.startswith('book_'):
                try:
                    index = int(data.split('_')[1])
                    audiobook = self.handler.get_book_by_index(index)
                    
                    if self.stats_manager.is_book_uploaded(audiobook['idDownload']):
                        await event.answer("Este audiolibro ya fue subido anteriormente.", alert=True)
                        return
                        
                    logger.info(f"Audiolibro seleccionado: {audiobook['title']}")
                    await self.upload_audiobook(audiobook)
                except Exception as e:
                    logger.error(f"Error al procesar selección: {e}")
                    await event.answer("Error al procesar la selección", alert=True)

    async def upload_random_audiobook(self):
        try:
            logger.info("Iniciando subida de audiolibro aleatorio")
            while True:
                audiobook = self.handler.get_random_audiobook()
                if not self.stats_manager.is_book_uploaded(audiobook['idDownload']):
                    break
            await self.upload_audiobook(audiobook)
        except Exception as e:
            logger.error(f"Error al subir audiolibro aleatorio: {e}")

    async def upload_audiobook(self, audiobook):
        try:
            self.stats_manager.update_status(f"Subiendo: {audiobook['title']}")
            logger.info(f"Subiendo audiolibro: {audiobook['title']}")
            
            caption = self.formatter.format_audiobook_info(audiobook)
            
            info_message = None
            try:
                async with self.client.action(self.config.CHANNEL_ID, 'photo'):
                    logger.info("Descargando portada...")
                    cover_path = await self.download_manager.download_file(
                        audiobook['cover']['url'],
                        f"{self.config.TEMP_DIR}/cover_{random.randint(1000, 9999)}.jpg"
                    )
                    
                    logger.info("Enviando portada como foto...")
                    info_message = await self.client.send_file(
                        self.config.CHANNEL_ID,
                        cover_path,
                        caption=caption,
                        parse_mode='markdown',
                        force_document=False,
                        attributes=[]
                    )
                    
                    if os.path.exists(cover_path):
                        os.remove(cover_path)
                        
                logger.info("Portada subida exitosamente")
            except MessageTooLongError:
                logger.warning("Caption demasiado largo, enviando en mensajes separados")
                async with self.client.action(self.config.CHANNEL_ID, 'photo'):
                    cover_path = await self.download_manager.download_file(
                        audiobook['cover']['url'],
                        f"{self.config.TEMP_DIR}/cover_{random.randint(1000, 9999)}.jpg"
                    )
                    info_message = await self.client.send_file(
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

            logger.info("Descargando archivo de audio")
            self.stats_manager.update_status(f"Descargando: {audiobook['title']}")
            
            download_url = (
                f"https://pelis.gbstream.us.kg/api/v1/redirectdownload/"
                f"{audiobook['title']}.mp3?a=0&id={audiobook['idDownload']}"
            )
            
            audio_path = await self.download_manager.download_file(
                download_url,
                f"{self.config.TEMP_DIR}/{audiobook['idDownload']}.mp3",
                num_connections=4
            )
            
            if not audio_path:
                raise Exception("Failed to download audiobook")

            file_size = os.path.getsize(audio_path)
            
            if file_size > 1.92 * 1024 * 1024 * 1024:  # 1.92GB
                logger.info("Archivo mayor a 1.92GB, dividiendo en partes")
                parts = self.splitter.split_file(audio_path)
                for i, part in enumerate(parts, 1):
                    filename = get_audiobook_filename(audiobook['title'], i, len(parts))
                    final_path = os.path.join(os.path.dirname(part), filename)
                    os.rename(part, final_path)
                    
                    logger.info(f"Subiendo parte {i}/{len(parts)}")
                    self.stats_manager.update_status(f"Subiendo parte {i}/{len(parts)}: {audiobook['title']}")
                    
                    await send_audio_file(
                        self.client,
                        self.config.CHANNEL_ID,
                        final_path,
                        info_message.id if info_message else None,
                        f"Parte {i}/{len(parts)}"
                    )
                    os.remove(final_path)
            else:
                logger.info("Subiendo archivo de audio completo")
                self.stats_manager.update_status(f"Subiendo archivo: {audiobook['title']}")
                
                filename = get_audiobook_filename(audiobook['title'])
                final_path = os.path.join(os.path.dirname(audio_path), filename)
                os.rename(audio_path, final_path)
                
                await send_audio_file(
                    self.client,
                    self.config.CHANNEL_ID,
                    final_path,
                    info_message.id if info_message else None
                )
                os.remove(final_path)
            
            self.stats_manager.add_upload(audiobook['idDownload'], file_size)
            self.stats_manager.update_status("idle")
            logger.info("Audiolibro subido exitosamente")
            
        except Exception as e:
            self.stats_manager.update_status("error")
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