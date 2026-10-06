"""Motor de conversación: se puede probar sin cuenta de Meta."""
import unicodedata
from datetime import datetime

MENU = """¡Hola! 👋🚌 Bienvenido a El Cometa Bis — Boletería Santa Rosa, Corrientes.
Soy tu asistente virtual.
1. Comprar pasajes
2. Consultar destinos y horarios
3. Encomiendas
4. Preguntas frecuentes
5. Atención de un asesor
Respondé con un número. Escribí MENÚ para volver al inicio.
✨ El Arte de viajar bien"""
FAQ = """¿Sobre qué querés consultar?
1. Boleto electrónico
2. Mascotas
3. Menores
4. Devoluciones
Escribí MENÚ para volver."""
QUESTIONS = {
    'pasajes': [('origen', '¿Desde qué ciudad viajás?'), ('destino', '¿A qué ciudad viajás?'), ('fecha', '¿Qué día viajás? Usá DD/MM/AAAA.'), ('pasajeros', '¿Cuántas personas viajan?')],
    'horarios': [('origen', '¿Desde qué ciudad salís?'), ('destino', '¿A qué ciudad viajás?'), ('fecha', '¿Para qué fecha? Usá DD/MM/AAAA.')],
    'encomiendas': [('origen', '¿Desde qué ciudad se envía?'), ('destino', '¿A qué ciudad se envía?'), ('paquete', 'Describí el contenido, las medidas y el peso aproximado del paquete.')],
}

def respond(state, text):
    """Devuelve (nuevo estado, respuesta). None significa silencio por atención humana."""
    state = dict(state or {})
    raw = text.strip()[:1500]
    normalized = ''.join(c for c in unicodedata.normalize('NFD', raw.lower()) if unicodedata.category(c) != 'Mn')
    if state.get('mode') == 'human':
        return state, None
    if normalized in ('menu', 'inicio', 'hola', 'cancelar'):
        return {}, MENU
    if normalized in ('5', 'asesor', 'persona') and state.get('mode') not in QUESTIONS:
        return {'mode': 'human'}, 'Tu consulta quedó pendiente de atención de un asesor. Te responderemos según disponibilidad.'
    mode = state.get('mode')
    if mode == 'faq':
        topics = {'1': 'boleto electrónico', '2': 'mascotas', '3': 'menores', '4': 'devoluciones'}
        if raw not in topics:
            return state, FAQ
        return {'mode': 'human', 'consulta': topics[raw]}, 'Un asesor revisará tu consulta sobre ' + topics[raw] + '. Las respuestas automáticas de este tema todavía están pendientes de confirmación.'
    if mode in QUESTIONS:
        index = state.get('index', 0)
        key, question = QUESTIONS[mode][index]
        if not raw:
            return state, question
        if key == 'fecha':
            try:
                date = datetime.strptime(raw, '%d/%m/%Y').date()
                # Se compara con la fecha local de Argentina.
                from zoneinfo import ZoneInfo
                if date < datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date():
                    raise ValueError()
            except ValueError:
                return state, 'Indicá una fecha válida desde hoy, con formato DD/MM/AAAA.'
        if key == 'pasajeros' and (not raw.isdigit() or not 1 <= int(raw) <= 50):
            return state, 'Indicá una cantidad de pasajeros entre 1 y 50.'
        data = dict(state.get('data', {}))
        data[key] = raw
        index += 1
        if index < len(QUESTIONS[mode]):
            return {'mode': mode, 'index': index, 'data': data}, QUESTIONS[mode][index][1]
        summary = '\n'.join(f'{k.capitalize()}: {v}' for k, v in data.items())
        return {'mode': 'human', 'tipo': mode, 'data': data}, 'Registramos tu consulta:\n' + summary + '\nUn asesor confirmará la información. Esta solicitud no reserva un asiento ni confirma una compra.'
    options = {'1': 'pasajes', '2': 'horarios', '3': 'encomiendas'}
    if raw in options:
        mode = options[raw]
        return {'mode': mode, 'index': 0, 'data': {}}, QUESTIONS[mode][0][1]
    if raw == '4':
        return {'mode': 'faq'}, FAQ
    return {}, MENU

if __name__ == '__main__':
    state = {}
    print(MENU)
    while True:
        try:
            message = input('\nCliente (SALIR para terminar, REINICIAR para nueva sesión): ')
        except EOFError:
            break
        if message.upper() == 'SALIR':
            break
        if message.upper() == 'REINICIAR':
            state = {}
            print(MENU)
            continue
        state, reply = respond(state, message)
        print(reply or '[Bot pausado: atención humana]')
