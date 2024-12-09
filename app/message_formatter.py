import logging
from typing import Dict

logger = logging.getLogger(__name__)

class MessageFormatter:
    MAX_CAPTION_LENGTH = 1024  # Telegram's caption limit
    
    def format_audiobook_info(self, audiobook: Dict) -> str:
        try:
            # Formato básico con información esencial
            basic_info = (
                f"📚 *{audiobook['title']}*\n\n"
                f"👤 *Autores:* {self._format_names(audiobook['authors'])}\n"
                f"🎙️ *Narradores:* {self._format_names(audiobook['narrators'])}\n"
                f"⏱️ *Duración:* {audiobook['duration']['hours']}h {audiobook['duration']['minutes']}m\n"
                f"📖 *Géneros:* {', '.join(audiobook['genres'])}\n"
                f"⭐ *Calificación:* {audiobook['ratings']['averageRating']}/5"
            )

            # Calcular espacio restante para la descripción
            remaining_space = self.MAX_CAPTION_LENGTH - len(basic_info) - len("\n\n📝 *Descripción:*\n") - len("\n\nDesarrollado by @Artutos") - 50  # Margen de seguridad
            
            description = audiobook.get('description', '')
            if len(description) > remaining_space:
                description = description[:remaining_space] + '...'

            full_message = (
                f"{basic_info}\n\n"
                f"📝 *Descripción:*\n{description}\n\n"
                f"Desarrollado by @Artutos"
            )

            return full_message
            
        except Exception as e:
            logger.error(f"Error formateando mensaje: {e}")
            return self._format_fallback_message(audiobook)
    
    def _format_names(self, items: list) -> str:
        """Formatea la lista de autores o narradores."""
        names = []
        for item in items[:2]:  # Solo los primeros 2
            if isinstance(item, dict):
                names.append(item['name'])
            else:
                names.append(item)
        return ', '.join(names)
    
    def _format_fallback_message(self, audiobook: Dict) -> str:
        """Mensaje de respaldo si hay error en el formato principal."""
        try:
            return (
                f"📚 *{audiobook['title']}*\n"
                f"👤 *Autor:* {audiobook['authors'][0] if audiobook['authors'] else 'Desconocido'}\n"
                f"⏱️ *Duración:* {audiobook['duration']['hours']}h {audiobook['duration']['minutes']}m\n\n"
                f"Desarrollado by @Artutos"
            )
        except:
            return "Error al formatear la información del audiolibro"