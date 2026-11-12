# 🌮 El Compa Chambeador — asistente IA en Python + HTML

## Instalación (una sola vez)
```
pip install -r requirements.txt
```

## Clave de API
Crea una en https://console.anthropic.com y defínela:

- Windows (PowerShell): `$env:ANTHROPIC_API_KEY="tu_clave"`
- Mac/Linux: `export ANTHROPIC_API_KEY="tu_clave"`

## Ejecutar
```
python server.py
```
Abre http://localhost:5000 en el navegador.

## Qué incluye
- Modos: General, Programador, Examen/tareas, Investigador
- Búsqueda web opcional
- Modo agente (opcional): la IA escribe, ejecuta y verifica código Python sola en un bucle.
  Actívalo con `ALLOW_CODE_EXEC=1` (Windows: `$env:ALLOW_CODE_EXEC="1"`). Ejecuta código en TU equipo; úsalo con cuidado.
- Adjuntar archivos de texto/código, dictado por voz, copiar código, historial local
- Cambiar modelo: variable `CLAUDE_MODEL`
