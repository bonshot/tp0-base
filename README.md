# <span style="color:#3d24c9">TP0: Docker, concurrencia y comunicación</span>
Bienvenidos a mi TP0 de Sistemas Distribuidos, soy Facundo Aguirre Argerich.  
En este trabajo práctico vamos a trabajar con Docker, concurrencia y comunicación entre procesos.

## <span style="color:#9669f0">Ejercicio 1 y 1.1</span>
Para el ejercicio 1 simplemente basta con agregar una configuración similar al `client1` proporcionado por la cátedra para poder tener un `container` nuevo que se conecte al server, a fin de cuentas usará la misma red.    

De manera análoga en el ejercicio 1.1 solo debemos agregar las líneas mencionadas cambiando el ID del cliente de forma que se identifique de forma única en la red. Esto decidí hacerlo con bash por simplicidad en el manejo de archivos y esto nos ahorra, como se explicó en la presentación del trabajo, tener que hacer a mano tantos clientes nuevos como queramos.  
La forma de ejecutar el script es la siguiente:  
```bash
./create_clients.sh <cantidad_de_clientes>
```
O para entornos no unix-like:
```bash
bash create_clients.sh <cantidad_de_clientes>
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
