# Quién puede mirar y quién puede mandar

El código está en `h08/web/acceso.py` y el servidor lo aplica en cada pedido
(`h08/web/servidor.py`).

## Qué resuelve

El tablero se muestra en el taller: hay una pantalla proyectada, un profesor con el
celular en la mano y veinte alumnos mirando desde el suyo. Todos tienen que poder **ver**
el tablero en vivo; ninguno tiene que poder meterle una falla por tocar donde no debe.

## Tres cosas distintas

1. **Entrar.** Cualquiera entra y mira. No hay clave para mirar.
2. **Ser admin.** Hace falta la clave, que viaja adentro del QR del profesor. Ser admin
   habilita a mandar.
3. **Tener el mando.** Un solo dispositivo a la vez. Si el profesor y un ayudante entran
   los dos con el QR, los dos son admin, pero manda uno solo; el otro puede pedirlo.

La tercera existe porque dos personas activando fallas distintas al mismo tiempo arruinan
la demostración. El que tiene el mando puede ceder o rechazar el pedido; si no contesta
en 30 segundos, el que pidió se lo queda. Y si el titular desaparece (cerró el navegador,
se quedó sin batería), a los 45 segundos sin señales el mando queda libre.

## Alcance de esta protección

Esto **no es seguridad informática** en sentido estricto. El tablero habla HTTP, no
HTTPS: la clave viaja en claro la primera vez y la cookie de sesión en todos los pedidos.
Alguien conectado a la misma red wifi, con herramientas y decidido, podría hacerse pasar
por el profesor.

Sirve contra lo que hay en un aula o en una muestra:

- el alumno que abre la página y toca todo para ver qué pasa;
- el que escribe a mano la dirección `/api/modo/3` en el navegador;
- el visitante que quiere «probar» el tablero.

Se dice así a propósito: una protección que se cree más fuerte de lo que es resulta peor
que ninguna, porque se confía en ella.

## La clave

Es un texto aleatorio de 22 caracteres, guardado en `datos/secreto_admin.json`, un
archivo que sólo puede leer el usuario que corre el tablero (permiso 600). Se genera sola
la primera vez y no cambia, salvo que se pida:

    python3 -m h08 --renovar-clave

Al renovarla, el QR anterior deja de servir en el acto y se cierran las sesiones abiertas.

**Ninguna ruta web muestra la clave ni el QR de administrador**: se obtienen en la
terminal de la Raspberry con `python3 -m h08 --qr-admin`. Una página que supiera mostrar
la llave sería una página a la que se le puede pedir la llave. `pruebas/test_servidor.py`
lo comprueba pidiendo todas las rutas y buscando la clave en cada respuesta.

## La cookie

El QR trae la clave en la dirección. Si esa dirección quedara en pantalla, la clave
quedaría en el historial del navegador y a la vista del curso. Por eso el servidor la
canjea por una cookie y redirige a la dirección limpia. La cookie es `HttpOnly` (el
javascript de la página no la puede leer) y `SameSite=Lax` (otra página no puede mandar
órdenes con esa sesión). Una sesión sin uso vence a las 8 horas, que cubren una jornada
de taller.
