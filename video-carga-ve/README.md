# Video: carga inteligente de 5 VE (1080×1920, 30 s)

- `sim.py`: escenario ilustrativo (5 VE, cargadores de 7,4 kW, baterías de 60 kWh, objetivo 80 % de SoC).
  - Sin gestión: cada VE carga a potencia máxima al conectarse → pico de 37,0 kW a las 20:00.
  - Gestionada: prioridad estática por holgura = (hora de salida − llegada) − energía requerida / 7,4 kW,
    que combina hora de salida y SoC; límite de potencia mínimo factible hallado por bisección → 8,2 kW.
- `render.py`: dibuja los cuadros con Cairo y codifica H.264 con ffmpeg (`pip install pycairo numpy imageio-ffmpeg`).

```
python3 render.py ev_carga_inteligente.mp4
```
