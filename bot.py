"""Motor de conversación: se puede probar sin cuenta de Meta."""
import unicodedata
from datetime import datetime

MENU = '¡Hola! 👋🚌 Bienvenido a El Cometa Bis — Boletería Santa Rosa, Corrientes.\n\n📌 *¿Cómo funciona la atención?*\nPrimero, seleccioná una de las siguientes opciones respondiendo únicamente con el *número correspondiente*:\n1️⃣ *Comprar pasajes*\n2️⃣ *Consultar destinos y horarios*\n3️⃣ *Encomiendas*\n4️⃣ *Preguntas frecuentes*\n5️⃣ *Hablar con un asesor*\n\n🤖 El asistente virtual te irá guiando según la opción seleccionada.\n👤 Si necesitás *atención personalizada*, seleccioná la opción *5*. El bot pausará las respuestas automáticas. La atención de un asesor depende de que la boletería revise este chat.\n⚠️ *Importante:* Para agilizar la atención, evitá enviar varios mensajes seguidos mientras aguardás la respuesta de un asesor.\n🏠 En cualquier momento podés escribir *MENÚ* para volver al menú principal.\n🚀 *Nos encontramos en proceso de modernización para brindarte una atención más rápida, ordenada y eficiente.*\n*El Cometa Bis — Boletería Santa Rosa, Corrientes* 🚌'
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
    if normalized in ('menu', 'inicio'):
        return {}, MENU
    if state.get('mode') == 'human':
        return state, None
    if normalized in ('hola', 'cancelar'):
        return {}, MENU
    if normalized in ('5', 'asesor', 'persona') and state.get('mode') not in QUESTIONS:
        return {'mode': 'human'}, 'Las respuestas automáticas están pausadas. La atención de un asesor depende de que la boletería revise este chat. Escribí MENÚ para volver al inicio.'
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
