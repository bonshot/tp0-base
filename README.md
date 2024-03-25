# <span style="color:#3d24c9">TP0: Docker, concurrencia y comunicación</span>
Bienvenidos a mi TP0 de Sistemas Distribuidos, soy Facundo Aguirre Argerich.  
En este trabajo práctico vamos a trabajar con Docker, concurrencia y comunicación entre procesos.

## <span style="color:#9669f0">Ejercicio 1 y 1.1</span>
Para el ejercicio 1 simplemente basta con agregar una configuración similar al `client1` proporcionado por la cátedra para poder tener un `container` nuevo que se conecte al server, a fin de cuentas usará la misma red.    

De manera análoga en el ejercicio 1.1 solo debemos agregar las líneas mencionadas cambiando el ID del cliente de forma que se identifique de forma única en la red. Esto decidí hacerlo con bash por simplicidad en el manejo de archivos y esto nos ahorra, como se explicó en la presentación del trabajo, tener que hacer a mano tantos clientes nuevos como queramos.  
La forma de ejecutar el script es la siguiente:  
```bash
./script-multiclient.sh <cantidad_de_clientes>
```
O para entornos no unix-like:
```bash
bash script-multiclient.sh <cantidad_de_clientes>
```  
Luego de ejecutarlo se generará un archivo `docker-compose.yml` con la cantidad de clientes que se haya especificado integrados en la red del server. Se hizo esto con el solo fin de no interferir con el `docker-compose-dev.yml` que provee la cátedra, es meramente arbitrario. 
Para poder "uppear" los contenedores se reemplaza en el `Makefile` proveído por la cátedra el `docker-compose-dev.yml` por el generado por el script.  

## <span style="color:#9669f0">Ejercicio 2</span>
En este ejercicio se quiere poder separar la configuración del container de la aplicación en sí. Para eso vamos a usar docker volumes para poder montar un archivo config tanto de `server` como de `client` y que estos puedan leerlo y modificarlo, evitando que tengamos que recompilar la imagen completa al cambiar algo en estas configs.  
Para lograrlo, ya que los volumenes se deben hacer con directorios como fuente, cree una carpeta `config` en cliente y servidor donde guardé sus configuraciones respectivas. Así también como cambié los directorios desde donde se parsean esas configuraciones en el código main de ambos.
1. Creo un volumen para cada parte declarándolo en el compose.
```yaml
volumes:
  x_vol:
    driver: local
    driver_opts:
      type: none
      device: ./x/config   # x es server o client
      o: bind
```
2. Utilizo en la declaración del servicio correspondiente, el volumen mappeado hacia la carpeta config de cada container.   
3. Una vez configurados los volumenes, estos se encargarán de persistir los cambios desde ámbos lados en las configuraciones de cliente y servidor sin necesidad de recompilar la imagen.  
Sin olvidarme claro de agregar esto a la definición de mi script para poder crear múltiples clientes, agregando la especificación del volúmen que estoy usando tanto en servidor como cliente.

## <span style="color:#9669f0">Ejercicio 3</span>
Ahora se pide hacer un script usando `netcat` para poder interactuar con el servidor y verificar que la respuesta es el mensaje mismo por ser un EchoServer. Ahora, también se pide que se interactúe todo desde el container sin tener que instalar nada en la máquina host ni exponer puertos, usando `docker network`.  
Para esto simplemente usaré un docker-compose que esté compuesto solamente por el servidor como servicio ya que no quiero N clientes además corriendo más que el que emularé con el script de bash para usar `netcat`.  
Luego de definido `docker-compose-server.yaml`, en el script levanto el compose y creo un container temporal para poder interactuar con el servidor emulando un cliente.
```bash
docker run --name client_test --network tp0_testing_net -it ubuntu:latest /bin/bash -c "apt-get update && apt-get install -y netcat"
```
Este comando asigna el nombre `client_test` al container, lo conecta a la red `tp0_testing_net` especificada en el compose y lo ejecuta con `bash` para poder instalar `netcat` **en el container y no el HOST** y luego interactuar con el servidor.  
La interacción de lleva a cabo en una sola línea así como la comprobación de recibir el mismo mensaje de parte del EchoServer.
```bash
docker exec -it client_test /bin/bash -c "echo 'Hello buddy' | nc server 12345 | grep -q 'Hello buddy' && echo 'Test passed' || echo 'Test failed'"
```
Esto se encarga de enviar el mensaje al servidor usando `netcat` con la IP y puerto que el servidor tiene asignado en sus configs iniciales, luego usando pipes para redireccionar las salidas, con `grep` imprimo por pantalla si el mensaje recibido como respuesta del servidor es el mismo que el enviado y con `&&` y `||` imprimo si el test pasó o falló.  
Finalmente como se trata de un script de testing, me encargo de parar y remover el container temporal así como el compose que levanté para el servidor.  
Modo de uso:
```bash
./net_test_script.sh
```
O para entornos no unix-like:
```bash 
bash net_test_script.sh
```

