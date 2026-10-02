# La aeronave: Sikorsky H-19A Chickasaw (S-55), matrícula H-08

Los valores que usa el simulador están en `h08/config/aeronave.py` (`AERONAVE` y `LIM`).
La fuente principal es el manual **T.O. 1H-19A-1**.

## Ficha de la célula H-08

| | |
|---|---|
| Modelo | Sikorsky H-19A Chickasaw (S-55) |
| Número de serie | c/n 55-135 (ex USAF 51-3873) |
| Operador | Fuerza Aérea Argentina, 1962 - 1968 |
| Motor | Pratt & Whitney R-1340-57 «Wasp», radial de 9 cilindros; 600 HP a 2250 RPM (despegue), 550 HP a 2200 RPM (continuo) |
| Rotor principal | 3 palas, 16,15 m de diámetro |
| RPM de rotor | 170 a 245 (operación normal ~220) |
| Relación de reducción | 10:1 (2200 RPM de motor → 220 RPM de rotor) |
| Combustible | tanque delantero 378 L + tanque trasero 322 L = 700 L |
| Sistema eléctrico | 24 V CC, generador de 200 A |
| Vne | 176 km/h (95 kt) a nivel del mar |
| Crucero | 137 km/h (74 kt) |
| Destino final | preservado como material didáctico en el Área Material Quilmes / Taller Regional Quilmes |

## La relación 10:1 y el tacómetro doble

El tacómetro doble del S-55 tiene dos agujas concéntricas: la escala de motor llega a
3500 RPM y la de rotor a 350 RPM. Como la reducción es 10:1, cuando el embrague está
acoplado y el motor arrastra al rotor, las dos agujas quedan **superpuestas**. Si el
motor falla, la rueda libre desacopla y las agujas se **separan** («needle split»): el
rotor sigue girando por autorrotación mientras la aguja del motor cae. Es uno de los
detalles más didácticos del simulador, y `pruebas/test_vuelo.py` comprueba que las dos
tablas de calibración se superpongan (diferencia de 0,5° como máximo).
