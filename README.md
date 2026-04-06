# Proyecto de Transacciones Bancarias (Cliente-Servidor)

Este proyecto implementa un sistema básico de transacciones bancarias mediante una arquitectura Cliente-Servidor utilizando *sockets* en Python (TCP).

## Características principales
- **Autenticación bidireccional**: El sistema requiere introducir un nombre de usuario y su respectiva contraseña, todo de manera interactiva a través del cliente.
- **Gestión por lotes (Batches)**: Las operaciones del usuario (consultar saldo, ingresar o retirar dinero) se acumulan en un lote temporal. Estas solo se aplican en el balance definitivo cuando el usuario aprueba y confirma el lote entero.
- **Base de datos local (JSON)**: Se utiliza un ligero archivo `.json` que actúa como base de datos de usuarios para almacenar credenciales, el saldo disponible y el historial de operaciones confirmadas.
- **Manejo de Inactividad y Excepciones**: El servidor detecta la inactividad de una sesión y la expira para evitar brechas de seguridad, de igual forma que valida todo tipo de carácteres introducidos evitando comportamientos extraños.

## Guion de archivos del proyecto

- `client/client.py`: Contiene el código fuente del cliente. Se encarga de conectarse al socket del servidor, retransmitir la interfaz en la consola del usuario y devolver las entradas de teclado a la máquina servidora.
- `server/server.py`: Contiene el motor principal y código del servidor. Es capaz de manejar múltiples cuentas al mismo tiempo por hilos (`threading`), realiza validación de entradas de usuario, manipula toda la lógica de los lotes de acciones bancarias y gestiona la lectura y escritura en la base local.
- `server/clients_db.json`: Es el archivo utilizado como base de datos. Contiene los datos persistentes de los clientes (usuario, constraseña, salario en cuenta e historial de lotes (batches)).
- `documentación.pdf`: documento en el que se encuentran los diagramas secuencia, de estados, reglas ABNF y el resto de información relevante del proyecto.
- `README.md`: Este mismo archivo con la documentación rápida del proyecto y guion de ficheros.
- 'npcaps':

## Instrucciones de Ejecución
Antes de todo, buscar la IP en la que vamos a correr el servidor, y en el código client.py en la variable host poner la ip del servidor. Si es en local poner en host localhost, y en el código de server.py en la última línea, borrar lo de dentro de los paréntesis.
1. **Iniciar el servidor**:
   Desplácese con la terminal a la carpeta `server` y ejecútelo con Python:
   ```bash
   python server.py
   ```
   El servidor empezará a escuchar conexiones entrantes inmediatamente (por defecto en el puerto `6345` del `localhost` o `[IP_ADDRESS]`).

2. **Iniciar el (los) cliente(s)**:
   Abra una nueva terminal en la carpeta `client` y ejecútelo con Python:
   ```bash
   python client.py
   ```
   *Nota: Puede iniciar tantos procesos de clientes como desee de forma simultánea, el servidor los despachará como es debido.*

   Una vez dentro, se pone el usuario los cuáles son cliente1, cliente2, cliente3, cliente4 y cliente5, y sus respectivas contraseñas pass1234, pass2345 y así sucesivamente.
   Para probar la funcionalidad, usar 1 para consultar el saldo , 2 y a continuación una cantidad para ingresar, el 3 y una cantidad para sacar y el 4 para cerrar sesión.
   Si se hace un lote de instrucciones y alguna está mal se hace la que está bien. Si hay algún error en lso estados 0 o 1 se vuelve al 0. si hay alguno en los 2 o 3 se vuelve al 2. Si se acaba el tiempo vuelve al estado 0.

## Instrucciones para ver los archivos de Wireshark

Abrir los archivos y filtrar por tcp.port==6345, se puede ver el establecimiento de la sesión y si en una traza le damos a Seguir/Follow y después a TCP Stream podemos ver el progeso de los mensajes.