## <span style="color:#9669f0">Ejercicio 4</span>
En este caso se deberá hacer un handleo de la señal _SIGTERM_ para que tanto cliente como servidor puedan cerrarse de manera correcta o _graceful_.  
Para lograrlo usé tanto en el servidor como cliente un `signal handler` que se encargue de cerrar el socket del lado correspondiente liberando la memoria asociada antes de cerrar el programa.  
En caso de `client` que corre en _Go_ utilizo la librería `os` para usar `os.Signal` y `os.Notify` para poder manejar la señal _SIGTERM_ con una _goroutine_ que se ejecuta de manera no bloqueante sobre el server esperando a que llegue la señal mediante la instrucción `<-sig` y en caso de `server` que corre en _Python_ utilizo `signal` para manejar la señal de manera análoga, sobrecargando el operador `__sigterm_handler` para que cierre el socket una vez que el handler creado reciba la señal.  
Una vez que estos handlers detectan la señal, cierran los recursos correspondientes y luego cierran el programa evitando
el uso de `os.Exit` para que el programa se cierre de manera _graceful_ y no abrupta, en el caso del se hace uso 
de un channel que se cierra cuando se recibe la señal y se chequea en el bucle principal para
cortar la ejecución, y en el caso del servidor se utiliza un flag `sigterm_received` así como un timeout al recibir conexiones para que el programa verifique cada segundo si se recibió la señal, además de evitar una llamada bloqueante con accept mediante el uso de `select` para verificar el socket solamente si hay algo para leer (una conexión entrante).
Para poder probar que los logs funcionan correctamente basta con agregar en el `Makefile` el comando `make docker-compose-logs` dentro de la regla `docker-compose-down` (ya que esta por dentro al hacer el _stop_ manda una _SIGTERM_ a los containers y debería cerrarlos de manera _graceful_ si no estaban cerrados ya).

## <span style="color:#9669f0">Ejercicio 5</span>
Para este ejercicio definí variables de entorno en el `docker-compose` para poder importarlas en el código como las propiedades de un gambler que registra una apuesta mediante una de las 5 agencias. Dichas agencias le mandaran el mensaje al servidor que es la central de apuestas y este registrará la apuesta en un csv usando `store_bets()` y luego envía un ACK al gambler de la agencia para confirmar que la apuesta fue registrada.  
Para lograr esto tuve que crear un protocolo de comunicación entre servidor y cliente que pueda ser interpretado por ámbos mediante una convención de mensajes, así como también poder evitar short-write y short-reads desde ámbos lados, leyendo y escribiendo todo el mensaje en un solo `write` o `read` mediante el uso de un header que especifique el tamaño del mensaje.  
En mi protocolo definí que los mensajes tendrían este formato:
```python
HEADER|MESSAGE
```
Donde el `HEADER` es un entero que representa la longitud del mensaje y el `MESSAGE` es el mensaje en sí.  
y el mensaje está conformado de la siguiente manera con la información de la apuesta:
```python
<ID_AGENCIA>|<NOMBRE_GAMBLER>|<APELLIDO_GAMBLER>|<DOCUMENTO_GAMBLER>|<FECHA_CUMPLE_GAMBLER>|<NUMERO>
```
Finalmente para probarlo se corre el compose up y se miran los logs viendo que efectivamente la comunicación entre cliente y servidor se dá bien así como también el cliente recibe el ACK final de la apuesta registrada.  

