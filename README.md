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
En este ejercicio se quiere poder separar la configuración del container de la aplicación en sí. Para eso vamos a usar docker volumes para poder montar un archivo config tanto de `server` como de `client` y que estos puedan leerlo, evitando que tengamos que recompilar la imagen completa al cambiar algo en estas configs.  
1. Creo un volumen usando el comando `docker volume create config-volume`.
2. Utilizo para la ejecución de los containers, el comando `docker run --rm -v $(PWD)/server/config.ini:/config2/config.ini -v config-volume:/config alpine cp /config2/config.ini /config`. Primero que nada con lo que está después del primer -v monto el archivo `config.ini` en el directorio `/config` del container, y con el segundo -v monto el volumen `config-volume` que es el que ya cree de manera externa en la consola, para luego poder usar el container temporal donde guardé el archivo `config.ini` para copiarlo al volumen `config-volume` usando alpine como herramienta. Esto se hace de manera análoga con el cliente. Estos comandos fueron definidos en el `Makefile` para poder ejecutarlos de manera más sencilla al usar el comando make _docker-compose-up_.  
Dicho comando solo se ejecutará para copiar las configs inicialmente, porque en caso de que lo haga cada vez que se haga `docker-compose up` se sobreescribirán las configs con las originales. Para eso agregué el siguiente if en el script `copy-checker.sh` usando `bash`:
```makefile
if ! docker run --rm -v config-volume:/config alpine test -e /config/config.x
```  
Que comprueba si el archivo `config.x` ya existe en el volumen `config-volume` y si no lo copia.      
3. Una vez con los archivos de configuración en mi volumen tengo que modificar el docker-compose para que los containers utilicen el volumen. Para esto simplemente agrego la siguiente línea en el `docker-compose.yml` para los servicios `server` y `client` respectivamente:
```yaml
volumes:
  - config-volume:/config
```
Sin olvidarme claro de agregar esto a la definición de mi script para poder crear múltiples clientes, agregando la especificación del volúmen que estoy usando tanto en servidor como cliente y declaralo como externo (ya que lo cree de manera externa con el comando `docker create`).  

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
el uso de `os.Exit` para que el programa se cierre de manera _graceful_ y no abrupta, en el caso del cliente se hace uso 
de un flag `sigterm_received` que se setea en `true` cuando se recibe la señal y se chequea en el bucle principal para
cortar la ejecución, y en el caso del servidor se utiliza un timeout al recibir conexiones para que el programa verifique
cada segundo si se recibió la señal, además de evitar una llamada bloqueante con accept mediante el uso de `select` para 
verificar el socket solamente si hay algo para leer (una conexión entrante).
Para poder probar que los logs funcionan correctamente basta con agregar en el `Makefile` el comando `make docker-compose-logs` dentro de la regla `docker-compose-down` (ya que esta por dentro al hacer el _stop_ manda una _SIGTERM_ a los containers y debería cerrarlos de manera _graceful_ si no estaban cerrados ya).