## <span style="color:#9669f0">Ejercicio 6</span>
En este ejercicio me encontré con unas pocas dificultades, entre ellas la de cambiar el protocolo ya existente del ejercicio anterior y tener problemas con el manejo de las _tildes en los nombres_, lo que hacía que haya 2 bytes en lugar de 1 en esos caracteres y por ende el header no coincidía con el tamaño del mensaje. Esto lo solucioné modificando la forma de tratar al mensaje ni bien llega al servidor para hacerlo como bytes, y luego de obtener la información importante ahí si decodificarlo a utf-8 para poder trabajar con los nombres de los apostadores.  
En este caso lo que hice fue agregar un volumen nuevo para cada cliente que se conecte al servidor, de manera que pueda acceder a su archivo de apuestas y leerlo para poder enviarlo al servidor en batches de tamaño `BATCH_SIZE` definido inicialmente como una constante en el código, y luego fue agregado como una variable de entorno en las configuraciones tanto de cliente como de servidor para su fácil modificación y cargado en el código.  
Se toman esas apuestas y se las envía al servidor, el cual las recibe y las va registrando en el archivo `bets.csv` de manera análoga al ejercicio anterior. Una vez alcanzado `BATCH_SIZE` se envía un ACK al cliente para que este pueda seguir enviando apuestas, y en caso de que el cliente llegue a la parte final del archivo se (el intento de lectura de un batch resulta en una longitud menor de bets), se envía un mensaje de cierre al servidor para que este devuelva un ACK y cierre la conexión.  
Para poder verificar que efectivamente se registraron las apuestas en el archivo `bets.csv` luego de la ejecución, se puede hacer un `docker exec -it server wc bets.csv` y ver el primero de los 3 valores devueltos que es la cantidad de líneas en el archivo, es equivalente a la suma de las apuestas de todos los clientes que se conectaron al servidor, siendo esta 78697 (Con los archivos de apuestas que se proveen en el repositorio).  
Además, para poder ver que los exit codes son correctos en cada cliente (que se dificulta verlos porque la cantidad de mensajes del log opaca el exit `message`) se puede usar el siguiente comando:  
```bash
docker inspect --format='{{.State.ExitCode}}' <nombre_del_contenedor_o_id>
```
Esto devolverá el exit code del container que se le pase como argumento, y si es 0 significa que la ejecución fue exitosa.  

## <span style="color:#9669f0">Ejercicio 7</span>
Para el ejercicio se pide que simulemos el sorteo de la lotería, que habiendo el servidor recibido todas las apuestas, se sorteen los números y se envíen los resultados a los clientes.  
El comportamiento de parte de los clientes es luego de mandar todo su archivo de apuestas esperar a que el servidor revele los ganadores, para esto el servidor debe enviar un mensaje de `WINNERS` al cliente, el cual este debe interpretar y luego de recibirlo esperar a que el servidor le envíe los números ganadores para finalmente imprimir la cantidad de apuestas ganadoras que tuvo su agencia.  
Para lograrlo agregué al servidor una lista de sockets de forma que al terminar la recepción y guardado de las apuestas de un cliente, luego no se pierda ni cierre el socket del mismo para que cuando las `5` agencias hayan enviado sus apuestas, el servidor pueda enviar los números ganadores a cada cliente. Tenía intenciones de hacerlo genérico para poder soportar `N` agencias pero como en nuestro ejemplo abarcamos solo `5` agencias, me limité a usar una constante como contador de las agencias que ya se atendió en el servidor, si lo fueramos a aplicar a un caso real de `N` agencias, deberíamos poner un estilo de timeout para que el server espere hasta determinado momento a las agencias para que registren sus apuestas y pasado el tiempo no acepte más agencias y proceda con el sorteo.  
La forma de ejecución de este ejercicio y su comprobación son análogas a los anteriores, simplemente se corre el make del compose y se miran los logs para ver que efectivamente se registraron las apuestas y luego de sortear la lotería cada cliente imprime la cantidad de ganadores de su agencia por log.  



